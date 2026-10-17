from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from model.product_orm import ProductORM


def get_all_products(db: Session) -> list[ProductORM]:
    # joinedload fetches the category in the same query (no N+1)
    query = select(ProductORM).options(joinedload(ProductORM.category)).order_by(ProductORM.id)
    return list(db.execute(query).scalars().all())


def get_product_by_id(db: Session, product_id: int) -> ProductORM | None:
    query = (
        select(ProductORM)
        .options(joinedload(ProductORM.category))
        .where(ProductORM.id == product_id)
    )
    return db.execute(query).scalar_one_or_none()
