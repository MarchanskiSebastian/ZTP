"""Read side (CQRS): queries never change state and return read models, not ORM objects."""
from sqlalchemy.orm import Session

from app.cart import repository as repo
from app.cart.model import Cart, CartLine, Order, OrderSummary
from app.REST.service.product_validators import NotFoundError


def get_cart(db: Session, user_id: int) -> Cart:
    lines = [
        CartLine(product_id=i.product_id, name=i.product.name, unit_price=float(i.product.price),
                 quantity=i.quantity, line_total=float(i.product.price * i.quantity))
        for i in repo.get_cart_items(db, user_id)
    ]
    return Cart(items=lines, total=round(sum(line.line_total for line in lines), 2))


def list_orders(db: Session, user_id: int) -> list[OrderSummary]:
    return [OrderSummary.model_validate(o) for o in repo.get_orders(db, user_id)]


def get_order(db: Session, user_id: int, order_id: int) -> Order:
    order = repo.get_order(db, user_id, order_id)
    if order is None:
        raise NotFoundError("Zamówienie nie istnieje.")
    return Order.model_validate(order)
