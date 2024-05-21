import os

import aiogram

import app.database.models
import app.database.requests
import app.keyboards
import app.messages
import app.states as st


router = aiogram.Router()


@router.message(aiogram.filters.CommandStart())
async def cmd_start(message: aiogram.types.Message):
    await message.answer(
        app.messages.START_MESSAGE,
        reply_markup=app.keyboards.MAIN,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )


@router.message(aiogram.F.text == "📨 Тех. поддержка")
async def cmd_create_ticket(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        "❗️ Пожалуйста, опишите вашу проблему/вопрос (кратко)",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(st.CreateTicket.question)


@router.message(st.CreateTicket.question)
async def cmd_create_ticket_question(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    await state.update_data(question=message.text.lower())

    async with app.database.models.async_session() as session:
        user = await app.database.requests.get_user(message.from_user.id)
        await state.update_data(user=user.id)
        data = await state.get_data()

        tickets_user = await app.database.requests.get_tickets_user(user.id)

        if not tickets_user:
            await app.database.requests.add_ticket(session, data)
            await app.database.requests.update_user_ticket(
                session,
                message.from_user.id,
            )
            ticket_id = await app.database.requests.get_ticket(user.id)

            await message.answer(
                f"♻️ <b>Тикет №{ticket_id.id}</b> успешно создан...\n"
                "Пожалуйста, ожидайте ответа от Агента Технической поддержки\n\n"
                "Если вы ошиблись - <b>закройте свой тикет кнопкой ниже</b>",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.keyboards.CANCEL_TICKET,
            )
        else:
            await message.answer(
                "❗️ Упс... Кажется у вас уже есть созданный тикет\n",
                reply_markup=app.keyboards.CANCEL_TICKET,
            )

    await state.clear()


@router.message(aiogram.F.text == "📪 Контакты")
async def cmd_contacts(message: aiogram.types.Message):
    await message.answer(
        app.messages.CONTACTS_MESSAGE,
        reply_markup=app.keyboards.MAIN,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )


@router.message(aiogram.F.text == "💚 Вывести команды")
async def cmd_keyboard(message: aiogram.types.Message):
    await message.answer(
        "Секунду... Уже вывожу вам свои команды 💚",
        reply_markup=app.keyboards.MAIN,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )


@router.message(aiogram.F.text == "📚 Каталог")
async def cmd_catalog(message: aiogram.types.Message):
    request = await app.database.requests.get_catalog()

    if request:
        await message.answer("♻️ Секунду, уже достаю каталог и пересылаю вам...")
        for i in request:

            keyboard = aiogram.utils.keyboard.InlineKeyboardBuilder()
            keyboard.add(
                aiogram.types.InlineKeyboardButton(
                    text="Выбрать",
                    callback_data=f"product_{str(i.id)}",
                ),
            )

            await message.answer_photo(i.image)
            await message.answer(
                f"<b>{i.title.title()}</b>\n\n"
                f"{i.description}\n\n"
                f"Цена за услугу: {i.price} руб.\n"
                f"Срок выполнения: {i.deadline} дней",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=keyboard.as_markup(),
            )

    else:
        await message.answer(
            "♻️ К сожалению, каталог пуст",
            parse_mode=aiogram.enums.ParseMode.HTML,
        )


@router.callback_query(aiogram.F.data.startswith("product_"))
async def product_selected(
    callback: aiogram.types.CallbackQuery,
    state: aiogram.fsm.context.FSMContext,
):
    product = callback.data.replace("product_", "")
    await state.update_data(item_id=product)

    await callback.message.answer(
        "♻️ Начинаем процесс оформления заказа...\n"
        f"Ваш выбранный товар - №{product}\n\n"
        "Пожалуйста, укажите промокод, если он у вас есть: (если нет - напишите 0)",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(st.CreateOrder.pcode)


@router.message(st.CreateOrder.pcode)
async def order_create_description(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    await state.update_data(pcode=message.text.lower())

    async with app.database.models.async_session() as session:
        user = await app.database.requests.get_user(
            message.from_user.id,
        )
        await state.update_data(user=user.id)

        pcode = None
        if message.text.lower() != "0":
            pcode = await app.database.requests.get_pcode(name=message.text.lower())
            if pcode:
                await app.database.requests.update_pcode(name=message.text.lower())
                await message.answer(
                    f"✅ Вы успешно активировали промокод {message.text.lower()} - {pcode.discount}% скидки",
                )
            else:
                await message.answer(
                    f"❗️ К сожалению, промокода {message.text.lower()} - не существует. "
                    "Повторите попытку или введите 0",
                )
                await state.set_state(st.CreateOrder.pcode)
                return

        await app.database.requests.update_user(
            session,
            tg_id=message.from_user.id,
        )

        data = await state.get_data()
        if await app.database.requests.add_order(session, data):
            await message.answer(
                app.messages.SUCC_CREATE_ORDER_MESSAGE,
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.keyboards.CANCEL_ORDER,
            )

            user_profile_link = f'<a href="tg://user?id={message.from_user.id}">Профиль пользователя</a>'
            discount_info = (
                f"ПРОМОКОД: {data.get('pcode')} - {pcode.discount}% скидки"
                if pcode
                else ""
            )
            item = await app.database.requests.get_item(data.get("item_id"))
            await bot.send_message(
                os.getenv("ADMIN_ID", "admin_id"),
                f"❗️ Пришел новый заказ\n\n{user_profile_link}\n"
                f"Товар: {item.title.title()}\n"
                f"{discount_info}",
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        else:
            await message.answer("😱 Похоже, у вас уже есть действительный заказ...")

        await state.clear()


@router.message(aiogram.F.text == "Отменить заказ")
async def cmd_cancel_order(message: aiogram.types.Message):
    async with app.database.models.async_session() as session:
        user = await app.database.requests.get_user(message.from_user.id)
        if await app.database.requests.get_order(user.id):
            await app.database.requests.delete_order(session, user.id)

            await message.answer(
                "♻️ Ваш заказ успешно отменен",
                reply_markup=app.keyboards.MAIN,
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        else:
            await message.answer("❗️ У вас нет активных заказов")


@router.message(aiogram.F.text == "Закрыть тикет")
async def cmd_close_ticket(message: aiogram.types.Message):

    async with app.database.models.async_session():
        user = await app.database.requests.get_user(message.from_user.id)
        await app.database.requests.close_ticket_from_user(user.id)

    await message.answer(
        "♻️ Ваш тикет <b>успешно закрыт</b>",
        reply_markup=app.keyboards.MAIN,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )


@router.message(aiogram.F.text == "✅ Подписался")
async def cmd_subscription(message: aiogram.types.Message):
    await message.answer(
        app.messages.SUBSCRIPTION_SUCC_MESSAGE,
        reply_markup=app.keyboards.MAIN,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )
