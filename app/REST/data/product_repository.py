from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.REST.model.product_history_orm import ProductHistoryORM
from app.REST.model.product_orm import CategoryORM, ForbiddenNameORM, ProductORM


def get_all_products(db: Session) -> list[ProductORM]:
    query = select(ProductORM).options(joinedload(ProductORM.category)).order_by(ProductORM.id)
    return list(db.execute(query).scalars().all())


def get_product_by_id(db: Session, product_id: int) -> ProductORM | None:
    query = (
        select(ProductORM)
        .options(joinedload(ProductORM.category))
        .where(ProductORM.id == product_id)
    )
    return db.execute(query).scalar_one_or_none()


def get_product_by_name(db: Session, name: str) -> ProductORM | None:
    query = select(ProductORM).where(func.lower(ProductORM.name) == name.lower())
    return db.execute(query).scalar_one_or_none()


def get_category_by_id(db: Session, category_id: int) -> CategoryORM | None:
    return db.get(CategoryORM, category_id)


def get_forbidden_phrases(db: Session) -> list[str]:
    return list(db.execute(select(ForbiddenNameORM.phrase)).scalars().all())


# Write functions flush (to get ids / catch DB errors) but do NOT commit:
# the service decides when the whole operation (change + history) is committed.
def add_product(db: Session, product: ProductORM) -> ProductORM:
    db.add(product)
    db.flush()
    db.refresh(product)
    return product


def save_product(db: Session, product: ProductORM) -> ProductORM:
    db.flush()
    db.refresh(product)
    return product


def delete_product(db: Session, product: ProductORM) -> None:
    db.delete(product)
    db.flush()


def commit(db: Session) -> None:
    db.commit()


def add_product_history(db: Session, entry: ProductHistoryORM) -> ProductHistoryORM:
    db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def get_product_history_by_product_id(db: Session, product_id: int) -> list[ProductHistoryORM]:
    query = (
        select(ProductHistoryORM)
        .where(ProductHistoryORM.product_id == product_id)
        .order_by(desc(ProductHistoryORM.changed_at), desc(ProductHistoryORM.id))
    )
    return list(db.execute(query).scalars().all())
