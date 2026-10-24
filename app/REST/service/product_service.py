from sqlalchemy.orm import Session

from app.REST.data.product_repository import (
    add_product,
    add_product_history,
    commit,
    delete_product,
    get_all_products,
    get_product_by_id,
    get_product_history_by_product_id,
    save_product,
)
from app.REST.model.product_history_orm import ProductHistoryORM
from app.REST.model.product_orm import ProductORM
from app.REST.model.product_schema import ProductCreate
from app.REST.service.product_validators import (
    validate_category_exists,
    validate_name_format,
    validate_name_not_forbidden,
    validate_name_unique,
    validate_price_in_category_range,
    validate_quantity_non_negative,
)


def _validate_product_full_data(db: Session, payload: ProductCreate, product_id: int | None = None):
    # Shared by POST and PUT (DRY)
    validate_name_format(payload.name)
    validate_name_not_forbidden(db, payload.name)
    validate_name_unique(db, payload.name, product_id)
    category = validate_category_exists(db, payload.category_id)
    validate_price_in_category_range(category, payload.price)
    validate_quantity_non_negative(payload.quantity)


def _build_product_snapshot(product: ProductORM) -> dict:
    category = product.category
    return {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "quantity": product.quantity,
        "category": {
            "id": category.id,
            "name": category.name,
            "min_price": float(category.min_price),
            "max_price": float(category.max_price),
        },
    }


def _save_product_history(db: Session, product_id: int, previous_state: dict, current_state: dict, action: str):
    entry = ProductHistoryORM(
        product_id=product_id,
        action=action,
        previous_state=previous_state,
        current_state=current_state,
    )
    return add_product_history(db, entry)


def list_products(db: Session) -> list[ProductORM]:
    return get_all_products(db)


def get_product(db: Session, product_id: int) -> ProductORM | None:
    return get_product_by_id(db, product_id)


def create_product(db: Session, payload: ProductCreate) -> ProductORM:
    _validate_product_full_data(db, payload)
    product = add_product(
        db,
        ProductORM(
            name=payload.name,
            price=payload.price,
            quantity=payload.quantity,
            category_id=payload.category_id,
        ),
    )
    _save_product_history(db, product.id, {}, _build_product_snapshot(product), "CREATE")
    commit(db)  # product and its history entry are saved atomically
    return product


def replace_product(db: Session, product_id: int, payload: ProductCreate) -> ProductORM | None:
    product = get_product_by_id(db, product_id)
    if product is None:
        return None  # existence is checked first, then validation
    previous_state = _build_product_snapshot(product)

    _validate_product_full_data(db, payload, product_id)

    product.name = payload.name
    product.price = payload.price
    product.quantity = payload.quantity
    product.category_id = payload.category_id
    product = save_product(db, product)

    _save_product_history(db, product.id, previous_state, _build_product_snapshot(product), "REPLACE")
    commit(db)
    return product


def remove_product(db: Session, product_id: int) -> bool:
    product = get_product_by_id(db, product_id)
    if product is None:
        return False
    previous_state = _build_product_snapshot(product)

    delete_product(db, product)
    _save_product_history(db, product_id, previous_state, {}, "DELETE")
    commit(db)
    return True


def list_product_history(db: Session, product_id: int):
    history = get_product_history_by_product_id(db, product_id)
    # A deleted product still has history; 404 only when there is neither product nor history
    if not history and get_product_by_id(db, product_id) is None:
        return None
    return history
