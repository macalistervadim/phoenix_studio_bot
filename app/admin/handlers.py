import asyncio
import os
import uuid

import aiogram
import sqlalchemy

import app.admin.filters
import app.admin.keyboards
import app.admin.states
import app.database.admin.requests
import app.database.models
import app.database.requests
import app.keyboards
import app.messages


router = aiogram.Router()

MAX_MESSAGE_LENGTH = 4096


async def get_profile_link(tg_id):
    user_profile_link = f'<a href="tg://user?id={tg_id}">Профиль пользователя</a>'
    return user_profile_link


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "/admin",
)
async def cmd_admin(message: aiogram.types.Message):
    await message.answer(
        app.messages.SUCCESS_MESSAGE + "Открываю админку",
        reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Черный список",
)
async def cmd_blacklist(message: aiogram.types.Message):
    blacklist = await app.database.admin.requests.get_all_blacklist()

    if blacklist:
        await message.answer(
            app.messages.SUCCESS_MESSAGE + "Вывожу черный список",
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )
        lines = []
        for i in blacklist:
            user = await app.database.admin.requests.get_user_for_id(i.user)
            user_profile_link = await get_profile_link(user.tg_id)
            lines.append(
                f"<b>Блокировка №{i.id}</b>\n"
                f"{user_profile_link}\n"
                f"Причина: {i.reason}\n"
                f"Дата блокировки: {i.created_on.strftime('%H:%M %D')}\n",
            )

        result_string = "\n".join(lines)

        # Разбиваем на части, если сообщение слишком длинное
        for i in range(0, len(result_string), MAX_MESSAGE_LENGTH):
            await message.answer(
                result_string[i : i + MAX_MESSAGE_LENGTH],  # noqa: E203
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
    else:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Блокировки отсутствуют",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Вынести из ЧС",
)
async def cmd_del_user_blacklist(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):
    await message.answer(
        app.messages.INFORMATION_MESSAGE
        + "Пожалуйста, перешлите контакт пользователя, которого необходимо вынести из ЧС",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.DelBlackList.contact)


@router.message(lambda message: message.contact, app.admin.states.DelBlackList.contact)
async def cmd_del_user_blacklist_contact(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    await state.update_data(contact=message.contact)
    user = await app.database.requests.get_user(int(message.contact.user_id))
    if await app.database.admin.requests.delete_user_blacklist(user.id):
        await message.answer(
            app.messages.SUCCESS_MESSAGE + "Пользователь вынесен из Черного списка",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )
        await bot.send_message(
            user.tg_id,
            app.messages.NOTIFICATION_MESSAGE
            + "Агент Поддержки вынес вас из Черного списка.\nПожалуйста, впредь не нарушайте правила PHOENIX STUDIO",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.MAIN,
        )
    else:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Пользователя нет в Черном списке",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Занести в ЧС",
)
async def cmd_add_user_blacklist(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):
    await message.answer(
        app.messages.INFORMATION_MESSAGE
        + "Пожалуйста, перешлите контакт пользователя, которого необходимо занести в ЧС",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.AddBlackList.contact)


@router.message(lambda message: message.contact, app.admin.states.AddBlackList.contact)
async def cmd_add_user_blacklist_contact(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext):
    await state.update_data(contact=message.contact)

    user = await app.database.requests.get_user(int(message.contact.user_id))
    if user:
        await state.update_data(user=user)

        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Укажите причину блокировки",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
        )

        await state.set_state(app.admin.states.AddBlackList.reason)
    else:
        await state.clear()
        await message.answer(
            app.messages.ERORR_MESSAGE + "Данный пользователь не является нашим клиентом",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )


@router.message(app.admin.states.AddBlackList.reason)
async def cmd_add_user_blacklist_reason(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    await state.update_data(reason=message.text.lower())
    data = await state.get_data()

    if await app.database.admin.requests.get_user_for_blacklist(data.get("user").id) is None:
        await app.database.admin.requests.add_user_blacklist(data)

        await message.answer(
            app.messages.SUCCESS_MESSAGE + "Пользователь занесен в Черный список",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

        await bot.send_message(
            data.get("user").tg_id,
            app.messages.NOTIFICATION_MESSAGE
            + f"Вы были занесены в Черный список Агентом Поддержки. <b>Причина блокировки: {data.get('reason')}</b>\n\n"
            "К сожалению, дальнейшее взаимодействие с ботом недоступно.\n"
            f"Если вы считаете это ошибкой, пожалуйста, свяжитесь с Администратором - https://t.me/macalistervadim",
            parse_mode=aiogram.enums.ParseMode.HTML,
        )
    else:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Данный пользователь уже в Черном списке",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Сделать рассылку",
)
async def cmd_mailing(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Отправьте сообщение с документом/фотографией или прочим для рассылки",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.Mailing.message)


@router.message(app.admin.states.Mailing.message)
async def cmd_mailing_message(message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext, bot: aiogram.Bot):
    users = await app.database.admin.requests.get_all_users()

    content = None
    content_type = None

    if message.photo:
        content = message.photo[-1].file_id
        content_type = "photo"
    elif message.document:
        content = message.document.file_id
        content_type = "document"
    else:
        content = message.text
        content_type = "text"

    successful = 0
    failed = 0

    for user in users:
        try:
            if content_type == "photo":
                await bot.send_photo(user.tg_id, content, caption=message.caption)
            elif content_type == "document":
                await bot.send_document(user.tg_id, content, caption=message.caption)
            else:
                await bot.send_message(user.tg_id, content, parse_mode=aiogram.enums.ParseMode.HTML)
            successful += 1
        except aiogram.exceptions.TelegramAPIError:
            failed += 1

        await asyncio.sleep(0.1)  # Пауза между отправками

    await message.answer(
        app.messages.SUCCESS_MESSAGE + f"Рассылка завершена.\nУспешно: {successful}\nНе удалось: {failed}",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
    )

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Отправить реквизиты",
)
async def cmd_send_payment(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Перешлите контакт, которому необходимо переслать реквизиты",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.SendPayment.contact)


@router.message(app.admin.states.SendPayment.contact)
async def cmd_send_payment_contact(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    user = message.contact.user_id
    await bot.send_message(
        user,
        app.messages.PAYMENT,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )
    await message.answer(
        app.messages.SUCCESS_MESSAGE + "Реквизиты отправлены пользователю",
        reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Статистика",
)
async def cmd_statistic(message: aiogram.types.Message):
    await message.answer(
        "🔰 Вывожу статистику...",
        reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )
    statistics = await app.database.admin.requests.get_ratings_statistics()
    await message.answer(
        f"Общее количество оценок: {statistics['total_ratings']}\n"
        f"😡: {statistics['scores']['score_bad']}\n"
        f"😕: {statistics['scores']['score_not_very']}\n"
        f"🤨: {statistics['scores']['score_not_bad']}\n"
        f"😀: {statistics['scores']['score_cool']}\n"
        f"Средняя оценка: {statistics['average_score']:.2f}",
    )


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Создание гифта(-ов)",
)
async def cmd_admin_create_gift(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Введите количество создаваемых гифтов",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.admin.states.AdminCreateGiftCard.count)


@router.message(app.admin.states.AdminCreateGiftCard.count)
async def cmd_admin_create_gift_count(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(count=message.text)

    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Теперь укажите сумму подарочных сертификатов",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.admin.states.AdminCreateGiftCard.amount)


@router.message(app.admin.states.AdminCreateGiftCard.amount)
async def cmd_admin_create_gift_amount(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    if 500 <= int(message.text) <= 25000:
        await state.update_data(amount=message.text)

        owner = await app.database.requests.get_user(message.from_user.id)
        await state.update_data(owner=owner.id)

        async with app.database.models.async_session() as session:
            data = await state.get_data()
            for i in range(int(data.get("count"))):
                gift = await app.database.admin.requests.add_admin_giftcard(
                    session,
                    data,
                )

                await message.answer(
                    app.messages.SUCCESS_MESSAGE + f"Вы успешно создали подарочный сертификат №{gift.id}",
                    reply_markup=app.keyboards.GIFT_CARDS,
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )
        await state.clear()
    else:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Сумма подарочного сертификата должна быть в диапазоне от 500 до 25000 руб.",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
        )
        await state.set_state(app.admin.states.AdminCreateGiftCard.amount)
        return


@router.callback_query(aiogram.F.data.startswith("gift_"))
async def gift_selected(
    callback: aiogram.types.CallbackQuery,
    bot: aiogram.Bot,
):
    gift = callback.data.replace("gift_", "")
    new_gift_name = uuid.uuid4().hex

    async with app.database.models.async_session() as session:
        await app.database.admin.requests.confirm_giftcard(
            session,
            int(gift),
            new_gift_name,
        )
        await callback.message.delete()
        await callback.message.answer(
            app.messages.SUCCESS_MESSAGE + f"Вы подтвердили выдачу подарочного сертификата №{gift}",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

        gift_user = await app.database.requests.get_gift(int(gift))
        get_gift_user = await app.database.admin.requests.get_user_for_id(
            gift_user.owner,
        )
        await bot.send_message(
            get_gift_user.tg_id,
            app.messages.NOTIFICATION_MESSAGE + "Агент Технической поддержки подтвердил выдачу подарочного сертификата."
            " Теперь вы можете посмотреть его в  <b>'Моих сертификатах'</b>",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.GIFT_CARDS,
        )


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Список тикетов",
)
async def cmd_get_tickets(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    async with app.database.models.async_session():
        tickets = await app.database.admin.requests.get_all_open_tickets()
        if tickets:
            await message.answer(
                app.messages.INFORMATION_MESSAGE + "Вывожу список активных тикетов\n\n",
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
            for i in tickets:
                keyboard = aiogram.utils.keyboard.InlineKeyboardBuilder()
                keyboard.add(
                    aiogram.types.InlineKeyboardButton(
                        text="Выбрать",
                        callback_data=f"ticket_{str(i.id)}",
                    ),
                )

                user = await app.database.admin.requests.get_user_for_id(i.user)
                await state.update_data(user=user)
                user_profile_link = await get_profile_link(user.tg_id)

                await message.answer(
                    f"<b>Тикет №{i.id}</b>\n\n"
                    f"{i.question}\n"
                    f"{user_profile_link}\n"
                    f"Статус: {i.status.name}\n"
                    f"Создан: {i.created_on.strftime('%H:%M %D')}\n",
                    parse_mode=aiogram.enums.ParseMode.HTML,
                    reply_markup=keyboard.as_markup(),
                )
        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "К сожалению, активных тикетов нет",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            )


@router.callback_query(aiogram.F.data.startswith("ticket_"))
async def ticket_selected(
    callback: aiogram.types.CallbackQuery,
    state: aiogram.fsm.context.FSMContext,
):
    ticket = callback.data.replace("ticket_", "")
    await state.update_data(ticket_id=ticket)

    await callback.message.answer(
        app.messages.INFORMATION_MESSAGE + "Начинаем процесс редактирования тикета\n"
        f"Ваш выбранный тикет - №{ticket}\n\n"
        "Выберите, что хотите отредактировать кнопками клавиатуры\n",
        reply_markup=app.admin.keyboards.CHOICE_EDIT_TICKET,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.EditTicket.ticket_id)


@router.message(app.admin.states.EditTicket.ticket_id)
async def ticket_ticket_id(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(choice=message.text.lower())

    if message.text == "Сменить статус":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Выберите на какой статус сменить",
            reply_markup=app.admin.keyboards.CHOICE_EDIT_ORDER_STATUS,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )

        await state.set_state(app.admin.states.EditTicket.edit_status)

    elif message.text == "Ответить":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Введите ответ пользователю:",
            reply_markup=app.keyboards.CANCEL_OR_BACK,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )

        await state.set_state(app.admin.states.EditTicket.answer_ticket)


@router.message(app.admin.states.EditTicket.edit_status)
async def ticket_edit_status(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    data = await state.get_data()
    translated_status = app.messages.STATUS_TRANSLATIONS.get(message.text.upper(), message.text)

    async with app.database.models.async_session() as session:
        if message.text == "COMPLETED":
            await app.database.requests.close_ticket_from_user(data.get("user").id)

            await message.answer(
                app.messages.SUCCESS_MESSAGE
                + f"Вы закрыли тикет №{data.get('ticket_id')}. Статус изменен на \"{translated_status}\" ",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            )

            await bot.send_message(
                data.get("user").tg_id,
                app.messages.NOTIFICATION_MESSAGE
                + f"Ваш <b>тикет №{data.get('ticket_id')}</b> закрыт Агентом Поддержки\n\n",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.keyboards.MAIN,
            )
            await bot.send_message(
                data.get("user").tg_id,
                app.messages.SCORE_SUPPORT_MESSAGE,
                reply_markup=app.keyboards.SCORE_SUPPORT.as_markup(),
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        else:
            try:
                await app.database.admin.requests.update_ticket_status(
                    session,
                    data.get("ticket_id"),
                    message.text,
                )
                await message.answer(
                    app.messages.SUCCESS_MESSAGE
                    + f"Вы успешно сменили статус тикета №{data.get('ticket_id')} на \"{translated_status}\"",
                    parse_mode=aiogram.enums.ParseMode.HTML,
                    reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
                )
                await bot.send_message(
                    data.get("user").tg_id,
                    app.messages.NOTIFICATION_MESSAGE
                    + f"Статус вашего <b>тикета №{data.get('ticket_id')}</b> изменен Агентом Поддержки на"
                    f' "{translated_status}"',
                    parse_mode=aiogram.enums.ParseMode.HTML,
                    reply_markup=app.keyboards.MAIN,
                )
            except sqlalchemy.exc.DBAPIError:
                await message.answer(
                    app.messages.ERORR_MESSAGE + "Выберите статус из перечня",
                    reply_markup=app.admin.keyboards.CHOICE_EDIT_ORDER_STATUS,
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )

                await state.set_state(app.admin.states.EditOrder.edit_status)
                return

        await state.clear()


@router.message(app.admin.states.EditTicket.answer_ticket)
async def ticket_answer_ticket(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    data = await state.get_data()

    async with app.database.models.async_session() as session:
        try:
            answer_ticket = aiogram.utils.keyboard.InlineKeyboardBuilder()
            answer_ticket.add(
                aiogram.types.InlineKeyboardButton(
                    text="Ответить Агенту поддержки",
                    callback_data=f"answer_ticket_{data.get('ticket_id')}",
                ),
            )

            await bot.send_message(
                data.get("user").tg_id,
                app.messages.NOTIFICATION_ADMIN_MESSAGE + f"Тикет №{data.get('ticket_id')}\n\"{message.text}\"",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=answer_ticket.as_markup(),
            )
            await app.database.admin.requests.update_ticket_status(
                session,
                data.get("ticket_id"),
                "IN_PROGRESS",
            )
            await message.answer(
                app.messages.SUCCESS_MESSAGE + f"Сообщение отправлено пользователю тикета №{data.get('ticket_id')}\n"
                "Статус автоматически изменен на - в работе",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            )

        except AttributeError:
            await message.answer(
                app.messages.ERORR_MESSAGE + f"Сообщение не отправлено пользователю тикета №{data.get('ticket_id')}\n"
                "Попробуйте повторно запросить список активных тикетов и повторите попытку дать ответ",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            )

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Список заказов",
)
async def cmd_all_orders(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    orders = await app.database.admin.requests.get_all_open_orders()

    if orders:
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Вывожу список заказов\n\n",
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )
        for i in orders:
            keyboard = aiogram.utils.keyboard.InlineKeyboardBuilder()
            keyboard.add(
                aiogram.types.InlineKeyboardButton(
                    text="Выбрать",
                    callback_data=f"order_{str(i.id)}",
                ),
            )

            giftcard_info = await app.database.requests.get_gift(i.giftcard) if i.giftcard is not None else "Нет"
            pcode_info = await app.database.admin.requests.get_pcode_for_id(i.pcode) if i.pcode != "0" else "Нет"
            item = await app.database.requests.get_item(i.product)
            user = await app.database.admin.requests.get_user_for_id(i.user)
            await state.update_data(user=user)

            user_profile_link = await get_profile_link(user.tg_id)
            await message.answer(
                f"<b>Заказ №{i.id}</b>\n\n"
                f"{item.title.title()}\n"
                f"{user_profile_link}\n"
                f"Статус: {i.status.name}\n"
                f"Создан: {i.created_on.strftime('%H:%M %D')}\n"
                f"ПРОМОКОД: <code>{pcode_info.name}</code> - {pcode_info.discount}% скидки\n"
                f"ПОД. СЕРТИФИКАТ: <code>{giftcard_info.name}</code> - сумма: {giftcard_info.amount} руб.\n",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=keyboard.as_markup(),
            )
    else:
        await message.answer(
            app.messages.ERORR_MESSAGE + "К сожалению, активных заказов нет",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )


@router.callback_query(aiogram.F.data.startswith("order_"))
async def order_selected(
    callback: aiogram.types.CallbackQuery,
    state: aiogram.fsm.context.FSMContext,
):
    order = callback.data.replace("order_", "")
    await state.update_data(order_id=order)

    await callback.message.answer(
        app.messages.INFORMATION_MESSAGE + "Начинаем процесс редактирования заказа...\n"
        f"Ваш выбранный заказ - №{order}\n\n"
        "Выберите, что хотите отредактировать кнопками клавиатуры\n",
        reply_markup=app.admin.keyboards.CHOICE_EDIT_ORDER,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.EditOrder.order_id)


@router.message(app.admin.states.EditOrder.order_id)
async def order_order_id(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(choice=message.text.lower())

    if message.text == "Сменить статус":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Выберите на какой статус сменить",
            reply_markup=app.admin.keyboards.CHOICE_EDIT_ORDER_STATUS,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )

        await state.set_state(app.admin.states.EditOrder.edit_status)


@router.message(app.admin.states.EditOrder.edit_status)
async def order_edit_status(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    data = await state.get_data()
    translated_status = app.messages.STATUS_TRANSLATIONS.get(message.text.upper(), message.text)

    async with app.database.models.async_session() as session:
        if message.text == "COMPLETED":
            await app.database.requests.close_order_from_user(data.get("user").id)

            await message.answer(
                app.messages.SUCCESS_MESSAGE
                + f"Вы завершили заказ №{data.get('order_id')}. Статус изменен на \"{translated_status}\" ",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            )
            await bot.send_message(
                data.get("user").tg_id,
                app.messages.NOTIFICATION_MESSAGE
                + f"Ваш <b>заказ №{data.get('order_id')}</b> завершен Исполнителем. Благодарим за обращение к нам",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.keyboards.MAIN,
            )
            await bot.send_message(
                data.get("user").tg_id,
                app.messages.SCORE_SUPPORT_MESSAGE,
                reply_markup=app.keyboards.SCORE_SUPPORT.as_markup(),
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        else:
            try:
                await app.database.admin.requests.update_order_status(
                    session,
                    data.get("order_id"),
                    message.text,
                )
                await message.answer(
                    app.messages.SUCCESS_MESSAGE
                    + f"Вы успешно сменили статус заказа №{data.get('order_id')} на \"{translated_status}\"",
                    reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )
                await bot.send_message(
                    data.get("user").tg_id,
                    app.messages.NOTIFICATION_MESSAGE
                    + f"Статус вашего <b>заказа №{data.get('order_id')}</b> изменен Исполнителем на"
                    f' "{translated_status}"',
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )

            except sqlalchemy.exc.DBAPIError:
                await message.answer(
                    app.messages.ERORR_MESSAGE + "Выберите статус из перечня",
                    reply_markup=app.admin.keyboards.CHOICE_EDIT_ORDER_STATUS,
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )

                await state.set_state(app.admin.states.EditOrder.edit_status)
                return

        await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Список промокодов",
)
async def cmd_all_pcodes(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    async with app.database.models.async_session():
        pcodes = await app.database.admin.requests.get_all_pcodes()

        if pcodes:
            await message.answer(
                app.messages.INFORMATION_MESSAGE + "Вывожу список промокодов\n\n",
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
            for i in await app.database.admin.requests.get_all_pcodes():
                await message.answer(
                    f"<code>{i.name}</code>\n" f"Скидка: {i.discount}%\n" f"Кол-во активаций: {i.activations}\n",
                    parse_mode=aiogram.enums.ParseMode.HTML,
                    reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
                )
        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "К сожалению, промокодов нет",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
            )


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Удаление промокода",
)
async def cmd_delete_pcode(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Укажите название промокода, который хотите удалить",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.DeletePocde.name)


@router.message(app.admin.states.DeletePocde.name)
async def delete_pcode_name(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(name=message.text.lower())

    pcode = await app.database.requests.get_pcode(message.text.lower())
    await state.update_data(pcode=pcode)

    if pcode:
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Вы уверены, что выбрали верный промокод?\n\n"
            f"<b>{pcode.name.title()}</b>\n"
            f"Скидка: {pcode.discount}%\n"
            f"Активаций: {pcode.activations}",
            reply_markup=app.admin.keyboards.CHOICE_EDIT_ITEM,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )

    elif pcode is None:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Такого промокода не существует",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

    await state.set_state(app.admin.states.DeletePocde.choice)


@router.message(app.admin.states.DeletePocde.choice)
async def delete_pcode_choice(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    data = await state.get_data()

    if message.text == "Верно":
        async with app.database.models.async_session() as session:
            await app.database.admin.requests.delete_pcode(
                session,
                data.get("pcode").name,
            )
        await message.answer(
            app.messages.SUCCESS_MESSAGE + f"Промокод - {data.get('name')} успешно удален из базы данных",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

    elif message.text == "Неверно":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Отменяем процесс удаления промокода",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Создание промокода",
)
async def cmd_create_pcode(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Укажите название нового промокода",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.CreatePcode.name)


@router.message(app.admin.states.CreatePcode.name)
async def create_pcode_name(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(name=message.text.lower())

    await message.answer(
        app.messages.INFORMATION_MESSAGE
        + "Теперь необходимо указать процент скидки (укажите просто цифру, например: 25)",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.admin.states.CreatePcode.discount)


@router.message(app.admin.states.CreatePcode.discount)
async def create_pcode_discount(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(discount=message.text.lower())

    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Укажите число активаций (просто цифру)",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.admin.states.CreatePcode.activations)


@router.message(app.admin.states.CreatePcode.activations)
async def create_pcode_activations(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(activations=message.text.lower())
    author = await app.database.requests.get_user(message.from_user.id)
    await state.update_data(author=author.id)
    data = await state.get_data()

    async with app.database.models.async_session() as session:
        await app.database.admin.requests.add_pcode(session, data)

    await message.answer(
        app.messages.SUCCESS_MESSAGE + f"Вы создали промокод: <code>{data.get('name')}</code>\n"
        f"Число активаций: {data.get('activations')}\n"
        f"Скидка: {data.get('discount')}%",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
    )

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Удаление товара/услуги",
)
async def cmd_delete_item(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Укажите название товара, который хотите удалить",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.DeleteItem.item)


@router.message(app.admin.states.DeleteItem.item)
async def delete_item_item(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(item=message.text.lower())

    object = await app.database.admin.requests.get_editable_item(message.text.lower())
    await state.update_data(object_db=object)

    if object:
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Вы уверены, что выбрали верный товар/услугу?\n\n"
            f"<b>{object.title.title()}</b>\n"
            f"{object.description}\n\n"
            f"Цена: {object.price} руб.\n"
            f"Сроки выполнения: {object.deadline} дней",
            reply_markup=app.admin.keyboards.CHOICE_EDIT_ITEM,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )

    elif object is None:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Такого товара/услуги не существует",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

    await state.set_state(app.admin.states.DeleteItem.choice)


@router.message(app.admin.states.DeleteItem.choice)
async def delete_item_choice(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    data = await state.get_data()

    if message.text == "Верно":
        async with app.database.models.async_session() as session:
            await app.database.admin.requests.delete_item(
                session,
                data.get("object_db").title,
            )
        await message.answer(
            app.messages.SUCCESS_MESSAGE + f"Товар/услуга '{data.get('item')}' удален из базы данных",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

    elif message.text == "Неверно":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Отменяем процесс удаления товара/услуги",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Редактирование товара/услуги",
)
async def cmd_edit_item(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Введите название товара/услуги, которую бы вы хотели отредактировать "
        "(ВНИМАНИЕ: Вводите точное название товара, иначе в боте возникнет ошибка):",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.EditItem.item)


@router.message(app.admin.states.EditItem.item)
async def edit_item_itemobject(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(object=message.text.lower())

    object = await app.database.admin.requests.get_editable_item(message.text.lower())
    await state.update_data(object_db=object)

    if object:
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Отправляю выбранный вами на редакцию товар/услугу",
            parse_mode=aiogram.enums.ParseMode.HTML,
        )
        await message.answer_photo(
            object.image,
            caption=f"<b>{object.title.title()}</b>\n\n"
            f"{object.description}\n\n"
            f"Цена: {object.price} руб.\n"
            f"Срок выполнения: {object.deadline} дней",
            parse_mode=aiogram.enums.ParseMode.HTML,
        )
        await message.answer(
            app.messages.INFORMATION_MESSAGE
            + "Пожалуйста, убедитесь что вы выбрали <b>нужный товар/услугу</b> и нажмите соответствующую кнопку",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.CHOICE_EDIT_ITEM,
        )

        await state.set_state(app.admin.states.EditItem.choice)

    elif object is None:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Такого товара/услуги не существует",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

        await state.clear()


@router.message(app.admin.states.EditItem.choice)
async def edit_item_choice(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    if message.text == "Верно":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Отлично, тогда продолжаем редактирование. Что будем редактировать?\n"
            "<b>1) Название</b>\n"
            "<b>2) Описание</b>\n"
            "<b>3) Цена</b>\n"
            "<b>4) Сроки выполнения</b>\n"
            "<b>5) Фотографию</b>\n\n"
            "Вам необходимо прислать мне <b>ЦИФРУ</b> обозначающую значение, которое вы хотите отредактировать",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
        )

        await state.set_state(app.admin.states.EditItem.editable_object)
    else:
        await message.answer(
            app.messages.INFORMATION_MESSAGE + "Отменяем процесс редактирования товара/услуги",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

        await state.clear()


@router.message(app.admin.states.EditItem.editable_object)
async def edit_item_editable_object(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(editable_object=message.text.lower())
    data = await state.get_data()
    object = data.get("object_db")

    if message.text == "1":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + f"Ваш выбранный элемент - 1) Название\n"
            f"Название: {object.title}\n\n"
            "Теперь введите новое название для товара/услуги (регистр не имеет значение)",
            reply_markup=app.keyboards.CANCEL_OR_BACK,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )

    if message.text == "2":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + f"Ваш выбранный элемент - 2) Описание\n"
            f"Описание: {object.description}\n\n"
            "Теперь введите новое описание для товара/услуги <b>(регистр не имеет значение)</b>",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
        )

    if message.text == "3":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + f"Ваш выбранный элемент - 3) Цена\n"
            f"Цена: {object.price} руб.\n\n"
            "Теперь введите новую цену для товара/услуги <b>(в рублях)</b>",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
        )

    if message.text == "4":
        await message.answer(
            app.messages.INFORMATION_MESSAGE + f"Ваш выбранный элемент - 4) Сроки выполнения\n"
            f"Сроки выполнения: {object.deadline} дней\n\n"
            "Теперь введите новые сроки выполнения для товара/услуги <b>(кол-во дней)</b>",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
        )

    if message.text == "5":
        await message.answer_photo(
            object.image,
            caption=app.messages.INFORMATION_MESSAGE + "Ваш выбранный элемент - 5) Фотография\n\n"
            "Теперь отправьте новую фотографию для товара",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
        )

    await state.set_state(app.admin.states.EditItem.edit_item)


@router.message(app.admin.states.EditItem.edit_item)
async def edit_item_edit_item(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    data = await state.get_data()
    edit_item = message.text.lower() if message.text else None

    if data.get("editable_object") == "5":
        edit_item = message.photo[-2] if message.photo else None

    if edit_item is None:
        await state.clear()
        return

    async with app.database.models.async_session() as session:
        if data.get("editable_object") == "1":
            await app.database.admin.requests.updata_item_title(
                session,
                data.get("object_db").title,
                edit_item,
            )
            edit_object = "Название"
        elif data.get("editable_object") == "2":
            await app.database.admin.requests.updata_item_description(
                session,
                data.get("object_db").description,
                edit_item,
            )
            edit_object = "Описание"
        elif data.get("editable_object") == "3":
            await app.database.admin.requests.updata_item_price(
                session,
                data.get("object_db").price,
                edit_item,
            )
            edit_object = "Цена"
        elif data.get("editable_object") == "4":
            await app.database.admin.requests.updata_item_deadline(
                session,
                data.get("object_db").deadline,
                edit_item,
            )
            edit_object = "Сроки выполнения"
        elif data.get("editable_object") == "5":
            await app.database.admin.requests.updata_item_image(
                session,
                data.get("object_db").image,
                edit_item.file_id,
            )
            edit_object = "Фотография"

    await message.answer(
        app.messages.SUCCESS_MESSAGE + f"Вы успешно отредактировали товар - {data.get('object')}\n\n"
        f"Редактируемый объект - {data.get('editable_object')}) {edit_object}\n"
        f"Отредактировали на - {edit_item if isinstance(edit_item, str) else ''}\n",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
    )

    if isinstance(edit_item, aiogram.types.PhotoSize):
        await message.answer_photo(edit_item.file_id)

    await state.clear()


@router.message(
    app.admin.filters.IsAdmin(os.getenv("ADMIN_ID", "null_admins")),
    aiogram.F.text == "Создание товара/услуги",
)
async def cmd_create_item(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Введите название нового товара",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.CreateItem.title)


@router.message(app.admin.states.CreateItem.title)
async def create_item_title(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(title=message.text.lower())

    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Теперь необходимо ввести описание товара/услуги (макс. 250 символов)",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.admin.states.CreateItem.description)


@router.message(app.admin.states.CreateItem.description)
async def create_item_description(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(description=message.text.lower())

    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Прикрепите одно изображение к товару/услуге",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(app.admin.states.CreateItem.image)


@router.message(aiogram.F.photo, app.admin.states.CreateItem.image)
async def create_item_image(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(image=message.photo[-2])

    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Укажите цену за товар/услугу (в руб.)",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.admin.states.CreateItem.price)


@router.message(app.admin.states.CreateItem.price)
async def create_item_price(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(price=message.text.lower())

    await message.answer(
        app.messages.INFORMATION_MESSAGE + "Укажите примерное время выполнения в днях",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.admin.states.CreateItem.deadline)


@router.message(app.admin.states.CreateItem.deadline)
async def create_item_deadline(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await state.update_data(deadline=message.text.lower())
    data = await state.get_data()

    try:
        async with app.database.models.async_session() as session:
            await app.database.requests.add_item(session, data)

        response_text = (
            f"<b>Отлично, товар создан:</b>\n\n"
            f"Название: {data.get('title')}\n\n"
            f"Описание: {data.get('description')}\n\n"
            f"Цена: {data.get('price')} руб.\n"
            f"Дедлайн: {data.get('deadline')} дней"
        )
        await message.answer_photo(
            data.get("image").file_id,
            caption=app.messages.INFORMATION_MESSAGE + response_text,
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )

        await state.clear()
    except ValueError:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Кажется, вы допустили ошибку при создании товара/услуги\n"
            "Вы можете попробовать создать товар/услугу заново",
            parse_mode=aiogram.enums.ParseMode.HTML,
            reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        )
