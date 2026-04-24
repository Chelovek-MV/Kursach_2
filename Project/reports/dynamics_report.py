"""
Отчет "Динамика продаж"
ТР-4: анализ динамики продаж по периодам (день / неделя / месяц / квартал / год)
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDateEdit, QComboBox
from PyQt6.QtCore import QDate
from sqlalchemy import func, extract

import sys
sys.path.append('..')
from models import Order, OrderItem, Product, Brand, Category, Customer
from .base_report import BaseReportWidget


class DynamicsReportWidget(BaseReportWidget):
    """Отчет по динамике продаж"""

    def __init__(self, session, parent=None):
        self.report_title = "Динамика продаж"
        super().__init__(session, parent)

    def _setup_filters(self):

        # Период
        row1 = QHBoxLayout()

        row1.addWidget(self._label("Период с:"))
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_from.setDate(QDate.currentDate().addMonths(-6))
        row1.addWidget(self.filter_date_from)

        row1.addWidget(self._label("по:"))
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_to.setDate(QDate.currentDate())
        row1.addWidget(self.filter_date_to)

        row1.addStretch()
        self.filter_layout.addLayout(row1)

        # Группировка по периоду
        row2 = QHBoxLayout()

        row2.addWidget(self._label("Группировка:"))
        self.filter_period = self.create_combo_filter([
            ("month",   "По месяцам"),
            ("week",    "По неделям"),
            ("quarter", "По кварталам"),
            ("year",    "По годам"),
            ("day",     "По дням"),
        ], include_all=False)
        row2.addWidget(self.filter_period)

        row2.addSpacing(20)

        # Категория
        categories = [(c.id, c.name) for c in self.session.query(Category).all()]
        self.filter_category = self.create_combo_filter(categories)
        row2.addWidget(self._label("Категория:"))
        row2.addWidget(self.filter_category)

        row2.addSpacing(20)

        # Бренд
        brands = [(b.id, b.name) for b in self.session.query(Brand).all()]
        self.filter_brand = self.create_combo_filter(brands)
        row2.addWidget(self._label("Бренд:"))
        row2.addWidget(self.filter_brand)

        row2.addStretch()
        self.filter_layout.addLayout(row2)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setMinimumWidth(80)
        return lbl

    def generate_report(self):
        try:
            period = self.filter_period.currentData() or "month"
            date_from = self.filter_date_from.date().toPyDate()
            date_to = self.filter_date_to.date().toPyDate()

            # Группировка по периоду
            if period == "day":
                period_expr = func.date_trunc("day", Order.created_at)
                period_label = "День"
                fmt = lambda dt: dt.strftime("%d.%m.%Y") if dt else ""
            elif period == "week":
                period_expr = func.date_trunc("week", Order.created_at)
                period_label = "Неделя"
                fmt = lambda dt: f"W{dt.strftime('%V %Y')}" if dt else ""
            elif period == "quarter":
                period_expr = func.date_trunc("quarter", Order.created_at)
                period_label = "Квартал"
                fmt = lambda dt: f"Q{((dt.month - 1) // 3) + 1} {dt.year}" if dt else ""
            elif period == "year":
                period_expr = func.date_trunc("year", Order.created_at)
                period_label = "Год"
                fmt = lambda dt: str(dt.year) if dt else ""
            else:  # month
                period_expr = func.date_trunc("month", Order.created_at)
                period_label = "Месяц"
                fmt = lambda dt: dt.strftime("%m.%Y") if dt else ""

            query = self.session.query(
                period_expr.label("period"),
                func.count(func.distinct(Order.id)).label("orders_count"),
                func.sum(OrderItem.quantity).label("total_qty"),
                func.sum(OrderItem.quantity * OrderItem.sell_price).label("revenue"),
                func.sum(OrderItem.quantity * OrderItem.buy_price).label("cost"),
                func.sum(
                    OrderItem.quantity * (OrderItem.sell_price - OrderItem.buy_price)
                ).label("profit"),
            ).join(
                OrderItem, OrderItem.order_id == Order.id
            ).join(
                Product, Product.id == OrderItem.product_id
            ).filter(
                Order.created_at >= date_from,
                Order.created_at <= date_to,
                Order.status != "cancelled",
            )

            category_id = self.filter_category.currentData()
            if category_id:
                query = query.filter(Product.category_id == category_id)

            brand_id = self.filter_brand.currentData()
            if brand_id:
                query = query.filter(Product.brand_id == brand_id)

            query = query.group_by("period").order_by("period")
            results = query.all()

            headers = [
                period_label, "Заказов", "Продано шт.",
                "Выручка, руб.", "Себест., руб.", "Прибыль, руб.", "Маржа %",
                "Динамика выручки"
            ]

            data = []
            prev_revenue = None
            total_orders = 0
            total_qty = 0
            total_revenue = 0.0
            total_cost = 0.0
            total_profit = 0.0

            for row in results:
                revenue = float(row.revenue or 0)
                cost = float(row.cost or 0)
                profit = float(row.profit or 0)
                qty = int(row.total_qty or 0)
                orders = int(row.orders_count or 0)
                margin = (profit / revenue * 100) if revenue > 0 else 0.0

                total_orders += orders
                total_qty += qty
                total_revenue += revenue
                total_cost += cost
                total_profit += profit

                # Динамика к предыдущему периоду
                if prev_revenue is None:
                    dynamics = "—"
                elif prev_revenue == 0:
                    dynamics = "+100%" if revenue > 0 else "0%"
                else:
                    delta = (revenue - prev_revenue) / prev_revenue * 100
                    dynamics = f"{'+' if delta >= 0 else ''}{delta:.1f}%"

                prev_revenue = revenue

                period_dt = row.period
                data.append([
                    fmt(period_dt),
                    orders,
                    qty,
                    f"{revenue:,.2f}".replace(",", " "),
                    f"{cost:,.2f}".replace(",", " "),
                    f"{profit:,.2f}".replace(",", " "),
                    f"{margin:.1f}%",
                    dynamics,
                ])

            total_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0

            totals = {
                1: total_orders,
                2: total_qty,
                3: f"{total_revenue:,.2f}".replace(",", " "),
                4: f"{total_cost:,.2f}".replace(",", " "),
                5: f"{total_profit:,.2f}".replace(",", " "),
                6: f"{total_margin:.1f}%",
            }

            self.display_data(headers, data, totals)

            self.clear_totals()
            self.add_total_label("Периодов", len(data))
            self.add_total_label("Всего заказов", total_orders)
            self.add_total_label(
                "Выручка", f"{total_revenue:,.2f} руб.".replace(",", " ")
            )
            self.add_total_label(
                "Прибыль",
                f"{total_profit:,.2f} руб.".replace(",", " "),
                "#28a745" if total_profit >= 0 else "#cc0000",
            )
            self.add_total_label("Средняя маржа", f"{total_margin:.1f}%")
            self.totals_layout.addStretch()

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчета: {e}")
