from pydantic import BaseModel, ConfigDict


class Category(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class Product(BaseModel):
    id: int
    name: str
    price: float
    category: Category

    model_config = ConfigDict(from_attributes=True)
