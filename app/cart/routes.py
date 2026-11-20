from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.cart import queries
from app.cart.commands import (
    AddToCart,
    CancelOrder,
    Checkout,
    CompleteOrder,
    RemoveFromCart,
    SetCartQuantity,
    execute,
)
from app.cart.model import Cart, CartItemIn, CartQuantityIn, Order, OrderSummary
from app.identity.model import UserORM
from app.identity.routes import current_user
from app.REST.data.database import get_db

cart_router = APIRouter(prefix="/cart", tags=["cart"])
orders_router = APIRouter(prefix="/orders", tags=["orders"])

IdempotencyKey = Header(None, alias="Idempotency-Key", max_length=100,
                        description="Powtórzenie klucza zwraca wynik pierwszego wykonania")


def _run(db: Session, command, key: str | None, response: Response) -> dict:
    result, replayed = execute(db, command, key)
    if replayed:
        response.headers["Idempotent-Replayed"] = "true"
    return result


@cart_router.get("", response_model=Cart)
def get_cart(user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    return queries.get_cart(db, user.id)


@cart_router.post("/items", response_model=Cart)
def add_item(body: CartItemIn, user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    execute(db, AddToCart(user.id, body.product_id, body.quantity))
    return queries.get_cart(db, user.id)


@cart_router.put("/items/{product_id}", response_model=Cart)
def set_quantity(product_id: int, body: CartQuantityIn, user: UserORM = Depends(current_user),
                 db: Session = Depends(get_db)):
    execute(db, SetCartQuantity(user.id, product_id, body.quantity))
    return queries.get_cart(db, user.id)


@cart_router.delete("/items/{product_id}", response_model=Cart)
def remove_item(product_id: int, user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    execute(db, RemoveFromCart(user.id, product_id))
    return queries.get_cart(db, user.id)


@cart_router.post("/checkout", response_model=Order, status_code=201)
def checkout(response: Response, idempotency_key: str | None = IdempotencyKey,
             user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    result = _run(db, Checkout(user.id), idempotency_key, response)
    return queries.get_order(db, user.id, result["order_id"])


@orders_router.get("", response_model=list[OrderSummary])
def list_orders(user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    return queries.list_orders(db, user.id)


@orders_router.get("/{order_id}", response_model=Order)
def get_order(order_id: int, user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    return queries.get_order(db, user.id, order_id)


@orders_router.post("/{order_id}/complete", response_model=Order)
def complete(order_id: int, response: Response, idempotency_key: str | None = IdempotencyKey,
             user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    _run(db, CompleteOrder(user.id, order_id), idempotency_key, response)
    return queries.get_order(db, user.id, order_id)


@orders_router.post("/{order_id}/cancel", response_model=Order)
def cancel(order_id: int, response: Response, idempotency_key: str | None = IdempotencyKey,
           user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    _run(db, CancelOrder(user.id, order_id), idempotency_key, response)
    return queries.get_order(db, user.id, order_id)
