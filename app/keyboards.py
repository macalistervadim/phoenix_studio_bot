import aiogram
import aiogram.utils.keyboard


MAIN = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [
            aiogram.types.KeyboardButton(text="📚 Каталог"),
            aiogram.types.KeyboardButton(text="📪 Контакты"),
        ],
        [
            aiogram.types.KeyboardButton(text="📨 Тех. поддержка"),
            aiogram.types.KeyboardButton(text="💚 Вывести команды"),
        ],
        [
            aiogram.types.KeyboardButton(text="🎁 Подарочные сертификаты"),
        ],
    ],
    resize_keyboard=True,
    row_width=2,
    input_field_placeholder="Выберите пункт меню",
)

SUBSCRIPTION = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="✅ Подписался")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)

CANCEL_OR_BACK = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="Отменить")],
        [aiogram.types.KeyboardButton(text="Назад")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)

CANCEL_ORDER_OR_CLOSE_TICKET = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="Отменить заказ")],
        [aiogram.types.KeyboardButton(text="Закрыть тикет")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)

GIFT_CARDS = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="🎀 Мои сертификаты")],
        [aiogram.types.KeyboardButton(text="📬 Создать сертификат")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)
