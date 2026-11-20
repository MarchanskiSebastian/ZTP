from datetime import date

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session, selectinload

from app.cart.model import CartItemORM, OrderORM, ProcessedCommandORM
from app.REST.model.product_orm import ProductORM


def get_cart_items(db: Session, user_id: int) -> list[CartItemORM]:
    query = (
        select(CartItemORM)
        .options(selectinload(CartItemORM.product))
        .where(CartItemORM.user_id == user_id)
        .order_by(CartItemORM.product_id)
    )
    return list(db.execute(query).scalars().all())


def get_cart_item(db: Session, user_id: int, product_id: int) -> CartItemORM | None:
    query = select(CartItemORM).where(CartItemORM.user_id == user_id, CartItemORM.product_id == product_id)
    return db.execute(query).scalar_one_or_none()


def get_product_for_update(db: Session, product_id: int) -> ProductORM | None:
    return db.execute(select(ProductORM).where(ProductORM.id == product_id).with_for_update()).scalar_one_or_none()


def lock_products(db: Session, product_ids: list[int]) -> dict[int, ProductORM]:
    # always lock in id order: two concurrent checkouts cannot deadlock
    query = select(ProductORM).where(ProductORM.id.in_(product_ids)).order_by(ProductORM.id).with_for_update()
    return {p.id: p for p in db.execute(query).scalars().all()}


def clear_cart(db: Session, user_id: int) -> None:
    db.execute(delete(CartItemORM).where(CartItemORM.user_id == user_id))


def next_order_number(db: Session, day: date) -> str:
    seq = db.execute(
        text(
            "INSERT INTO order_counters (day, last) VALUES (:day, 1) "
            "ON CONFLICT (day) DO UPDATE SET last = order_counters.last + 1 RETURNING last"
        ),
        {"day": day},
    ).scalar_one()
    return f"ZAM-{day:%Y%m%d}-{seq:06d}"


def get_order(db: Session, user_id: int, order_id: int, lock: bool = False) -> OrderORM | None:
    query = (
        select(OrderORM)
        .options(selectinload(OrderORM.items))
        .where(OrderORM.id == order_id, OrderORM.user_id == user_id)  # other users' orders are invisible
    )
    if lock:
        query = query.with_for_update(of=OrderORM)
    return db.execute(query).scalar_one_or_none()


def get_orders(db: Session, user_id: int) -> list[OrderORM]:
    query = select(OrderORM).where(OrderORM.user_id == user_id).order_by(OrderORM.id.desc())
    return list(db.execute(query).scalars().all())


def get_processed_command(db: Session, user_id: int, key: str) -> ProcessedCommandORM | None:
    query = select(ProcessedCommandORM).where(
        ProcessedCommandORM.user_id == user_id, ProcessedCommandORM.idempotency_key == key
    )
    return db.execute(query).scalar_one_or_none()


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj
