"""
Отчет "Прибыльность"
Анализ прибыльности товаров: выручка, себестоимость, маржа
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDateEdit, QSpinBox
from PyQt6.QtCore import QDate
from sqlalchemy import func

import sys
sys.path.append('..')
from models import Product, Brand, Category, Order, OrderItem
from .base_report import BaseReportWidget


class ProfitReportWidget(BaseReportWidget):
    """Отчет по прибыльности"""
    
    def __init__(self, session, parent=None):
        self.report_title = "Прибыльность товаров"
        super().__init__(session, parent)
    
    def _setup_filters(self):
        """Настройка фильтров"""
        
        # Первая строка: Период
        row1 = QHBoxLayout()
        
        row1.addWidget(self._create_label("Период с:"))
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_from.setDate(QDate.currentDate().addMonths(-3))
        row1.addWidget(self.filter_date_from)
        
        row1.addWidget(self._create_label("по:"))
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_to.setDate(QDate.currentDate())
        row1.addWidget(self.filter_date_to)
        
        row1.addStretch()
        self.filter_layout.addLayout(row1)
        
        # Вторая строка: Категория, Бренд
        row2 = QHBoxLayout()
        
        # Категория
        categories = [(c.id, c.name) for c in self.session.query(Category).all()]
        self.filter_category = self.create_combo_filter(categories)
        row2.addWidget(self._create_label("Категория:"))
        row2.addWidget(self.filter_category)
        
        row2.addSpacing(20)
        
        # Бренд
        brands = [(b.id, b.name) for b in self.session.query(Brand).all()]
        self.filter_brand = self.create_combo_filter(brands)
        row2.addWidget(self._create_label("Бренд:"))
        row2.addWidget(self.filter_brand)
        
        row2.addStretch()
        self.filter_layout.addLayout(row2)
        
        # Третья строка: Топ N
        row3 = QHBoxLayout()
        
        row3.addWidget(self._create_label("Показать топ:"))
        self.filter_top_n = QSpinBox()
        self.filter_top_n.setRange(0, 1000)
        self.filter_top_n.setValue(0)
        self.filter_top_n.setSpecialValueText("Все")
        self.filter_top_n.setToolTip("0 = показать все товары")
        row3.addWidget(self.filter_top_n)
        
        row3.addSpacing(20)
        
        # Сортировка
        sort_options = [
            ("profit", "По прибыли"),
            ("margin", "По марже %"),
            ("revenue", "По выручке"),
            ("quantity", "По количеству"),
        ]
        self.filter_sort = self.create_combo_filter(sort_options, include_all=False)
        row3.addWidget(self._create_label("Сортировка:"))
        row3.addWidget(self.filter_sort)
        
        row3.addStretch()
        self.filter_layout.addLayout(row3)
    
    def _create_label(self, text):
        """Создать метку"""
        label = QLabel(text)
        label.setMinimumWidth(80)
        return label
    
    def generate_report(self):
        """Формирование отчета"""
        try:
            # Базовый запрос: товары с продажами
            query = self.session.query(
                Product.articul,
                Product.name.label('product_name'),
                Brand.name.label('brand_name'),
                Category.name.label('category_name'),
                func.sum(OrderItem.quantity).label('total_qty'),
                func.sum(OrderItem.quantity * OrderItem.sell_price).label('revenue'),
                func.sum(OrderItem.quantity * OrderItem.buy_price).label('cost'),
                func.sum(OrderItem.quantity * (OrderItem.sell_price - OrderItem.buy_price)).label('profit')
            ).join(
                OrderItem, OrderItem.product_id == Product.id
            ).join(
                Order, Order.id == OrderItem.order_id
            ).outerjoin(
                Brand, Brand.id == Product.brand_id
            ).outerjoin(
                Category, Category.id == Product.category_id
            ).group_by(
                Product.id, Product.articul, Product.name,
                Brand.name, Category.name
            )
            
            # Фильтр по категории
            category_id = self.filter_category.currentData()
            if category_id:
                query = query.filter(Product.category_id == category_id)
            
            # Фильтр по бренду
            brand_id = self.filter_brand.currentData()
            if brand_id:
                query = query.filter(Product.brand_id == brand_id)
            
            # Сортировка
            sort_by = self.filter_sort.currentData()
            if sort_by == "profit":
                query = query.order_by(func.sum(OrderItem.quantity * (OrderItem.sell_price - OrderItem.buy_price)).desc())
            elif sort_by == "margin":
                # Маржа = прибыль / выручка
                query = query.order_by(
                    (func.sum(OrderItem.quantity * (OrderItem.sell_price - OrderItem.buy_price)) / 
                     func.nullif(func.sum(OrderItem.quantity * OrderItem.sell_price), 0)).desc()
                )
            elif sort_by == "revenue":
                query = query.order_by(func.sum(OrderItem.quantity * OrderItem.sell_price).desc())
            elif sort_by == "quantity":
                query = query.order_by(func.sum(OrderItem.quantity).desc())
            
            # Лимит
            top_n = self.filter_top_n.value()
            if top_n > 0:
                query = query.limit(top_n)
            
            results = query.all()
            
            headers = [
                "Артикул", "Наименование", "Бренд", "Категория",
                "Продано шт.", "Выручка", "Себестоимость", "Прибыль", "Маржа %"
            ]
            
            data = []
            total_qty = 0
            total_revenue = 0
            total_cost = 0
            total_profit = 0
            
            for row in results:
                qty = row.total_qty or 0
                revenue = row.revenue or 0
                cost = row.cost or 0
                profit = row.profit or 0
                margin = (profit / revenue * 100) if revenue > 0 else 0
                
                total_qty += qty
                total_revenue += revenue
                total_cost += cost
                total_profit += profit
                
                data.append([
                    row.articul or "",
                    row.product_name or "",
                    row.brand_name or "",
                    row.category_name or "",
                    qty,
                    f"{revenue:.2f}",
                    f"{cost:.2f}",
                    f"{profit:.2f}",
                    f"{margin:.1f}%"
                ])
            
            # Общая маржа
            total_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            totals = {
                4: total_qty,
                5: f"{total_revenue:.2f}",
                6: f"{total_cost:.2f}",
                7: f"{total_profit:.2f}",
                8: f"{total_margin:.1f}%"
            }
            
            self.display_data(headers, data, totals)
            
            # Панель итогов
            self.clear_totals()
            self.add_total_label("Товаров", len(data))
            self.add_total_label("Общая выручка", f"{total_revenue:,.2f} руб.".replace(",", " "))
            self.add_total_label("Общая прибыль", f"{total_profit:,.2f} руб.".replace(",", " "), 
                                "#28a745" if total_profit > 0 else "#cc0000")
            self.add_total_label("Средняя маржа", f"{total_margin:.1f}%")
            self.totals_layout.addStretch()
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчета: {e}")
