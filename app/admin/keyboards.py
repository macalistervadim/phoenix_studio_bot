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
        [
            aiogram.types.KeyboardButton(text="Создание гифта(-ов)"),
        ],
        [
            aiogram.types.KeyboardButton(text="Статистика"),
        ],
        [
            aiogram.types.KeyboardButton(text="Черный список"),
            aiogram.types.KeyboardButton(text="Занести в ЧС"),
            aiogram.types.KeyboardButton(text="Вынести из ЧС"),
        ],
        [
            aiogram.types.KeyboardButton(text="Отправить реквизиты"),
            aiogram.types.KeyboardButton(text="Сделать рассылку"),
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
        [aiogram.types.KeyboardButton(text="Ответить")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню",
)
