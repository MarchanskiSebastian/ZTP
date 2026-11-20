"""Write side (CQRS): every state change is a Command object executed by its Handler through `execute()`."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.cart import repository as repo
from app.cart.model import (
    ORDER_TRANSITIONS,
    CartItemORM,
    OrderItemORM,
    OrderORM,
    OrderStatus,
    ProcessedCommandORM,
)
from app.identity.repository import get_user_by_id
from app.REST.data.notification_repository import add_notification
from app.REST.model.notification_orm import Channel, NotificationORM, Status
from app.REST.service.product_validators import ConflictError, NotFoundError, ValidationError


# ---- Commands: plain immutable data describing the intent ----

@dataclass(frozen=True)
class AddToCart:
    user_id: int
    product_id: int
    quantity: int


@dataclass(frozen=True)
class SetCartQuantity:
    user_id: int
    product_id: int
    quantity: int


@dataclass(frozen=True)
class RemoveFromCart:
    user_id: int
    product_id: int


@dataclass(frozen=True)
class Checkout:
    user_id: int


@dataclass(frozen=True)
class CompleteOrder:
    user_id: int
    order_id: int


@dataclass(frozen=True)
class CancelOrder:
    user_id: int
    order_id: int


# ---- Handlers: one per command, they do not commit (execute() owns the transaction) ----

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_stock(db: Session, product_id: int, quantity: int):
    if quantity <= 0:
        raise ValidationError("Ilość musi być większa od 0.")
    product = repo.get_product_for_update(db, product_id)
    if product is None:
        raise NotFoundError("Produkt nie istnieje.")
    if quantity > product.quantity:
        raise ConflictError(f"Niewystarczająca ilość w magazynie (dostępne: {product.quantity}).")


def handle_add_to_cart(db: Session, c: AddToCart) -> dict:
    if c.quantity <= 0:
        raise ValidationError("Ilość musi być większa od 0.")
    item = repo.get_cart_item(db, c.user_id, c.product_id)
    new_quantity = c.quantity + (item.quantity if item else 0)
    _check_stock(db, c.product_id, new_quantity)  # the whole cart line must fit in stock
    if item:
        item.quantity = new_quantity
    else:
        repo.add(db, CartItemORM(user_id=c.user_id, product_id=c.product_id, quantity=new_quantity))
    return {"product_id": c.product_id, "quantity": new_quantity}


def handle_set_cart_quantity(db: Session, c: SetCartQuantity) -> dict:
    item = repo.get_cart_item(db, c.user_id, c.product_id)
    if item is None:
        raise NotFoundError("Produktu nie ma w koszyku.")
    _check_stock(db, c.product_id, c.quantity)
    item.quantity = c.quantity
    return {"product_id": c.product_id, "quantity": c.quantity}


def handle_remove_from_cart(db: Session, c: RemoveFromCart) -> dict:
    item = repo.get_cart_item(db, c.user_id, c.product_id)
    if item is None:
        raise NotFoundError("Produktu nie ma w koszyku.")
    db.delete(item)
    return {"product_id": c.product_id}


def handle_checkout(db: Session, c: Checkout) -> dict:
    items = repo.get_cart_items(db, c.user_id)
    if not items:
        raise ValidationError("Koszyk jest pusty.")
    products = repo.lock_products(db, [i.product_id for i in items])
    # aggregate + validate everything before changing anything
    for i in items:
        if i.quantity > products[i.product_id].quantity:
            raise ConflictError(
                f"Niewystarczająca ilość produktu {products[i.product_id].name} "
                f"(w koszyku {i.quantity}, dostępne {products[i.product_id].quantity})."
            )
    lines = [(products[i.product_id], i.quantity) for i in items]
    total = sum((p.price * q for p, q in lines), Decimal("0"))

    order = repo.add(
        db,
        OrderORM(
            number=repo.next_order_number(db, _now().date()),
            user_id=c.user_id,
            status=OrderStatus.PENDING.value,
            total=total,
        ),
    )
    for product, quantity in lines:
        # snapshot: name and price are copied, later product edits do not change the order
        db.add(OrderItemORM(order_id=order.id, product_id=product.id, product_name=product.name,
                            unit_price=product.price, quantity=quantity, line_total=product.price * quantity))
        product.quantity -= quantity  # stock is reserved at checkout
    repo.clear_cart(db, c.user_id)
    return {"order_id": order.id}


def change_order_status(order: OrderORM, new: OrderStatus) -> None:
    current = OrderStatus(order.status)
    if new not in ORDER_TRANSITIONS[current]:
        raise ConflictError(f"Niedozwolona zmiana statusu zamówienia: {current.value} -> {new.value}.")
    order.status = new.value


def _locked_order(db: Session, user_id: int, order_id: int) -> OrderORM:
    order = repo.get_order(db, user_id, order_id, lock=True)
    if order is None:
        raise NotFoundError("Zamówienie nie istnieje.")
    return order


def handle_complete_order(db: Session, c: CompleteOrder) -> dict:
    order = _locked_order(db, c.user_id, c.order_id)
    change_order_status(order, OrderStatus.COMPLETED)
    order.completed_at = _now()
    user = get_user_by_id(db, c.user_id)
    # same transaction as the status change (outbox): the worker of the notifications module sends them;
    # idempotency_key is UNIQUE, so an order can never get a duplicate notification
    for channel, recipient in ((Channel.EMAIL, user.email), (Channel.PUSH, f"ztp-user-{user.id}")):
        add_notification(db, NotificationORM(
            channel=channel.value,
            recipient=recipient,
            subject=f"Zamówienie {order.number} zrealizowane",
            message=f"Twoje zamówienie {order.number} na kwotę {order.total} zł zostało zrealizowane.",
            status=Status.PENDING.value,
            scheduled_at=_now(),
            idempotency_key=f"order-{order.id}-{channel.value}",
        ))
    return {"order_id": order.id}


def handle_cancel_order(db: Session, c: CancelOrder) -> dict:
    order = _locked_order(db, c.user_id, c.order_id)
    change_order_status(order, OrderStatus.CANCELLED)
    order.cancelled_at = _now()
    products = repo.lock_products(db, [i.product_id for i in order.items])
    for i in order.items:
        if i.product_id in products:  # product may have been deleted meanwhile
            products[i.product_id].quantity += i.quantity  # return the reserved stock
    return {"order_id": order.id}


HANDLERS = {
    AddToCart: handle_add_to_cart,
    SetCartQuantity: handle_set_cart_quantity,
    RemoveFromCart: handle_remove_from_cart,
    Checkout: handle_checkout,
    CompleteOrder: handle_complete_order,
    CancelOrder: handle_cancel_order,
}


# ---- Command bus: idempotency + one transaction per command ----

def execute(db: Session, command, idempotency_key: str | None = None) -> tuple[dict, bool]:
    """Runs the command's handler. Returns (result, replayed).

    With an Idempotency-Key the first result is stored in processed_commands (same transaction as the
    change); repeating the key returns that result without running the handler again.
    """
    name = type(command).__name__
    target = ",".join(f"{k}={v}" for k, v in asdict(command).items() if k != "user_id")[:50]
    if idempotency_key:
        done = repo.get_processed_command(db, command.user_id, idempotency_key)
        if done is not None:
            if (done.command, done.target) != (name, target):
                raise ValidationError("Ten Idempotency-Key został użyty dla innej operacji.")
            return done.result, True
    result = HANDLERS[type(command)](db, command)
    if idempotency_key:
        repo.add(db, ProcessedCommandORM(user_id=command.user_id, idempotency_key=idempotency_key,
                                         command=name, target=target, result=result))
    db.commit()
    return result, False
