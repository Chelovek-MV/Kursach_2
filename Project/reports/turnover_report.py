"""
Отчет "Оборачиваемость запасов"
ТР-4: оценка оборачиваемости запасов — сколько дней товар лежит на складе
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDateEdit, QDoubleSpinBox
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor, QBrush
from sqlalchemy import func
from datetime import date

import sys
sys.path.append('..')
from models import Product, Brand, Category, Stock, Order, OrderItem
from .base_report import BaseReportWidget


class TurnoverReportWidget(BaseReportWidget):
    """Отчет по оборачиваемости запасов"""

    def __init__(self, session, parent=None):
        self.report_title = "Оборачиваемость запасов"
        super().__init__(session, parent)

    def _setup_filters(self):

        # Период для расчёта продаж
        row1 = QHBoxLayout()

        row1.addWidget(self._label("Период с:"))
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_from.setDate(QDate.currentDate().addMonths(-3))
        row1.addWidget(self.filter_date_from)

        row1.addWidget(self._label("по:"))
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_to.setDate(QDate.currentDate())
        row1.addWidget(self.filter_date_to)

        row1.addStretch()
        self.filter_layout.addLayout(row1)

        # Категория / Бренд
        row2 = QHBoxLayout()

        categories = [(c.id, c.name) for c in self.session.query(Category).all()]
        self.filter_category = self.create_combo_filter(categories)
        row2.addWidget(self._label("Категория:"))
        row2.addWidget(self.filter_category)

        row2.addSpacing(20)

        brands = [(b.id, b.name) for b in self.session.query(Brand).all()]
        self.filter_brand = self.create_combo_filter(brands)
        row2.addWidget(self._label("Бренд:"))
        row2.addWidget(self.filter_brand)

        row2.addStretch()
        self.filter_layout.addLayout(row2)

        # Порог "медленный оборот"
        row3 = QHBoxLayout()
        row3.addWidget(self._label("Порог ДОЗ (дней):"))
        self.filter_slow_threshold = QDoubleSpinBox()
        self.filter_slow_threshold.setRange(1, 3650)
        self.filter_slow_threshold.setValue(90)
        self.filter_slow_threshold.setDecimals(0)
        self.filter_slow_threshold.setSuffix(" дн.")
        self.filter_slow_threshold.setToolTip(
            "Товары с ДОЗ выше этого порога считаются 'медленными'"
        )
        row3.addWidget(self.filter_slow_threshold)
        row3.addStretch()
        self.filter_layout.addLayout(row3)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setMinimumWidth(120)
        return lbl

    def generate_report(self):
        try:
            date_from = self.filter_date_from.date().toPyDate()
            date_to = self.filter_date_to.date().toPyDate()
            period_days = max((date_to - date_from).days, 1)
            slow_threshold = int(self.filter_slow_threshold.value())

            # Продажи за период
            sales_q = self.session.query(
                Product.id.label("product_id"),
                func.sum(OrderItem.quantity).label("sold_qty"),
                func.sum(OrderItem.quantity * OrderItem.sell_price).label("revenue"),
            ).join(
                OrderItem, OrderItem.product_id == Product.id
            ).join(
                Order, Order.id == OrderItem.order_id
            ).filter(
                Order.created_at >= date_from,
                Order.created_at <= date_to,
                Order.status != "cancelled",
            ).group_by(Product.id)

            category_id = self.filter_category.currentData()
            if category_id:
                sales_q = sales_q.filter(Product.category_id == category_id)

            brand_id = self.filter_brand.currentData()
            if brand_id:
                sales_q = sales_q.filter(Product.brand_id == brand_id)

            sales_map = {r.product_id: r for r in sales_q.all()}

            # Текущие остатки
            stock_q = self.session.query(
                Product.id.label("product_id"),
                Product.articul,
                Product.name.label("product_name"),
                Product.min_balance,
                Brand.name.label("brand_name"),
                Category.name.label("category_name"),
                func.coalesce(func.sum(Stock.quantity), 0).label("current_stock"),
            ).outerjoin(
                Stock, Stock.product_id == Product.id
            ).outerjoin(
                Brand, Brand.id == Product.brand_id
            ).outerjoin(
                Category, Category.id == Product.category_id
            ).group_by(
                Product.id, Product.articul, Product.name,
                Product.min_balance, Brand.name, Category.name
            )

            if category_id:
                stock_q = stock_q.filter(Product.category_id == category_id)
            if brand_id:
                stock_q = stock_q.filter(Product.brand_id == brand_id)

            products = stock_q.all()

            headers = [
                "Артикул", "Наименование", "Бренд", "Категория",
                "Остаток", "Продано (период)", "Ср. продаж/день",
                "ДОЗ (дней)", "Статус"
            ]

            data = []
            slow_count = 0
            zero_count = 0
            total_stock = 0

            for p in products:
                sales = sales_map.get(p.product_id)
                sold_qty = int(sales.sold_qty) if sales else 0
                current = int(p.current_stock)
                total_stock += current

                # Среднедневные продажи
                avg_daily = sold_qty / period_days if sold_qty > 0 else 0

                # ДОЗ — Дни Оборота Запаса
                if avg_daily > 0:
                    doz = current / avg_daily
                    status = "Медленный" if doz > slow_threshold else "Норма"
                    if doz > slow_threshold:
                        slow_count += 1
                elif current > 0:
                    doz = None
                    status = "Нет продаж"
                    zero_count += 1
                else:
                    doz = None
                    status = "Нет остатка"

                data.append([
                    p.articul or "",
                    p.product_name or "",
                    p.brand_name or "",
                    p.category_name or "",
                    current,
                    sold_qty,
                    f"{avg_daily:.2f}",
                    f"{doz:.0f}" if doz is not None else "∞",
                    status,
                ])

            # Сортировка: сначала "Нет продаж" (самый медленный), потом по ДОЗ убыванию
            status_order = {"Медленный": 0, "Нет продаж": 1, "Норма": 2, "Нет остатка": 3}
            data.sort(key=lambda r: (status_order.get(r[8], 9), r[7] if r[7] != "∞" else 999999))

            self.display_data(headers, data)

            # Подсветка
            self._colorize_rows(data)

            self.clear_totals()
            self.add_total_label("Товаров", len(data))
            self.add_total_label("Общий остаток", f"{total_stock:,}".replace(",", " "))
            self.add_total_label("Медленный оборот", slow_count, "#cc0000")
            self.add_total_label(f"Нет продаж (>{slow_threshold} дн.)", zero_count, "#e67e22")
            self.totals_layout.addStretch()

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчета: {e}")

    def _colorize_rows(self, data: list):
        colors = {
            "Медленный": "#fff3cd",
            "Нет продаж": "#fde8e8",
            "Норма": "#d4edda",
            "Нет остатка": "#f8f9fa",
        }
        for row_idx, row_data in enumerate(data):
            status = row_data[8]
            color = colors.get(status, "#ffffff")
            for col in range(self.table.columnCount()):
                item = self.table.item(row_idx, col)
                if item:
                    item.setBackground(QBrush(QColor(color)))
