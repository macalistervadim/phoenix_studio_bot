import aiogram.fsm.state


class CreateOrder(aiogram.fsm.state.StatesGroup):
    pcode = aiogram.fsm.state.State()


class CreateTicket(aiogram.fsm.state.StatesGroup):
    question = aiogram.fsm.state.State()
