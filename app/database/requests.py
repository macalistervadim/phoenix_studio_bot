import sqlalchemy

import app.database.models
import app.database.requests


async def add_user(session: sqlalchemy.ext.asyncio.AsyncSession, tg_id):
    try:
        new_user = app.database.models.User(tg_id=tg_id)
        session.add(new_user)
        await session.commit()
    except sqlalchemy.exc.IntegrityError:
        pass


async def update_user(
    session: sqlalchemy.ext.asyncio.AsyncSession,
    tg_id,
):
    try:
        await session.execute(
            sqlalchemy.update(app.database.models.User)
            .where(app.database.models.User.tg_id == tg_id)
            .values(waiting_order=True),
        )
        await session.commit()
    except sqlalchemy.exc.IntegrityError:
        pass


async def update_pcode(name):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.Pcode).where(app.database.models.Pcode.name == name),
        )
        pcode = result.scalars().first()

        if pcode.activations <= 0:
            return False

        # Обновляем количество активаций
        await session.execute(
            sqlalchemy.update(app.database.models.Pcode)
            .where(app.database.models.Pcode.name == name)
            .values(activations=pcode.activations - 1),
        )
        await session.commit()


async def update_giftcard(name):
    async with app.database.models.async_session() as session:
        await session.execute(
            sqlalchemy.update(app.database.models.GiftCard)
            .where(app.database.models.GiftCard.name == name)
            .values(is_active=True),
        )
        await session.commit()


async def close_ticket_from_user(user_id):
    try:
        async with app.database.models.async_session() as session:
            await session.execute(
                sqlalchemy.update(app.database.models.User)
                .where(app.database.models.User.id == user_id)
                .values(waiting_support=False),
            )
            await session.execute(
                sqlalchemy.update(app.database.models.Ticket)
                .where(app.database.models.Ticket.user == user_id)
                .values(status="COMPLETED"),
            )
            await session.commit()

    except sqlalchemy.exc.IntegrityError:
        await session.rollback()
        return False


async def get_pcode(name):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.Pcode).filter_by(name=name),
        )
        if result:
            return result.scalars().first()
        else:
            return False


async def get_item(id):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.Catalog).filter_by(id=int(id)),
        )
        if result:
            return result.scalars().first()
        else:
            return False


async def get_ticket(user_id):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.Ticket)
            .filter_by(user=user_id)
            .filter(app.database.models.Ticket.status == "CREATED"),
        )
        return result.scalars().first()


async def get_giftcard(user_id):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.Ticket)
            .filter_by(user=user_id)
            .filter(app.database.models.Ticket.status == "CREATED"),
        )
        return result.scalars().first()


async def get_order(user_id):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.Order)
            .filter_by(user=user_id)
            .filter(
                app.database.models.Order.status == "CREATED" and app.database.models.Order.status == "IN_PROGRESS",
            ),
        )
        return result.scalars().first()


async def add_order(session: sqlalchemy.ext.asyncio.AsyncSession, data):
    try:
        # Проверяем, есть ли уже заказ у данного пользователя
        existing_order = await get_order(data.get("user"))
        if existing_order:
            return False
        else:
            item = app.database.models.Order(
                product=int(data.get("item_id")),
                user=data.get("user"),
                pcode=data.get("pcode").id if data.get("pcode") != "0" else None,
                giftcard=data.get("giftcard").id if data.get("giftcard") is not None else None,
            )
            session.add(item)
            await session.commit()
            return True
    except sqlalchemy.exc.IntegrityError:
        await session.rollback()
        return False


async def close_order_from_user(user_id):
    try:
        async with app.database.models.async_session() as session:
            await session.execute(
                sqlalchemy.update(app.database.models.User)
                .where(app.database.models.User.id == user_id)
                .values(waiting_order=False),
            )
            await session.execute(
                sqlalchemy.update(app.database.models.Order)
                .where(app.database.models.Order.user == user_id)
                .values(status="COMPLETED"),
            )
            await session.commit()

    except sqlalchemy.exc.IntegrityError:
        await session.rollback()
        return False


async def add_item(session: sqlalchemy.ext.asyncio.AsyncSession, data):
    try:
        item = app.database.models.Catalog(
            title=data.get("title"),
            description=data.get("description"),
            image=data.get("image").file_id,
            price=int(data.get("price")),
            deadline=int(data.get("deadline")),
        )
        session.add(item)
        await session.commit()
    except sqlalchemy.exc.IntegrityError:
        pass


async def add_score(session: sqlalchemy.ext.asyncio.AsyncSession, score):
    try:
        score = app.database.models.Rating(
            score=int(score),
        )
        session.add(score)
        await session.commit()
    except sqlalchemy.exc.IntegrityError:
        pass


async def add_giftcard(session: sqlalchemy.ext.asyncio.AsyncSession, data):
    try:
        giftcard = app.database.models.GiftCard(
            amount=int(data.get("amount")),
            owner=data.get("owner"),
        )
        session.add(giftcard)
        await session.commit()
        await session.refresh(giftcard)
        return giftcard
    except sqlalchemy.exc.IntegrityError:
        return None


async def get_active_giftcards_user(user_id):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.GiftCard).where(
                (app.database.models.GiftCard.owner == user_id)
                & (
                    sqlalchemy.or_(
                        app.database.models.GiftCard.status == "COMPLETED",
                    )
                ),
            ),
        )
        return result.scalars().all()


async def get_inactive_giftcards_user(user_id):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.GiftCard).where(
                (app.database.models.GiftCard.owner == user_id)
                & (
                    sqlalchemy.or_(
                        app.database.models.GiftCard.status == "CREATED",
                    )
                ),
            ),
        )
        return result.scalars().all()


async def get_tickets_user(user_id):
    async with app.database.models.async_session() as session:
        result = await session.execute(
            sqlalchemy.select(app.database.models.Ticket).where(
                (app.database.models.Ticket.user == user_id)
                & (
                    sqlalchemy.or_(
                        app.database.models.Ticket.status == "CREATED",
                        app.database.models.Ticket.status == "IN_PROGRESS",
                    )
                ),
            ),
        )
        return result.scalars().all()


async def add_ticket(session: sqlalchemy.ext.asyncio.AsyncSession, data):
    try:
        ticket = app.database.models.Ticket(
            user=data.get("user"),
            question=data.get("question"),
        )
        session.add(ticket)
        await session.commit()
    except sqlalchemy.exc.IntegrityError:
        await session.rollback()
        return None


async def update_user_ticket(
    session: sqlalchemy.ext.asyncio.AsyncSession,
    tg_id,
):
    try:
        await session.execute(
            sqlalchemy.update(app.database.models.User)
            .where(app.database.models.User.tg_id == tg_id)
            .values(waiting_support=True),
        )
        await session.commit()
    except sqlalchemy.exc.IntegrityError:
        await session.rollback()
        return None


async def get_catalog():
    async with app.database.models.async_session() as session:
        result = await session.execute(sqlalchemy.select(app.database.models.Catalog))
        return result.scalars().all()


async def get_user(tg_id):
    async with app.database.models.async_session() as session:
        result = await session.scalar(
            sqlalchemy.select(app.database.models.User).where(
                app.database.models.User.tg_id == tg_id,
            ),
        )
        return result


async def get_gift(gift_id):
    async with app.database.models.async_session() as session:
        result = await session.scalar(
            sqlalchemy.select(app.database.models.GiftCard).where(
                app.database.models.GiftCard.id == gift_id,
            ),
        )
        return result
