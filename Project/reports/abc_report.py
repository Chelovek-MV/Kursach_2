"""
Отчет "ABC-анализ ассортимента"
ТР-4: классификация ассортимента по методу ABC
  A — 20% товаров, дающих 80% выручки
  B — 30% товаров, дающих 15% выручки
  C — 50% товаров, дающих 5% выручки
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDateEdit, QDoubleSpinBox
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor, QBrush
from sqlalchemy import func

import sys
sys.path.append('..')
from models import Product, Brand, Category, Order, OrderItem
from .base_report import BaseReportWidget


# Пороги по умолчанию (% от суммарной выручки)
DEFAULT_A_THRESHOLD = 80.0
DEFAULT_B_THRESHOLD = 95.0  # A+B


class AbcReportWidget(BaseReportWidget):
    """Отчет ABC-анализ ассортимента"""

    def __init__(self, session, parent=None):
        self.report_title = "ABC-анализ ассортимента"
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

        # Параметры ABC
        row2 = QHBoxLayout()

        row2.addWidget(self._label("Порог A (%):"))
        self.threshold_a = QDoubleSpinBox()
        self.threshold_a.setRange(1, 99)
        self.threshold_a.setValue(DEFAULT_A_THRESHOLD)
        self.threshold_a.setSuffix("%")
        self.threshold_a.setToolTip("Накопленный % выручки для группы A")
        row2.addWidget(self.threshold_a)

        row2.addSpacing(20)

        row2.addWidget(self._label("Порог A+B (%):"))
        self.threshold_ab = QDoubleSpinBox()
        self.threshold_ab.setRange(1, 100)
        self.threshold_ab.setValue(DEFAULT_B_THRESHOLD)
        self.threshold_ab.setSuffix("%")
        self.threshold_ab.setToolTip("Накопленный % выручки для групп A+B (всё остальное — C)")
        row2.addWidget(self.threshold_ab)

        row2.addSpacing(20)

        # Анализировать по
        self.filter_metric = self.create_combo_filter([
            ("revenue", "По выручке"),
            ("profit",  "По прибыли"),
            ("qty",     "По количеству"),
        ], include_all=False)
        row2.addWidget(self._label("Метрика:"))
        row2.addWidget(self.filter_metric)

        row2.addSpacing(20)

        # Категория
        categories = [(c.id, c.name) for c in self.session.query(Category).all()]
        self.filter_category = self.create_combo_filter(categories)
        row2.addWidget(self._label("Категория:"))
        row2.addWidget(self.filter_category)

        row2.addStretch()
        self.filter_layout.addLayout(row2)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setMinimumWidth(100)
        return lbl

    def generate_report(self):
        try:
            date_from = self.filter_date_from.date().toPyDate()
            date_to = self.filter_date_to.date().toPyDate()
            threshold_a = self.threshold_a.value()
            threshold_ab = self.threshold_ab.value()
            metric = self.filter_metric.currentData() or "revenue"

            query = self.session.query(
                Product.articul,
                Product.name.label("product_name"),
                Brand.name.label("brand_name"),
                Category.name.label("category_name"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("sold_qty"),
                func.coalesce(
                    func.sum(OrderItem.quantity * OrderItem.sell_price), 0
                ).label("revenue"),
                func.coalesce(
                    func.sum(
                        OrderItem.quantity * (OrderItem.sell_price - OrderItem.buy_price)
                    ), 0
                ).label("profit"),
            ).outerjoin(
                OrderItem, OrderItem.product_id == Product.id
            ).outerjoin(
                Order,
                (Order.id == OrderItem.order_id)
                & (Order.created_at >= date_from)
                & (Order.created_at <= date_to)
                & (Order.status != "cancelled"),
            ).outerjoin(
                Brand, Brand.id == Product.brand_id
            ).outerjoin(
                Category, Category.id == Product.category_id
            ).group_by(
                Product.id, Product.articul, Product.name,
                Brand.name, Category.name
            )

            category_id = self.filter_category.currentData()
            if category_id:
                query = query.filter(Product.category_id == category_id)

            results = query.all()

            # Сортируем по выбранной метрике убыванию
            metric_fn = {
                "revenue": lambda r: float(r.revenue or 0),
                "profit":  lambda r: float(r.profit or 0),
                "qty":     lambda r: int(r.sold_qty or 0),
            }[metric]

            sorted_results = sorted(results, key=metric_fn, reverse=True)

            # Считаем суммы
            total_metric = sum(metric_fn(r) for r in sorted_results)

            headers = [
                "#", "Артикул", "Наименование", "Бренд", "Категория",
                "Продано шт.", "Выручка", "Прибыль",
                "Доля %", "Накопл. %", "Группа"
            ]

            data = []
            cumulative = 0.0
            a_count = b_count = c_count = 0

            for rank, row in enumerate(sorted_results, 1):
                metric_val = metric_fn(row)
                share = (metric_val / total_metric * 100) if total_metric > 0 else 0.0
                cumulative += share

                if cumulative <= threshold_a or (rank == 1 and cumulative > threshold_a):
                    group = "A"
                    a_count += 1
                elif cumulative <= threshold_ab:
                    group = "B"
                    b_count += 1
                else:
                    group = "C"
                    c_count += 1

                data.append([
                    rank,
                    row.articul or "",
                    row.product_name or "",
                    row.brand_name or "",
                    row.category_name or "",
                    int(row.sold_qty or 0),
                    f"{float(row.revenue or 0):,.2f}".replace(",", " "),
                    f"{float(row.profit or 0):,.2f}".replace(",", " "),
                    f"{share:.2f}%",
                    f"{min(cumulative, 100.0):.2f}%",
                    group,
                ])

            self.display_data(headers, data)
            self._colorize_abc(data)

            # Итоги
            total_revenue = sum(float(r.revenue or 0) for r in results)
            total_profit = sum(float(r.profit or 0) for r in results)
            total_qty = sum(int(r.sold_qty or 0) for r in results)

            self.clear_totals()
            self.add_total_label(
                f"Группа A ({a_count} товаров)",
                f"{a_count / len(data) * 100:.0f}% ассортимента" if data else "0%",
                "#28a745"
            )
            self.add_total_label(
                f"Группа B ({b_count} товаров)",
                f"{b_count / len(data) * 100:.0f}% ассортимента" if data else "0%",
                "#e67e22"
            )
            self.add_total_label(
                f"Группа C ({c_count} товаров)",
                f"{c_count / len(data) * 100:.0f}% ассортимента" if data else "0%",
                "#888888"
            )
            self.add_total_label("Общая выручка", f"{total_revenue:,.2f} руб.".replace(",", " "))
            self.totals_layout.addStretch()

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчета: {e}")

    def _colorize_abc(self, data: list):
        """Раскрасить строки по группе A/B/C"""
        colors = {
            "A": "#d4edda",  # зелёный
            "B": "#fff3cd",  # жёлтый
            "C": "#f8f9fa",  # серый
        }
        for row_idx, row_data in enumerate(data):
            group = row_data[10]
            color = colors.get(group, "#ffffff")
            for col in range(self.table.columnCount()):
                item = self.table.item(row_idx, col)
                if item:
                    item.setBackground(QBrush(QColor(color)))
