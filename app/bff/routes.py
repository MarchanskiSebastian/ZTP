"""Backend for Frontend: one endpoint shaped exactly for the dashboard view, so the SPA makes a single
request instead of combining /auth/me, /orders and /cart itself."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.cart import queries
from app.cart import repository as repo
from app.cart.model import OrderStatus, OrderSummary
from app.identity.model import User, UserORM
from app.identity.routes import current_user
from app.REST.data.database import get_db

router = APIRouter(prefix="/bff", tags=["bff"])
RECENT = 5


class OrderStats(BaseModel):
    total: int
    pending: int
    completed: int
    cancelled: int
    completed_value: float  # money spent on completed orders


class CartStats(BaseModel):
    items: int
    total: float


class Dashboard(BaseModel):
    user: User
    orders: OrderStats
    cart: CartStats
    recent_orders: list[OrderSummary]
    recent_cancelled: list[OrderSummary]


@router.get("/dashboard", response_model=Dashboard)
def dashboard(user: UserORM = Depends(current_user), db: Session = Depends(get_db)):
    by_status = repo.count_orders_by_status(db, user.id)

    def count(status: OrderStatus) -> int:
        return by_status.get(status.value, (0, 0.0))[0]

    cart = queries.get_cart(db, user.id)
    return Dashboard(
        user=User.model_validate(user),
        orders=OrderStats(
            total=sum(c for c, _ in by_status.values()),
            pending=count(OrderStatus.PENDING),
            completed=count(OrderStatus.COMPLETED),
            cancelled=count(OrderStatus.CANCELLED),
            completed_value=by_status.get(OrderStatus.COMPLETED.value, (0, 0.0))[1],
        ),
        cart=CartStats(items=sum(i.quantity for i in cart.items), total=cart.total),
        recent_orders=[OrderSummary.model_validate(o) for o in repo.get_recent_orders(db, user.id, RECENT)],
        recent_cancelled=[OrderSummary.model_validate(o) for o in
                          repo.get_recent_orders(db, user.id, RECENT, OrderStatus.CANCELLED.value)],
    )
