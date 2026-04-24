"""
Отчет "Продажи"
Анализ продаж по периодам, клиентам, товарам
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDateEdit
from PyQt6.QtCore import QDate
from sqlalchemy import func, and_

import sys
sys.path.append('..')
from models import Product, Brand, Customer, Order, OrderItem
from .base_report import BaseReportWidget


class SalesReportWidget(BaseReportWidget):
    """Отчет по продажам"""
    
    def __init__(self, session, parent=None):
        self.report_title = "Продажи"
        super().__init__(session, parent)
    
    def _setup_filters(self):
        """Настройка фильтров"""
        
        # Первая строка: Период
        row1 = QHBoxLayout()
        
        row1.addWidget(self._create_label("Период с:"))
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_from.setDate(QDate.currentDate().addMonths(-1))
        row1.addWidget(self.filter_date_from)
        
        row1.addWidget(self._create_label("по:"))
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_to.setDate(QDate.currentDate())
        row1.addWidget(self.filter_date_to)
        
        row1.addStretch()
        self.filter_layout.addLayout(row1)
        
        # Вторая строка: Клиент, Статус
        row2 = QHBoxLayout()
        
        # Клиент
        customers = [(c.id, c.full_name or f"Клиент #{c.id}") 
                     for c in self.session.query(Customer).all()]
        self.filter_customer = self.create_combo_filter(customers)
        row2.addWidget(self._create_label("Клиент:"))
        row2.addWidget(self.filter_customer)
        
        row2.addSpacing(20)
        
        # Статус заказа
        statuses = [
            ("new", "Новый"),
            ("processing", "В обработке"),
            ("completed", "Выполнен"),
            ("cancelled", "Отменен"),
        ]
        self.filter_status = self.create_combo_filter(statuses)
        row2.addWidget(self._create_label("Статус:"))
        row2.addWidget(self.filter_status)
        
        row2.addStretch()
        self.filter_layout.addLayout(row2)
        
        # Третья строка: Группировка
        row3 = QHBoxLayout()
        
        row3.addWidget(self._create_label("Группировка:"))
        self.filter_grouping = self.create_combo_filter([
            ("none", "Без группировки"),
            ("customer", "По клиентам"),
            ("product", "По товарам"),
        ], include_all=False)
        row3.addWidget(self.filter_grouping)
        
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
            grouping = self.filter_grouping.currentData()
            
            if grouping == "customer":
                self._generate_by_customer()
            elif grouping == "product":
                self._generate_by_product()
            else:
                self._generate_detailed()
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчета: {e}")
    
    def _generate_detailed(self):
        """Детальный отчет по продажам"""
        
        # Базовый запрос
        query = self.session.query(
            Order.id.label('order_id'),
            Customer.full_name.label('customer_name'),
            Order.status,
            Product.articul,
            Product.name.label('product_name'),
            OrderItem.quantity,
            OrderItem.sell_price,
            (OrderItem.quantity * OrderItem.sell_price).label('total')
        ).join(
            OrderItem, OrderItem.order_id == Order.id
        ).join(
            Product, Product.id == OrderItem.product_id
        ).outerjoin(
            Customer, Customer.id == Order.customer_id
        )
        
        # Фильтры
        customer_id = self.filter_customer.currentData()
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        
        status = self.filter_status.currentData()
        if status:
            query = query.filter(Order.status == status)
        
        results = query.all()
        
        headers = [
            "Заказ #", "Клиент", "Статус", "Артикул",
            "Товар", "Кол-во", "Цена", "Сумма"
        ]
        
        data = []
        total_qty = 0
        total_sum = 0
        
        for row in results:
            qty = row.quantity or 0
            total = row.total or 0
            total_qty += qty
            total_sum += total
            
            data.append([
                row.order_id,
                row.customer_name or "Не указан",
                self._translate_status(row.status),
                row.articul or "",
                row.product_name or "",
                qty,
                f"{row.sell_price or 0:.2f}",
                f"{total:.2f}"
            ])
        
        totals = {
            5: total_qty,
            7: f"{total_sum:.2f}"
        }
        
        self.display_data(headers, data, totals)
        
        # Панель итогов
        self.clear_totals()
        self.add_total_label("Всего позиций", len(data))
        self.add_total_label("Продано единиц", f"{total_qty:,}".replace(",", " "))
        self.add_total_label("Общая сумма", f"{total_sum:,.2f} руб.".replace(",", " "))
        self.totals_layout.addStretch()
    
    def _generate_by_customer(self):
        """Отчет с группировкой по клиентам"""
        
        query = self.session.query(
            Customer.full_name.label('customer_name'),
            func.count(func.distinct(Order.id)).label('orders_count'),
            func.sum(OrderItem.quantity).label('total_qty'),
            func.sum(OrderItem.quantity * OrderItem.sell_price).label('total_sum')
        ).join(
            Order, Order.customer_id == Customer.id
        ).join(
            OrderItem, OrderItem.order_id == Order.id
        ).group_by(Customer.id, Customer.full_name)
        
        # Фильтры
        customer_id = self.filter_customer.currentData()
        if customer_id:
            query = query.filter(Customer.id == customer_id)
        
        status = self.filter_status.currentData()
        if status:
            query = query.filter(Order.status == status)
        
        results = query.all()
        
        headers = ["Клиент", "Заказов", "Продано шт.", "Сумма"]
        
        data = []
        total_orders = 0
        total_qty = 0
        total_sum = 0
        
        for row in results:
            orders = row.orders_count or 0
            qty = row.total_qty or 0
            summ = row.total_sum or 0
            
            total_orders += orders
            total_qty += qty
            total_sum += summ
            
            data.append([
                row.customer_name or "Не указан",
                orders,
                qty,
                f"{summ:.2f}"
            ])
        
        totals = {1: total_orders, 2: total_qty, 3: f"{total_sum:.2f}"}
        
        self.display_data(headers, data, totals)
        
        self.clear_totals()
        self.add_total_label("Клиентов", len(data))
        self.add_total_label("Всего заказов", total_orders)
        self.add_total_label("Общая сумма", f"{total_sum:,.2f} руб.".replace(",", " "))
        self.totals_layout.addStretch()
    
    def _generate_by_product(self):
        """Отчет с группировкой по товарам"""
        
        query = self.session.query(
            Product.articul,
            Product.name.label('product_name'),
            func.sum(OrderItem.quantity).label('total_qty'),
            func.sum(OrderItem.quantity * OrderItem.sell_price).label('total_sum')
        ).join(
            OrderItem, OrderItem.product_id == Product.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).group_by(Product.id, Product.articul, Product.name)
        
        # Фильтры
        customer_id = self.filter_customer.currentData()
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        
        status = self.filter_status.currentData()
        if status:
            query = query.filter(Order.status == status)
        
        results = query.order_by(func.sum(OrderItem.quantity * OrderItem.sell_price).desc()).all()
        
        headers = ["Артикул", "Товар", "Продано шт.", "Сумма"]
        
        data = []
        total_qty = 0
        total_sum = 0
        
        for row in results:
            qty = row.total_qty or 0
            summ = row.total_sum or 0
            
            total_qty += qty
            total_sum += summ
            
            data.append([
                row.articul or "",
                row.product_name or "",
                qty,
                f"{summ:.2f}"
            ])
        
        totals = {2: total_qty, 3: f"{total_sum:.2f}"}
        
        self.display_data(headers, data, totals)
        
        self.clear_totals()
        self.add_total_label("Товаров", len(data))
        self.add_total_label("Продано единиц", f"{total_qty:,}".replace(",", " "))
        self.add_total_label("Общая сумма", f"{total_sum:,.2f} руб.".replace(",", " "))
        self.totals_layout.addStretch()
    
    def _translate_status(self, status):
        """Перевод статуса заказа"""
        translations = {
            "new": "Новый",
            "processing": "В обработке",
            "completed": "Выполнен",
            "cancelled": "Отменен",
        }
        return translations.get(status, status or "Не указан")
