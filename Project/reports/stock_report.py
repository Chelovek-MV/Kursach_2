"""
Отчет "Остатки товаров"
Показывает текущие остатки товаров на складах.
ТР-3: адресное хранение, инвентаризация, автоматическое формирование
заявки поставщику при достижении минимальных остатков.
"""

from datetime import datetime

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QDialog, QComboBox,
    QDialogButtonBox, QFormLayout, QSpinBox, QTextEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from sqlalchemy import func

import sys
sys.path.append('..')
from models import (
    Product, Brand, Category, Warehouse, Stock,
    Supplier, PurchaseOrder, PurchaseOrderItem
)
from .base_report import BaseReportWidget


# ---------------------------------------------------------------------------
# Диалог подтверждения создания заявки
# ---------------------------------------------------------------------------

class CreateOrderDialog(QDialog):
    """Диалог параметров автоматической заявки поставщику"""

    def __init__(self, session, low_stock_rows: list, parent=None):
        """
        low_stock_rows: список кортежей (articul, product_name, quantity, min_balance, product_id)
        """
        super().__init__(parent)
        self.session = session
        self.low_stock_rows = low_stock_rows
        self.setWindowTitle("Формирование заявки поставщику")
        self.setMinimumWidth(560)
        self.setMinimumHeight(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        from PyQt6.QtGui import QFont
        title = QLabel(f"Товаров ниже минимума: {len(self.low_stock_rows)}")
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # Таблица товаров для заказа
        self.items_table = QTableWidget(len(self.low_stock_rows), 5)
        self.items_table.setHorizontalHeaderLabels([
            "Артикул", "Наименование", "Остаток", "Мин. остаток", "Заказать"
        ])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        for row, (articul, name, qty, min_bal, pid) in enumerate(self.low_stock_rows):
            deficit = max(min_bal - (qty or 0), 1)
            self.items_table.setItem(row, 0, QTableWidgetItem(articul or ""))
            self.items_table.setItem(row, 1, QTableWidgetItem(name or ""))

            qty_item = QTableWidgetItem(str(qty or 0))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_item.setForeground(QBrush(QColor("#cc0000")))
            self.items_table.setItem(row, 2, qty_item)

            min_item = QTableWidgetItem(str(min_bal or 0))
            min_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_table.setItem(row, 3, min_item)

            order_spin = QSpinBox()
            order_spin.setRange(1, 99999)
            order_spin.setValue(deficit)
            order_spin.setProperty("product_id", pid)
            self.items_table.setCellWidget(row, 4, order_spin)

        self.items_table.resizeColumnsToContents()
        layout.addWidget(self.items_table, 1)

        # Параметры заявки
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("-- Выберите поставщика --", None)
        try:
            for s in self.session.query(Supplier).order_by(Supplier.name).all():
                self.supplier_combo.addItem(s.name or f"#{s.id}", s.id)
        except Exception:
            pass
        form.addRow("Поставщик:", self.supplier_combo)

        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Комментарий к заявке (необязательно)...")
        self.note_edit.setMaximumHeight(70)
        form.addRow("Примечание:", self.note_edit)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Создать заявку")
        ok_btn.setProperty("cssClass", "action")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btn_box.accepted.connect(self._create_order)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _create_order(self):
        supplier_id = self.supplier_combo.currentData()

        try:
            po = PurchaseOrder(
                supplier_id=supplier_id,
                status="pending",
                created_at=datetime.utcnow(),
                note=self.note_edit.toPlainText().strip() or None,
            )
            self.session.add(po)
            self.session.flush()

            total = 0.0
            for row in range(self.items_table.rowCount()):
                spin = self.items_table.cellWidget(row, 4)
                if not spin:
                    continue
                qty = spin.value()
                product_id = spin.property("product_id")
                if not product_id or qty <= 0:
                    continue

                item = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    product_id=product_id,
                    quantity_ordered=qty,
                    quantity_received=0,
                )
                self.session.add(item)

            po.total_amount = total
            self.session.commit()

            QMessageBox.information(
                self, "Заявка создана",
                f"Заявка #{po.id} на {self.items_table.rowCount()} позиций "
                f"со статусом «Ожидает отправки» успешно создана."
            )
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать заявку: {e}")


# ---------------------------------------------------------------------------
# Отчёт по остаткам
# ---------------------------------------------------------------------------

class StockReportWidget(BaseReportWidget):
    """Отчет по остаткам товаров"""

    def __init__(self, session, parent=None):
        self.report_title = "Остатки товаров"
        super().__init__(session, parent)

    def _setup_filters(self):
        """Настройка фильтров"""

        # Первая строка: Склад, Категория
        row1 = QHBoxLayout()

        warehouses = [(w.id, w.name) for w in self.session.query(Warehouse).all()]
        self.filter_warehouse = self.create_combo_filter(warehouses)
        row1.addWidget(self._create_label("Склад:"))
        row1.addWidget(self.filter_warehouse)

        row1.addSpacing(20)

        categories = [(c.id, c.name) for c in self.session.query(Category).all()]
        self.filter_category = self.create_combo_filter(categories)
        row1.addWidget(self._create_label("Категория:"))
        row1.addWidget(self.filter_category)

        row1.addStretch()
        self.filter_layout.addLayout(row1)

        # Вторая строка: Бренд, Чекбоксы
        row2 = QHBoxLayout()

        brands = [(b.id, b.name) for b in self.session.query(Brand).all()]
        self.filter_brand = self.create_combo_filter(brands)
        row2.addWidget(self._create_label("Бренд:"))
        row2.addWidget(self.filter_brand)

        row2.addSpacing(20)

        self.filter_only_available = self.create_checkbox_filter("Только с остатками", True)
        row2.addWidget(self.filter_only_available)

        row2.addSpacing(20)

        self.filter_below_min = self.create_checkbox_filter("Ниже минимума")
        row2.addWidget(self.filter_below_min)

        row2.addStretch()
        self.filter_layout.addLayout(row2)

        # Кнопка автозаявки — добавляем в базовый layout кнопок
        self.btn_create_order = QPushButton("Сформировать заявку поставщику")
        self.btn_create_order.setProperty("cssClass", "success")
        self.btn_create_order.setToolTip(
            "Создать заявку на закупку по всем товарам ниже минимального остатка"
        )
        self.btn_create_order.clicked.connect(self._create_supplier_order)

    def _setup_ui_extra(self):
        """Вызывается после базового _setup_ui — добавляем кнопку заявки"""
        # Вставляем кнопку в строку с кнопкой экспорта
        export_btn = self.btn_export
        # Находим layout кнопки экспорта и добавляем нашу кнопку рядом
        parent_layout = self.layout()
        # Получаем layout последнего элемента и вставляем туда нашу кнопку
        from PyQt6.QtWidgets import QHBoxLayout as HBox
        btn_row = HBox()
        btn_row.addWidget(self.btn_create_order)
        btn_row.addStretch()
        btn_row.addWidget(export_btn)
        parent_layout.addLayout(btn_row)

    def _create_label(self, text):
        """Создать метку"""
        from PyQt6.QtWidgets import QLabel
        label = QLabel(text)
        label.setMinimumWidth(80)
        return label

    def generate_report(self):
        """Формирование отчета"""
        try:
            query = self.session.query(
                Product.id.label("product_id"),
                Product.articul,
                Product.name.label("product_name"),
                Brand.name.label("brand_name"),
                Category.name.label("category_name"),
                Warehouse.name.label("warehouse_name"),
                Stock.quantity,
                Stock.cell_address,
                Product.min_balance
            ).outerjoin(
                Stock, Stock.product_id == Product.id
            ).outerjoin(
                Warehouse, Warehouse.id == Stock.warehouse_id
            ).outerjoin(
                Brand, Brand.id == Product.brand_id
            ).outerjoin(
                Category, Category.id == Product.category_id
            )

            warehouse_id = self.filter_warehouse.currentData()
            if warehouse_id:
                query = query.filter(Stock.warehouse_id == warehouse_id)

            category_id = self.filter_category.currentData()
            if category_id:
                query = query.filter(Product.category_id == category_id)

            brand_id = self.filter_brand.currentData()
            if brand_id:
                query = query.filter(Product.brand_id == brand_id)

            if self.filter_only_available.isChecked():
                query = query.filter(Stock.quantity > 0)

            if self.filter_below_min.isChecked():
                query = query.filter(Stock.quantity < Product.min_balance)

            results = query.all()

            headers = [
                "Артикул", "Наименование", "Бренд", "Категория",
                "Склад", "Ячейка", "Остаток", "Мин. остаток", "Статус"
            ]

            data = []
            total_quantity = 0
            below_min_count = 0

            # Сохраняем для автозаявки
            self._low_stock_rows = []

            for row in results:
                quantity = row.quantity or 0
                min_bal = row.min_balance or 0
                total_quantity += quantity

                is_below = quantity < min_bal
                if is_below:
                    below_min_count += 1
                    self._low_stock_rows.append((
                        row.articul, row.product_name,
                        quantity, min_bal, row.product_id
                    ))

                status = "Ниже минимума" if is_below else ("В норме" if quantity > 0 else "Нет в наличии")

                data.append([
                    row.articul or "",
                    row.product_name or "",
                    row.brand_name or "",
                    row.category_name or "",
                    row.warehouse_name or "Не указан",
                    row.cell_address or "",
                    quantity,
                    min_bal,
                    status,
                ])

            totals = {6: total_quantity}

            self.display_data(headers, data, totals)

            # Подсветка строк "ниже минимума" красным
            self._highlight_low_stock(data)

            # Панель итогов
            self.clear_totals()
            self.add_total_label("Всего позиций", len(data))
            self.add_total_label("Общий остаток", f"{total_quantity:,}".replace(",", " "))
            if below_min_count:
                self.add_total_label(
                    "Ниже минимума", below_min_count, "#cc0000"
                )
            self.totals_layout.addStretch()

            # Кнопка заявки — вставляем в панель итогов справа
            self.totals_layout.addWidget(self.btn_create_order)
            self.btn_create_order.setEnabled(bool(self._low_stock_rows))

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка формирования отчета: {e}")

    def _highlight_low_stock(self, data: list):
        """Подсветить строки с остатком ниже минимума"""
        for row_idx, row_data in enumerate(data):
            qty = row_data[6]
            min_bal = row_data[7]
            if qty < min_bal:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row_idx, col)
                    if item:
                        item.setBackground(QBrush(QColor("#fff3cd")))

    def _create_supplier_order(self):
        """Автоматическое формирование заявки поставщику"""
        if not self._low_stock_rows:
            QMessageBox.information(
                self, "Нет товаров",
                "Нет товаров ниже минимального остатка для формирования заявки.\n"
                "Сначала сформируйте отчет с фильтром «Ниже минимума» или без него."
            )
            return

        dlg = CreateOrderDialog(self.session, self._low_stock_rows, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.generate_report()
