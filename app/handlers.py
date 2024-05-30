import os

import aiogram

import app.admin
import app.admin.keyboards
import app.database.models
import app.database.requests
import app.keyboards
import app.messages
import app.states as st
import app.states


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


@router.message(aiogram.F.text == "🎁 Подарочные сертификаты")
async def cmd_giftcards(
    message: aiogram.types.Message,
):
    await message.answer(
        app.messages.GIFT_CARDS,
        reply_markup=app.keyboards.GIFT_CARDS,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )


@router.message(aiogram.F.text == "📬 Создать сертификат")
async def cmd_create_giftcard(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    await message.answer(
        "♻️ Для создания подарочного сертификата, пожалуйста, укажите сумму будущего сертификата (500-25000 руб.)\n"
        "Не указывайте любые другие символы, кроме цифр - иначе бот выдаст ошибку",
        reply_markup=app.keyboards.CANCEL_OR_BACK,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )

    await state.set_state(st.CreateGiftCard.amount)


@router.message(st.CreateGiftCard.amount)
async def cmd_create_giftcard_amount(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
):
    if 500 <= int(message.text) <= 25000:
        await state.update_data(amount=message.text.lower())
        await message.answer(
            f"♻️ Теперь необходимо оплатить сумму сертификата: {message.text} руб. Пересылаю вам реквизиты...\n\n"
            "После оплаты вам необходимо прикрепить соответствующий скриншот с платежом - после чего, я переведу"
            " вас на Агента поддержки, который выдаст вам код от сертификата",
            reply_markup=app.keyboards.CANCEL_OR_BACK,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )
        await message.answer(
            app.messages.PAYMENT,
            reply_markup=app.keyboards.CANCEL_OR_BACK,
            parse_mode=aiogram.enums.ParseMode.HTML,
        )

        await state.set_state(st.CreateGiftCard.sckreenshot)
    else:
        await message.answer(
            app.messages.ERORR_MESSAGE + "Сумма подарочного сертификата должна быть в диапазоне от 500 до 25000 руб.",
            parse_mode=aiogram.enums.ParseMode.HTML,
        )
        await state.set_state(st.CreateGiftCard.amount)
        return


@router.message(aiogram.F.photo, st.CreateGiftCard.sckreenshot)
async def cmd_create_giftcard_screenshot(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    async with app.database.models.async_session() as session:
        await state.update_data(sckreen=message.photo[-1].file_id)

        owner = await app.database.requests.get_user(message.from_user.id)
        await state.update_data(owner=owner.id)

        gift_cards = await app.database.requests.get_inactive_giftcards_user(owner.id)
        if not gift_cards:
            data = await state.get_data()
            new_gift = await app.database.requests.add_giftcard(session, data)
            session.commit()

            keyboard = aiogram.utils.keyboard.InlineKeyboardBuilder()
            keyboard.add(
                aiogram.types.InlineKeyboardButton(
                    text="Подтвердить выдачу",
                    callback_data=f"gift_{str(new_gift.id)}",
                ),
            )

            user_profile_link = f'<a href="tg://user?id={message.from_user.id}">Профиль пользователя</a>'
            admin_id = os.getenv("ADMIN_ID", "no_admin")
            caption = (
                f"❗️ Подтвердите выдачу подарочного сертификат на сумму {data.get('amount')} руб."
                f" и выдайте пользователю: {user_profile_link}\n"
            )

            await bot.send_photo(
                chat_id=admin_id,
                photo=data.get("sckreen"),
                caption=caption,
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=keyboard.as_markup(),
            )

            await message.answer(
                "✅ Вы отметили, что <b>выполнили оплату</b>...\n\n"
                "Я уже передал информацию Агенту Поддержки. Скоро он <b>свяжется с вами и выдаст код</b>"
                f" от сертификата на сумму: {data.get('amount')} руб.\n\n"
                "💚 Спасибо, что доверяете PHOENIX STUDIO\n",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.keyboards.MAIN,
            )
        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "Вы уже подали заявку на выдачу нового сертификата."
                " До его выдачи вы не можете зарегистрировать новый",
                reply_markup=app.keyboards.MAIN,
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        await state.clear()


@router.message(aiogram.F.text == "🎀 Мои сертификаты")
async def cmd_mygiftcards(message: aiogram.types.Message):
    async with app.database.models.async_session():
        user = await app.database.requests.get_user(message.from_user.id)
        active_giftcards_user = await app.database.requests.get_active_giftcards_user(
            user.id,
        )
        inactive_giftcards_user = await app.database.requests.get_inactive_giftcards_user(
            user.id,
        )

        if active_giftcards_user or inactive_giftcards_user:
            await message.answer(
                "♻️ Вывожу ваши подарочные карты...",
                reply_markup=app.keyboards.MAIN,
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
            for i in active_giftcards_user:
                is_active = "Да" if i.is_active else "Нет"
                await message.answer(
                    f"<code>{i.name}</code>\n"
                    f"Сумма: {i.amount} руб.\n"
                    f"Активирован: {is_active}\n\n"
                    "Скопируйте код, <b>нажав на его название</b> и отправьте другу!"
                    " При оплате он сможет им воспользоваться",
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )
            for i in inactive_giftcards_user:
                is_active = "Да" if i.is_active else "Нет"
                await message.answer(
                    f"<b>Ожидает выдачи Агентом Поддержки</b>\n"
                    f"Сумма: {i.amount} руб.\n"
                    f"Активирован: {is_active}",
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )
        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "У вас нет созданных подарочных сертификатов",
                parse_mode=aiogram.enums.ParseMode.HTML,
            )


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
                reply_markup=app.keyboards.CANCEL_ORDER_OR_CLOSE_TICKET,
            )

            user_profile_link = f'<a href="tg://user?id={message.from_user.id}">Профиль пользователя</a>'
            await bot.send_message(
                os.getenv("ADMIN_ID", "no_admin"),
                f"❗️ Пришел новый <b>тикет №{ticket_id.id}</b>\n" f"{user_profile_link}\n" f"Сообщение: {message.text}",
                parse_mode=aiogram.enums.ParseMode.HTML,
            )

        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "Кажется, у вас уже есть созданный тикет\n",
                reply_markup=app.keyboards.CANCEL_ORDER_OR_CLOSE_TICKET,
                parse_mode=aiogram.enums.ParseMode.HTML,
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

            await message.answer_photo(
                i.image,
                caption=f"<b>{i.title.title()}</b>\n\n"
                f"{i.description}\n\n"
                f"Цена за услугу: {i.price} руб.\n"
                f"Срок выполнения: {i.deadline} дней",
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=keyboard.as_markup(),
            )

    else:
        await message.answer(
            app.messages.ERORR_MESSAGE + "К сожалению, каталог пуст",
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
                    app.messages.ERORR_MESSAGE + f"К сожалению, промокода {message.text.lower()} - не существует. "
                    "Повторите попытку или введите 0",
                    parse_mode=aiogram.enums.ParseMode.HTML,
                )
                await state.set_state(st.CreateOrder.pcode)
                return

        data = await state.get_data()
        if await app.database.requests.add_order(session, data):
            await app.database.requests.update_user(
                session,
                tg_id=message.from_user.id,
            )
            await message.answer(
                app.messages.SUCC_CREATE_ORDER_MESSAGE,
                parse_mode=aiogram.enums.ParseMode.HTML,
                reply_markup=app.keyboards.CANCEL_ORDER_OR_CLOSE_TICKET,
            )

            user_profile_link = f'<a href="tg://user?id={message.from_user.id}">Профиль пользователя</a>'
            discount_info = f"ПРОМОКОД: {data.get('pcode')} - {pcode.discount}% скидки" if pcode else ""
            item = await app.database.requests.get_item(data.get("item_id"))
            await bot.send_message(
                os.getenv("ADMIN_ID", "admin_id"),
                f"❗️ Пришел новый заказ\n\n{user_profile_link}\n" f"Товар: {item.title.title()}\n" f"{discount_info}",
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "Похоже, у вас уже есть действительный заказ",
                parse_mode=aiogram.enums.ParseMode.HTML,
            )

        await state.clear()


@router.message(aiogram.F.text == "Отменить заказ")
async def cmd_cancel_order(message: aiogram.types.Message):
    async with app.database.models.async_session():
        user = await app.database.requests.get_user(message.from_user.id)
        if await app.database.requests.get_order(user.id):
            await app.database.requests.close_order_from_user(user.id)

            await message.answer(
                "♻️ Ваш заказ <b>успешно отменен</b>",
                reply_markup=app.keyboards.MAIN,
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "У вас нет активных заказов",
                parse_mode=aiogram.enums.ParseMode.HTML,
            )


@router.message(aiogram.F.text == "Закрыть тикет")
async def cmd_close_ticket(message: aiogram.types.Message):
    async with app.database.models.async_session():
        user = await app.database.requests.get_user(message.from_user.id)
        if await app.database.requests.get_tickets_user(user.id):
            await app.database.requests.close_ticket_from_user(user.id)

            await message.answer(
                "♻️ Ваш тикет <b>успешно закрыт</b>",
                reply_markup=app.keyboards.MAIN,
                parse_mode=aiogram.enums.ParseMode.HTML,
            )
        else:
            await message.answer(
                app.messages.ERORR_MESSAGE + "У вас нет активных тикетов",
                parse_mode=aiogram.enums.ParseMode.HTML,
            )


@router.callback_query(aiogram.F.data.startswith("score_"))
async def score_selected(
    callback: aiogram.types.CallbackQuery,
):
    score = callback.data.replace("score_", "")

    async with app.database.models.async_session() as session:
        await app.database.requests.add_score(session, score)

    await callback.message.delete()
    await callback.message.answer("⭐️ Благодарим за обратную связь!")


@router.callback_query(aiogram.F.data.startswith("answer_ticket_"))
async def ticket_answer(
    callback: aiogram.types.CallbackQuery,
    state: aiogram.fsm.context.FSMContext,
):
    ticket_id = callback.data.replace("answer_ticket_", "")
    await state.update_data(ticket_id=ticket_id, keyboard_message_id=callback.message.message_id)

    await callback.message.answer(
        f"Введите сообщение для Агента Поддержки <b>(по тикету №{ticket_id})</b>."
        " Также при необходимости <b>прикрепите документ/фотографию</b> или иные средства, "
        "которые помогут в решение вашей проблемы",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=app.keyboards.CANCEL_OR_BACK,
    )

    await state.set_state(app.states.AnswerTicket.message)


@router.message(app.states.AnswerTicket.message)
async def ticket_answer_message(
    message: aiogram.types.Message,
    state: aiogram.fsm.context.FSMContext,
    bot: aiogram.Bot,
):
    data = await state.get_data()

    admin_id = int(os.getenv("ADMIN_ID", "no_admin"))

    await message.answer(
        app.messages.SUCCESS_MESSAGE + "Сообщение отправлено Агенту Поддержки. Ожидайте обратной связи",
        parse_mode=aiogram.enums.ParseMode.HTML,
        reply_markup=aiogram.types.ReplyKeyboardRemove(),
    )
    keyboard_message_id = data.get("keyboard_message_id")
    await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=keyboard_message_id, reply_markup=None)
    await bot.send_message(
        admin_id,
        app.messages.NOTIFICATION_MESSAGE
        + f"Пришло новое сообщение от пользователя по тикету №{data.get('ticket_id')}",
        reply_markup=app.admin.keyboards.ADMIN_COMMANDS,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )
    await bot.forward_message(admin_id, message.chat.id, message.message_id)

    async with app.database.models.async_session():
        pass

    await state.clear()


@router.message(aiogram.F.text == "✅ Подписался")
async def cmd_subscription(message: aiogram.types.Message):
    await message.answer(
        app.messages.SUBSCRIPTION_SUCC_MESSAGE,
        reply_markup=app.keyboards.MAIN,
        parse_mode=aiogram.enums.ParseMode.HTML,
    )
