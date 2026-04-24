"""
Отчет "Движение товаров"
История прихода и расхода товаров
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDateEdit, QLineEdit
from PyQt6.QtCore import QDate
from sqlalchemy import func, or_, union_all, literal

import sys
sys.path.append('..')
from models import Product, Brand, Warehouse, Stock, Order, OrderItem, PurchaseOrder
from .base_report import BaseReportWidget


class MovementReportWidget(BaseReportWidget):
    """Отчет по движению товаров"""
    
    def __init__(self, session, parent=None):
        self.report_title = "Движение товаров"
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
        
        # Вторая строка: Товар, Склад
        row2 = QHBoxLayout()
        
        # Поиск товара по артикулу
        row2.addWidget(self._create_label("Артикул:"))
        self.filter_articul = QLineEdit()
        self.filter_articul.setPlaceholderText("Введите артикул...")
        self.filter_articul.setMinimumWidth(200)
        row2.addWidget(self.filter_articul)
        
        row2.addSpacing(20)
        
        # Склад
        warehouses = [(w.id, w.name) for w in self.session.query(Warehouse).all()]
        self.filter_warehouse = self.create_combo_filter(warehouses)
        row2.addWidget(self._create_label("Склад:"))
        row2.addWidget(self.filter_warehouse)
        
        row2.addStretch()
        self.filter_layout.addLayout(row2)
        
        # Третья строка: Тип операции
        row3 = QHBoxLayout()
        
        operations = [
            ("income", "Приход"),
            ("expense", "Расход"),
        ]
        self.filter_operation = self.create_combo_filter(operations)
        row3.addWidget(self._create_label("Операция:"))
        row3.addWidget(self.filter_operation)
        
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
            # Получаем данные о расходах (продажи)
            expenses_query = self.session.query(
                Order.id.label('doc_id'),
                literal('Заказ клиента').label('doc_type'),
                literal('Расход').label('operation'),
                Product.articul,
                Product.name.label('product_name'),
                OrderItem.quantity,
                literal(None).label('warehouse_name')
            ).join(
                OrderItem, OrderItem.order_id == Order.id
            ).join(
                Product, Product.id == OrderItem.product_id
            )
            
            # Фильтр по артикулу
            articul = self.filter_articul.text().strip()
            if articul:
                expenses_query = expenses_query.filter(
                    Product.articul.ilike(f"%{articul}%")
                )
            
            # Фильтр по типу операции
            operation_type = self.filter_operation.currentData()
            
            # Собираем результаты
            results = []
            
            if operation_type is None or operation_type == "expense":
                results.extend(expenses_query.all())
            
            # Для демонстрации добавим текущие остатки как "приход"
            if operation_type is None or operation_type == "income":
                income_query = self.session.query(
                    Stock.id.label('doc_id'),
                    literal('Остаток на складе').label('doc_type'),
                    literal('Остаток').label('operation'),
                    Product.articul,
                    Product.name.label('product_name'),
                    Stock.quantity,
                    Warehouse.name.label('warehouse_name')
                ).join(
                    Product, Product.id == Stock.product_id
                ).outerjoin(
                    Warehouse, Warehouse.id == Stock.warehouse_id
                )
                
                if articul:
                    income_query = income_query.filter(
                        Product.articul.ilike(f"%{articul}%")
                    )
                
                warehouse_id = self.filter_warehouse.currentData()
                if warehouse_id:
                    income_query = income_query.filter(Stock.warehouse_id == warehouse_id)
                
                results.extend(income_query.all())
            
            headers = [
                "Документ #", "Тип документа", "Операция",
                "Артикул", "Товар", "Количество", "Склад"
            ]
            
            data = []
            total_income = 0
            total_expense = 0
            
            for row in results:
                qty = row.quantity or 0
                
                if row.operation == "Расход":
                    total_expense += qty
                elif row.operation in ("Приход", "Остаток"):
                    total_income += qty
                
                data.append([
                    row.doc_id,
                    row.doc_type,
                    row.operation,
                    row.articul or "",
                    row.product_name or "",
                    qty,
                    row.warehouse_name or "-"
                ])
            
            # Сортируем по типу операции
            data.sort(key=lambda x: (x[2], x[0]))
            
            self.display_data(headers, data)
            
            # Панель итогов
            self.clear_totals()
            self.add_total_label("Всего записей", len(data))
            self.add_total_label("Приход/Остаток", f"{total_income:,}".replace(",", " "), "#28a745")
            self.add_total_label("Расход", f"{total_expense:,}".replace(",", " "), "#cc0000")
            self.add_total_label("Баланс", f"{total_income - total_expense:,}".replace(",", " "))
            self.totals_layout.addStretch()
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчета: {e}")
