import aiogram


ADMIN_COMMANDS = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [
            aiogram.types.KeyboardButton(text="Создание товара/услуги"),
            aiogram.types.KeyboardButton(text="Редактирование товара/услуги"),
            aiogram.types.KeyboardButton(text="Удаление товара/услуги"),
        ],
        [
            aiogram.types.KeyboardButton(text="Создание промокода"),
            aiogram.types.KeyboardButton(text="Удаление промокода"),
            aiogram.types.KeyboardButton(text="Список промокодов"),
        ],
        [
            aiogram.types.KeyboardButton(text="Список заказов"),
            aiogram.types.KeyboardButton(text="Список тикетов"),
        ],
    ],
    row_width=3,
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)

CHOICE_EDIT_ITEM = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="Верно")],
        [aiogram.types.KeyboardButton(text="Неверно")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)

CHOICE_EDIT_ORDER = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="Сменить статус")],
        [aiogram.types.KeyboardButton(text="Удалить")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)

CHOICE_EDIT_ORDER_STATUS = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="CREATED")],
        [aiogram.types.KeyboardButton(text="IN_PROGRESS")],
        [aiogram.types.KeyboardButton(text="COMPLETED")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)

CHOICE_EDIT_TICKET = aiogram.types.ReplyKeyboardMarkup(
    keyboard=[
        [aiogram.types.KeyboardButton(text="Сменить статус")],
        [aiogram.types.KeyboardButton(text="Удалить")],
        [aiogram.types.KeyboardButton(text="Ответить")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)
