from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import random
import string
from datetime import datetime, timedelta

from models import *
from db import SessionLocal

session = SessionLocal()


# =========================
# Очистка БД (полный сброс)
# =========================
def clear_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


# =========================
# Генераторы
# =========================

def random_vin():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=17))


def random_phone():
    return f"+7{random.randint(9000000000, 9999999999)}"


def random_articul():
    return f"{random.choice(['BOSCH', 'TOY', 'BMW', 'VAL'])}-{random.randint(10000,99999)}"


# =========================
# Заполнение
# =========================

def seed():

    # --- Бренды ---
    brands = [
        Brand(name="Toyota"),
        Brand(name="BMW"),
        Brand(name="Bosch"),
        Brand(name="Valeo"),
        Brand(name="NGK"),
        Brand(name="Denso")
    ]
    session.add_all(brands)
    session.commit()

    # --- Категории ---
    categories = [
        Category(name="Фильтры"),
        Category(name="Тормозная система"),
        Category(name="Двигатель"),
        Category(name="Подвеска"),
        Category(name="Электрика")
    ]
    session.add_all(categories)
    session.commit()

    # --- Товары ---
    product_names = [
        "Масляный фильтр", "Тормозные колодки", "Свеча зажигания",
        "Воздушный фильтр", "Амортизатор", "Генератор",
        "Стартер", "Радиатор", "Топливный насос"
    ]

    products = []
    for _ in range(100):
        brand = random.choice(brands)
        category = random.choice(categories)
        name = random.choice(product_names)

        articul = random_articul()

        product = Product(
            brand_id=brand.id,
            articul=articul,
            clean_articul=articul.replace("-", ""),
            name=f"{name} {brand.name}",
            category_id=category.id,
            min_balance=random.randint(1, 10)
        )
        products.append(product)

    session.add_all(products)
    session.commit()

    # --- Кросс-номера ---
    for _ in range(40):
        p1, p2 = random.sample(products, 2)
        session.add(CrossReference(
            product_id_1=p1.id,
            product_id_2=p2.id,
            relation_type=random.choice(["equivalent", "compatible"]),
            source="catalog",
            is_verified=random.choice([True, False])
        ))
    session.commit()

    # --- Клиенты ---
    names = [
        "Иван Иванов", "Петр Петров", "Сергей Смирнов",
        "Алексей Кузнецов", "Дмитрий Соколов",
        "Николай Попов", "Андрей Васильев"
    ]

    customers = []
    for _ in range(20):
        c = Customer(
            full_name=random.choice(names),
            phone=random_phone(),
            email=f"user{random.randint(1,100)}@mail.ru",
            discount_level=random.choice([0, 5, 10])
        )
        customers.append(c)

    session.add_all(customers)
    session.commit()

    # --- Машины ---
    car_models = [
        ("Toyota", "Camry"),
        ("Toyota", "Corolla"),
        ("BMW", "X5"),
        ("BMW", "3 Series")
    ]

    vehicles = []
    for c in customers:
        brand, model = random.choice(car_models)

        v = Vehicle(
            customer_id=c.id,
            vin=random_vin(),
            license_plate=f"{random.choice(string.ascii_uppercase)}{random.randint(100,999)}{random.choice(string.ascii_uppercase)}",
            brand=brand,
            model=model,
            year=random.randint(2005, 2022),
            engine=random.choice(["1.6", "2.0", "2.5", "3.0"])
        )
        vehicles.append(v)

    session.add_all(vehicles)
    session.commit()

    # --- Склады ---
    warehouses = [
        Warehouse(name="Основной склад", address="Москва"),
        Warehouse(name="Склад СПб", address="Санкт-Петербург"),
        Warehouse(name="Склад Екатеринбург", address="Екатеринбург")
    ]
    session.add_all(warehouses)
    session.commit()

    # --- Остатки ---
    for p in products:
        for w in warehouses:
            session.add(Stock(
                product_id=p.id,
                warehouse_id=w.id,
                quantity=random.randint(0, 100),
                cell_address=f"{random.choice(['A','B','C'])}-{random.randint(1,20)}"
            ))
    session.commit()

    # --- Поставщики ---
    suppliers = [
        Supplier(name="AutoTrade", delivery_days=3),
        Supplier(name="Exist API", delivery_days=2),
        Supplier(name="Emex", delivery_days=4)
    ]
    session.add_all(suppliers)
    session.commit()

    # --- Логи цен ---
    for p in products[:50]:
        for s in suppliers:
            session.add(PricingLog(
                articul=p.articul,
                supplier_id=s.id,
                price=random.randint(500, 5000),
                delivery_time=s.delivery_days
            ))
    session.commit()

    # --- Заказы ---
    for c in customers:
        order = Order(
            customer_id=c.id,
            vehicle_id=random.choice(vehicles).id,
            status=random.choice(["new", "completed"]),
            payment_method=random.choice(["card", "cash"]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        session.add(order)
        session.commit()

        total = 0

        for _ in range(random.randint(2, 5)):
            p = random.choice(products)
            qty = random.randint(1, 3)
            price = random.randint(1000, 7000)

            total += price * qty

            session.add(OrderItem(
                order_id=order.id,
                product_id=p.id,
                quantity=qty,
                buy_price=price * 0.7,
                sell_price=price
            ))

        order.total_price = total

    session.commit()

    print("БД заполнена")


if __name__ == "__main__":
    clear_db()
    seed()