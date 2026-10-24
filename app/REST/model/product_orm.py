from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.REST.data.database import Base


class CategoryORM(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    min_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)


class ForbiddenNameORM(Base):
    __tablename__ = "forbidden_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phrase: Mapped[str] = mapped_column(String, nullable=False)


class ProductORM(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    category: Mapped[CategoryORM] = relationship()
