import aiogram.fsm.state


class CreateItem(aiogram.fsm.state.StatesGroup):
    title = aiogram.fsm.state.State()
    description = aiogram.fsm.state.State()
    image = aiogram.fsm.state.State()
    price = aiogram.fsm.state.State()
    deadline = aiogram.fsm.state.State()


class EditItem(aiogram.fsm.state.StatesGroup):
    item = aiogram.fsm.state.State()
    choice = aiogram.fsm.state.State()
    editable_object = aiogram.fsm.state.State()
    edit_item = aiogram.fsm.state.State()


class DeleteItem(aiogram.fsm.state.StatesGroup):
    item = aiogram.fsm.state.State()
    choice = aiogram.fsm.state.State()


class CreatePcode(aiogram.fsm.state.StatesGroup):
    name = aiogram.fsm.state.State()
    discount = aiogram.fsm.state.State()
    activations = aiogram.fsm.state.State()


class DeletePocde(aiogram.fsm.state.StatesGroup):
    name = aiogram.fsm.state.State()
    choice = aiogram.fsm.state.State()


class EditOrder(aiogram.fsm.state.StatesGroup):
    order_id = aiogram.fsm.state.State()
    edit_status = aiogram.fsm.state.State()
    edit_object = aiogram.fsm.state.State()


class EditTicket(aiogram.fsm.state.StatesGroup):
    ticket_id = aiogram.fsm.state.State()
    edit_status = aiogram.fsm.state.State()
    answer_ticket = aiogram.fsm.state.State()


class AdminCreateGiftCard(aiogram.fsm.state.StatesGroup):
    count = aiogram.fsm.state.State()
    amount = aiogram.fsm.state.State()
