import datetime
import os
import typing

import aiogram

import app.database.admin
import app.database.admin.requests
import app.database.requests
import app.keyboards
import app.messages
import app.states


class ChechSubUser(aiogram.BaseMiddleware):
    """
    Проверка подписки на ТГ канал
    """

    def __init__(self, bot):
        self.bot = bot

    async def __call__(
        self,
        handler: typing.Callable[
            [aiogram.types.Message, typing.Dict[str, typing.Any]],
            typing.Awaitable[typing.Any],
        ],
        event: aiogram.types.Message,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        user_channel_status = await self.bot.get_chat_member(
            chat_id=os.getenv("TG_CHANNEL_ID", "-1002064780409"),
            user_id=data["event_from_user"].id,
        )
        if user_channel_status.status != "left" or data["event_update"].message.text == "/start":
            return await handler(event, data)

        await event.answer(
            app.messages.SUBSCRIPTION_MESSAGE,
            reply_markup=app.keyboards.SUBSCRIPTION,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )


class RegistrationNewUser(aiogram.BaseMiddleware):
    """
    Мидлварь для создания нового юзера в БД
    """

    async def __call__(
        self,
        handler: typing.Callable[
            [aiogram.types.Message, typing.Dict[str, typing.Any]],
            typing.Awaitable[typing.Any],
        ],
        event: aiogram.types.Message,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:

        async with app.database.models.async_session() as session:
            user = await app.database.requests.get_user(tg_id=data["event_from_user"].id)
            if user is None:
                await app.database.requests.add_user(
                    session,
                    tg_id=data["event_from_user"].id,
                )

        return await handler(event, data)


class CancelCommand(aiogram.BaseMiddleware):
    """
    Мидлварь для кнопки отмены (сброс стейта)
    """

    async def __call__(
        self,
        handler: typing.Callable[
            [aiogram.types.Message, typing.Dict[str, typing.Any]],
            typing.Awaitable[typing.Any],
        ],
        event: aiogram.types.Message,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:

        if data["event_update"].message.text == "Отменить":
            await data["state"].clear()
            await event.answer(
                app.messages.SUCCESS_MESSAGE + "Процесс прерван",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.keyboards.MAIN,
            )
            return

        return await handler(event, data)


class CheckWaitingOrder(aiogram.BaseMiddleware):
    """
    Проверка нахождения пользователя в состоянии ожидания/ЧС
    """

    async def __call__(
        self,
        handler: typing.Callable[
            [aiogram.types.Message, typing.Dict[str, typing.Any]],
            typing.Awaitable[typing.Any],
        ],
        event: aiogram.types.Message,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:

        async with app.database.models.async_session():
            user = await app.database.requests.get_user(
                tg_id=data["event_from_user"].id,
            )
            if user:
                blacklist = await app.database.admin.requests.get_user_for_blacklist(user.id)

                state: aiogram.fsm.context.FSMContext = data.get("state")
                current_state = await state.get_state()

                if (
                    data["event_update"].message.text != "Отменить заказ"
                    and data["event_update"].message.text != "Закрыть тикет"
                    and (user.waiting_support or user.waiting_order)
                    and current_state != app.states.AnswerTicket.message.state
                ):
                    await event.answer(
                        app.messages.WAITING_ORDER_OR_SUPPORT_MESSAGE,
                        parse_mode=aiogram.enums.ParseMode.HTML,
                        reply_markup=app.keyboards.CANCEL_ORDER_OR_CLOSE_TICKET,
                    )
                elif blacklist:
                    await event.answer(app.messages.BLACKLIST_MESSAGE, parse_mode=aiogram.enums.ParseMode.HTML)
                else:
                    return await handler(event, data)


class CheckTime(aiogram.BaseMiddleware):
    """
    Мидлварь для проверки часов работы студии
    """

    async def __call__(
        self,
        handler: typing.Callable[
            [aiogram.types.Message, typing.Dict[str, typing.Any]],
            typing.Awaitable[typing.Any],
        ],
        event: aiogram.types.Message,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:

        start_time = datetime.time(10, 0)
        end_time = datetime.time(22, 0)

        formatted_start_time = start_time.strftime("%H:%M")
        formatted_end_time = end_time.strftime("%H:%M")

        if start_time <= datetime.datetime.now().time() <= end_time:
            return await handler(event, data)
        return event.answer(
            "Упс!\n"
            "🙈 К сожалению, время работы нашего бота вышло.\n\n"
            f"Время работы бота: с {formatted_start_time} до {formatted_end_time} часов",
        )
