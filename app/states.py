import aiogram.fsm.state


class CreateOrder(aiogram.fsm.state.StatesGroup):
    pcode = aiogram.fsm.state.State()


class CreateTicket(aiogram.fsm.state.StatesGroup):
    question = aiogram.fsm.state.State()


class CreateGiftCard(aiogram.fsm.state.StatesGroup):
    amount = aiogram.fsm.state.State()
    sckreenshot = aiogram.fsm.state.State()


class AnswerTicket(aiogram.fsm.state.StatesGroup):
    message = aiogram.fsm.state.State()
