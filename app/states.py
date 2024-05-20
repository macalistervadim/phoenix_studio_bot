import aiogram.fsm.state


class CreateOrder(aiogram.fsm.state.StatesGroup):
    pcode = aiogram.fsm.state.State()
