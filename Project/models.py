from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey,
    Float, DateTime, Text, Index, UniqueConstraint, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# =========================
# 1. Каталог
# =========================

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)

    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    articul = Column(String, nullable=False)
    clean_articul = Column(String, nullable=False)

    name = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"))

    min_balance = Column(Integer, default=0)

    brand = relationship("Brand")
    category = relationship("Category")

    # Связи для кросс-номеров
    cross_refs_as_1 = relationship(
        "CrossReference",
        foreign_keys="CrossReference.product_id_1",
        back_populates="product_1"
    )
    cross_refs_as_2 = relationship(
        "CrossReference",
        foreign_keys="CrossReference.product_id_2",
        back_populates="product_2"
    )

    __table_args__ = (
        Index("ix_products_articul", "articul"),
        Index("ix_products_clean_articul", "clean_articul"),
        UniqueConstraint("brand_id", "articul", name="uq_brand_articul"),
    )


class CrossReference(Base):
    """Кросс-номера: взаимозаменяемые / совместимые запчасти"""
    __tablename__ = "cross_references"

    id = Column(Integer, primary_key=True)

    product_id_1 = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_id_2 = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Тип связи: "equivalent" — аналог, "compatible" — совместим, "supersedes" — заменяет
    relation_type = Column(String, default="equivalent")
    source = Column(String)  # откуда получена информация (каталог, поставщик, вручную)
    is_verified = Column(Boolean, default=False)  # проверена ли замена

    product_1 = relationship("Product", foreign_keys=[product_id_1], back_populates="cross_refs_as_1")
    product_2 = relationship("Product", foreign_keys=[product_id_2], back_populates="cross_refs_as_2")

    __table_args__ = (
        UniqueConstraint("product_id_1", "product_id_2", name="uq_cross_pair"),
    )


# =========================
# 2. CRM
# =========================

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)

    full_name = Column(String)
    phone = Column(String, index=True)
    email = Column(String)
    telegram_id = Column(String)
    discount_level = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    note = Column(Text)  # произвольная заметка менеджера

    vehicles = relationship("Vehicle", back_populates="customer")
    orders = relationship("Order", back_populates="customer")
    warranties = relationship("Warranty", back_populates="customer")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    vin = Column(String, index=True)
    license_plate = Column(String, index=True)

    brand = Column(String)
    model = Column(String)
    year = Column(Integer)
    trim = Column(String)   # комплектация (расшифрованная из VIN или введённая вручную)
    engine = Column(String) # двигатель / объём

    customer = relationship("Customer", back_populates="vehicles")
    warranties = relationship("Warranty", back_populates="vehicle")


class VinDecodeCache(Base):
    """Кеш расшифровок VIN — чтобы не запрашивать API повторно"""
    __tablename__ = "vin_decode_cache"

    id = Column(Integer, primary_key=True)

    vin = Column(String, nullable=False, unique=True, index=True)

    make = Column(String)    # марка
    model = Column(String)   # модель
    year = Column(Integer)   # год
    trim = Column(String)    # комплектация
    engine = Column(String)  # двигатель
    country = Column(String) # страна производства
    plant = Column(String)   # завод

    raw_data = Column(Text)  # полный JSON-ответ для будущего анализа
    decoded_at = Column(DateTime, default=datetime.utcnow)


class Warranty(Base):
    """Гарантийные обязательства по запчастям"""
    __tablename__ = "warranties"

    id = Column(Integer, primary_key=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))

    # Сроки
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Статус: "active", "expired", "claimed", "closed"
    status = Column(String, default="active", index=True)

    # Условия
    warranty_months = Column(Integer, default=12)
    note = Column(Text)

    customer = relationship("Customer", back_populates="warranties")
    vehicle = relationship("Vehicle", back_populates="warranties")
    product = relationship("Product")
    order = relationship("Order")


class VinRequest(Base):
    __tablename__ = "vin_requests"

    id = Column(Integer, primary_key=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    status = Column(String, index=True)

    manager_id = Column(Integer)
    comment = Column(Text)

    vehicle = relationship("Vehicle")


# =========================
# 3. Склад
# =========================

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)

    quantity = Column(Integer, default=0)
    cell_address = Column(String)

    product = relationship("Product")
    warehouse = relationship("Warehouse")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_stock"),
    )


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    api_key = Column(String)
    api_endpoint = Column(String)
    delivery_days = Column(Integer)
    contact_phone = Column(String)
    contact_email = Column(String)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)

    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    # Статусы: "pending" (заявка), "sent", "received", "cancelled"
    status = Column(String, index=True, default="pending")

    total_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    note = Column(Text)

    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")


class PurchaseOrderItem(Base):
    """Позиции заявки поставщику"""
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True)

    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)
    unit_price = Column(Float)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")


# =========================
# 4. Продажи
# =========================

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)

    customer_id = Column(Integer, ForeignKey("customers.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))  # к какому ТС относится заказ
    # Статусы: "new", "processing", "completed", "cancelled"
    status = Column(String, index=True, default="new")

    payment_method = Column(String)
    total_price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    customer = relationship("Customer", back_populates="orders")
    vehicle = relationship("Vehicle")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity = Column(Integer)
    buy_price = Column(Float)
    sell_price = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
    )


class PricingLog(Base):
    __tablename__ = "pricing_log"

    id = Column(Integer, primary_key=True)

    articul = Column(String, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))

    price = Column(Float)
    delivery_time = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# =========================
# Подключение и создание БД
# =========================

DATABASE_URL = "postgresql+psycopg2://postgres:1212@localhost:5432/mydb"

engine = create_engine(DATABASE_URL, echo=True)

def create_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    create_db()
