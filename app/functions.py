import app.admin
import app.admin.handlers
import app.admin.keyboards
import app.database.models
import app.database.requests
import app.keyboards
import app.messages
import app.states


async def get_giftcards_message(user_id):
    async with app.database.models.async_session():
        user = await app.database.requests.get_user(user_id)
        active_giftcards_user = await app.database.requests.get_active_giftcards_user(user.id)
        inactive_giftcards_user = await app.database.requests.get_inactive_giftcards_user(user.id)

        messages = []

        if active_giftcards_user or inactive_giftcards_user:
            messages.append(
                (app.messages.INFORMATION_MESSAGE + "Вывожу ваши подарочные сертификаты", app.keyboards.MAIN),
            )
            for i in active_giftcards_user:
                is_active = "Да" if i.is_active else "Нет"
                messages.append(
                    (
                        f"<code>{i.name}</code>\n"
                        f"Сумма: {i.amount} руб.\n"
                        f"Активирован: {is_active}\n\n"
                        "Скопируйте код, <b>нажав на его название</b> и отправьте другу!"
                        " При оплате он сможет им воспользоваться",
                        app.keyboards.MAIN,
                    ),
                )
            for i in inactive_giftcards_user:
                is_active = "Да" if i.is_active else "Нет"
                messages.append(
                    (
                        f"<b>Ожидает выдачи Агентом Поддержки</b>\n"
                        f"Сумма: {i.amount} руб.\n"
                        f"Активирован: {is_active}",
                        app.keyboards.MAIN,
                    ),
                )
        else:
            messages.append(
                (app.messages.ERORR_MESSAGE + "У вас нет созданных подарочных сертификатов", app.keyboards.MAIN),
            )

        return messages
