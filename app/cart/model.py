from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.REST.data.database import Base
from app.REST.model.product_orm import ProductORM


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# State machine: only PENDING can move; COMPLETED / CANCELLED are terminal
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class CartItemORM(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    product: Mapped[ProductORM] = relationship()


class OrderORM(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=OrderStatus.PENDING.value)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["OrderItemORM"]] = relationship(order_by="OrderItemORM.id")


class OrderItemORM(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class OrderCounterORM(Base):
    __tablename__ = "order_counters"

    day: Mapped[datetime] = mapped_column(Date, primary_key=True)
    last: Mapped[int] = mapped_column(Integer, nullable=False)


class ProcessedCommandORM(Base):
    __tablename__ = "processed_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    command: Mapped[str] = mapped_column(String, nullable=False)
    target: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---- API schemas (read models) ----

class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(description="> 0, nie więcej niż stan magazynowy")


class CartQuantityIn(BaseModel):
    quantity: int


class CartLine(BaseModel):
    product_id: int
    name: str
    unit_price: float
    quantity: int
    line_total: float
    available: int = Field(description="Aktualny stan magazynowy (maks. ilość w koszyku)")


class Cart(BaseModel):
    items: list[CartLine]
    total: float


class OrderLine(BaseModel):
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class OrderSummary(BaseModel):
    id: int
    number: str
    status: OrderStatus
    total: float
    created_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class Order(OrderSummary):
    items: list[OrderLine]
