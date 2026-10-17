from sqlalchemy.orm import Session

from data.product_repository import get_all_products, get_product_by_id
from model.product_orm import ProductORM


def list_products(db: Session) -> list[ProductORM]:
    return get_all_products(db)


def get_product(db: Session, product_id: int) -> ProductORM | None:
    return get_product_by_id(db, product_id)
