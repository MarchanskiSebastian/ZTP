import re
from decimal import Decimal

from sqlalchemy.orm import Session

from app.REST.data.product_repository import (
    get_category_by_id,
    get_forbidden_phrases,
    get_product_by_name,
)
from app.REST.model.product_orm import CategoryORM


# Domain exceptions: no HTTP here, the Web layer maps them to status codes
class ValidationError(Exception):  # 422 - value breaks a business rule
    pass


class ConflictError(Exception):  # 409 - collides with current DB state
    pass


class ResourceNotFoundError(Exception):  # 400 - reference to a missing related resource
    pass


def validate_name_format(name: str) -> None:
    if not (3 <= len(name) <= 20):
        raise ValidationError("Nazwa produktu musi mieć od 3 do 20 znaków.")
    if not re.fullmatch(r"[A-Za-z0-9]+", name):
        raise ValidationError("Nazwa produktu może zawierać tylko litery i cyfry.")


def validate_name_not_forbidden(db: Session, name: str) -> None:
    lowered = name.lower()
    if any(phrase.lower() in lowered for phrase in get_forbidden_phrases(db)):
        raise ValidationError("Nazwa zawiera zakazaną frazę.")


def validate_name_unique(db: Session, name: str, product_id: int | None = None) -> None:
    existing = get_product_by_name(db, name)
    if existing is not None and existing.id != product_id:
        raise ConflictError("Produkt o takiej nazwie już istnieje.")


def validate_category_exists(db: Session, category_id: int) -> CategoryORM:
    category = get_category_by_id(db, category_id)
    if category is None:
        raise ResourceNotFoundError("Wskazana kategoria nie istnieje.")
    return category


def validate_price_in_category_range(category: CategoryORM, price: float) -> None:
    value = Decimal(str(price))
    if not (category.min_price <= value <= category.max_price):
        raise ValidationError(
            f"Cena dla kategorii {category.name} musi mieścić się w przedziale "
            f"{category.min_price}-{category.max_price}."
        )


def validate_quantity_non_negative(quantity: int) -> None:
    if quantity < 0:
        raise ValidationError("Ilość sztuk nie może być ujemna.")
