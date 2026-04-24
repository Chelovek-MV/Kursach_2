"""
Диалог быстрого создания операции
Поддерживает: покупку, продажу, перемещение между складами, приход, списание
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QPushButton, QFrame, QStackedWidget,
    QWidget, QLineEdit, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import sys
sys.path.append('../..')
from models import (
    Product, Customer, Supplier, Warehouse, Stock,
    Order, OrderItem, PurchaseOrder
)


# Описания типов операций
OPERATION_TYPES = [
    ("sale",      "Продажа",                 "Продажа товара клиенту"),
    ("purchase",  "Закупка",                 "Приход товара от поставщика"),
    ("move",      "Перемещение",             "Перемещение товара между складами"),
    ("receipt",   "Приход (инвентаризация)", "Постановка товара на склад"),
    ("writeoff",  "Списание",                "Списание товара со склада"),
]


class QuickOperationDialog(QDialog):
    """Универсальный диалог быстрого создания операции"""

    def __init__(self, session, operation_type: str = "sale", parent=None):
        super().__init__(parent)
        self.session = session
        self.operation_type = operation_type

        self.setWindowTitle("Быстрое создание операции")
        self.setMinimumWidth(480)
        self.setModal(True)

        self._setup_ui()
        self._on_type_changed(
            next(i for i, (t, _, _) in enumerate(OPERATION_TYPES) if t == operation_type)
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Заголовок ---
        title = QLabel("Новая операция")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #cc0000;")
        layout.addWidget(title)

        # --- Разделитель ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #cccccc;")
        layout.addWidget(line)

        # --- Тип операции ---
        type_layout = QFormLayout()
        type_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.type_combo = QComboBox()
        for _, label, _ in OPERATION_TYPES:
            self.type_combo.addItem(label)

        # Устанавливаем текущий тип
        current_index = next(
            i for i, (t, _, _) in enumerate(OPERATION_TYPES)
            if t == self.operation_type
        )
        self.type_combo.setCurrentIndex(current_index)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        type_layout.addRow("Тип операции:", self.type_combo)
        layout.addLayout(type_layout)

        # --- Описание операции ---
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet("color: #888888; font-size: 12px; padding: 2px 0 8px 0;")
        layout.addWidget(self.desc_label)

        # --- Стек панелей для разных операций ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Создаём панели для каждого типа
        self.panels = {}
        panel_builders = {
            "sale":      self._build_sale_panel,
            "purchase":  self._build_purchase_panel,
            "move":      self._build_move_panel,
            "receipt":   self._build_receipt_panel,
            "writeoff":  self._build_writeoff_panel,
        }
        for op_type, _, _ in OPERATION_TYPES:
            panel = panel_builders[op_type]()
            self.panels[op_type] = panel
            self.stack.addWidget(panel)

        # --- Кнопки ---
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = btn_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("Провести")
        save_btn.setProperty("cssClass", "action")
        cancel_btn = btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("Отмена")

        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Панели для конкретных типов операций
    # ------------------------------------------------------------------

    def _make_form_widget(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)
        return widget, form

    def _build_sale_panel(self):
        widget, form = self._make_form_widget()

        # Товар
        self.sale_product = QComboBox()
        self._fill_products(self.sale_product)
        form.addRow("Товар:", self.sale_product)

        # Клиент
        self.sale_customer = QComboBox()
        self.sale_customer.addItem("— не выбран —", None)
        try:
            for c in self.session.query(Customer).order_by(Customer.full_name).all():
                self.sale_customer.addItem(c.full_name or f"#{c.id}", c.id)
        except Exception:
            pass
        form.addRow("Клиент:", self.sale_customer)

        # Склад
        self.sale_warehouse = QComboBox()
        self._fill_warehouses(self.sale_warehouse)
        form.addRow("Склад:", self.sale_warehouse)

        # Количество
        self.sale_qty = QSpinBox()
        self.sale_qty.setRange(1, 999999)
        self.sale_qty.setValue(1)
        form.addRow("Количество:", self.sale_qty)

        # Цена продажи
        self.sale_price = QDoubleSpinBox()
        self.sale_price.setRange(0, 99999999)
        self.sale_price.setDecimals(2)
        self.sale_price.setSuffix(" ₽")
        form.addRow("Цена продажи:", self.sale_price)

        # Способ оплаты
        self.sale_payment = QComboBox()
        for m in ["Наличные", "Карта", "Перевод", "Безналичный"]:
            self.sale_payment.addItem(m)
        form.addRow("Оплата:", self.sale_payment)

        return widget

    def _build_purchase_panel(self):
        widget, form = self._make_form_widget()

        # Товар
        self.pur_product = QComboBox()
        self._fill_products(self.pur_product)
        form.addRow("Товар:", self.pur_product)

        # Поставщик
        self.pur_supplier = QComboBox()
        self.pur_supplier.addItem("— не выбран —", None)
        try:
            for s in self.session.query(Supplier).order_by(Supplier.name).all():
                self.pur_supplier.addItem(s.name or f"#{s.id}", s.id)
        except Exception:
            pass
        form.addRow("Поставщик:", self.pur_supplier)

        # Склад назначения
        self.pur_warehouse = QComboBox()
        self._fill_warehouses(self.pur_warehouse)
        form.addRow("Склад прихода:", self.pur_warehouse)

        # Количество
        self.pur_qty = QSpinBox()
        self.pur_qty.setRange(1, 999999)
        self.pur_qty.setValue(1)
        form.addRow("Количество:", self.pur_qty)

        # Цена закупки
        self.pur_price = QDoubleSpinBox()
        self.pur_price.setRange(0, 99999999)
        self.pur_price.setDecimals(2)
        self.pur_price.setSuffix(" ₽")
        form.addRow("Цена закупки:", self.pur_price)

        return widget

    def _build_move_panel(self):
        widget, form = self._make_form_widget()

        # Товар
        self.move_product = QComboBox()
        self._fill_products(self.move_product)
        form.addRow("Товар:", self.move_product)

        # Откуда
        self.move_from = QComboBox()
        self._fill_warehouses(self.move_from)
        form.addRow("Откуда (склад):", self.move_from)

        # Куда
        self.move_to = QComboBox()
        self._fill_warehouses(self.move_to)
        form.addRow("Куда (склад):", self.move_to)

        # Количество
        self.move_qty = QSpinBox()
        self.move_qty.setRange(1, 999999)
        self.move_qty.setValue(1)
        form.addRow("Количество:", self.move_qty)

        return widget

    def _build_receipt_panel(self):
        widget, form = self._make_form_widget()

        # Товар
        self.rec_product = QComboBox()
        self._fill_products(self.rec_product)
        form.addRow("Товар:", self.rec_product)

        # Склад
        self.rec_warehouse = QComboBox()
        self._fill_warehouses(self.rec_warehouse)
        form.addRow("Склад:", self.rec_warehouse)

        # Количество
        self.rec_qty = QSpinBox()
        self.rec_qty.setRange(1, 999999)
        self.rec_qty.setValue(1)
        form.addRow("Количество:", self.rec_qty)

        # Ячейка
        self.rec_cell = QLineEdit()
        self.rec_cell.setPlaceholderText("например: A1-01")
        form.addRow("Ячейка:", self.rec_cell)

        return widget

    def _build_writeoff_panel(self):
        widget, form = self._make_form_widget()

        # Товар
        self.wo_product = QComboBox()
        self._fill_products(self.wo_product)
        form.addRow("Товар:", self.wo_product)

        # Склад
        self.wo_warehouse = QComboBox()
        self._fill_warehouses(self.wo_warehouse)
        form.addRow("Склад:", self.wo_warehouse)

        # Количество
        self.wo_qty = QSpinBox()
        self.wo_qty.setRange(1, 999999)
        self.wo_qty.setValue(1)
        form.addRow("Количество:", self.wo_qty)

        # Причина
        self.wo_reason = QComboBox()
        for r in ["Брак / повреждение", "Истечение срока", "Пересорт", "Другое"]:
            self.wo_reason.addItem(r)
        form.addRow("Причина:", self.wo_reason)

        return widget

    # ------------------------------------------------------------------
    # Вспомогательные методы заполнения
    # ------------------------------------------------------------------

    def _fill_products(self, combo: QComboBox):
        combo.addItem("— выберите товар —", None)
        try:
            for p in self.session.query(Product).order_by(Product.name).all():
                label = f"{p.articul}  {p.name or ''}"
                combo.addItem(label.strip(), p.id)
        except Exception:
            pass

    def _fill_warehouses(self, combo: QComboBox):
        combo.addItem("— выберите склад —", None)
        try:
            for w in self.session.query(Warehouse).order_by(Warehouse.name).all():
                combo.addItem(w.name or f"Склад #{w.id}", w.id)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Переключение типа
    # ------------------------------------------------------------------

    def _on_type_changed(self, index: int):
        op_type, _, desc = OPERATION_TYPES[index]
        self.operation_type = op_type
        self.desc_label.setText(desc)
        panel = self.panels.get(op_type)
        if panel:
            self.stack.setCurrentWidget(panel)

    # ------------------------------------------------------------------
    # Сохранение
    # ------------------------------------------------------------------

    def _save(self):
        try:
            if self.operation_type == "sale":
                self._save_sale()
            elif self.operation_type == "purchase":
                self._save_purchase()
            elif self.operation_type == "move":
                self._save_move()
            elif self.operation_type == "receipt":
                self._save_receipt()
            elif self.operation_type == "writeoff":
                self._save_writeoff()

            self.session.commit()
            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка ввода", str(e))
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось провести операцию:\n{e}")

    def _get_combo_data(self, combo: QComboBox, label: str):
        data = combo.currentData()
        if data is None:
            raise ValueError(f"Выберите значение для поля «{label}»")
        return data

    def _adjust_stock(self, product_id: int, warehouse_id: int, delta: int):
        """Изменяет остаток товара на складе (создаёт запись если нет)."""
        stock = (
            self.session.query(Stock)
            .filter_by(product_id=product_id, warehouse_id=warehouse_id)
            .first()
        )
        if stock is None:
            if delta < 0:
                raise ValueError("На выбранном складе нет остатка этого товара")
            stock = Stock(product_id=product_id, warehouse_id=warehouse_id, quantity=0)
            self.session.add(stock)
        new_qty = stock.quantity + delta
        if new_qty < 0:
            raise ValueError(
                f"Недостаточно товара на складе. Доступно: {stock.quantity} шт."
            )
        stock.quantity = new_qty

    # --- Продажа ---
    def _save_sale(self):
        product_id  = self._get_combo_data(self.sale_product,   "Товар")
        warehouse_id = self._get_combo_data(self.sale_warehouse, "Склад")
        customer_id  = self.sale_customer.currentData()  # может быть None
        qty          = self.sale_qty.value()
        price        = self.sale_price.value()
        payment      = self.sale_payment.currentText()

        # Снимаем остаток
        self._adjust_stock(product_id, warehouse_id, -qty)

        # Создаём заказ
        order = Order(
            customer_id=customer_id,
            status="completed",
            payment_method=payment,
            total_price=price * qty,
        )
        self.session.add(order)
        self.session.flush()  # получаем order.id

        item = OrderItem(
            order_id=order.id,
            product_id=product_id,
            quantity=qty,
            buy_price=0,
            sell_price=price,
        )
        self.session.add(item)

    # --- Закупка ---
    def _save_purchase(self):
        product_id   = self._get_combo_data(self.pur_product,   "Товар")
        warehouse_id = self._get_combo_data(self.pur_warehouse,  "Склад прихода")
        supplier_id  = self.pur_supplier.currentData()
        qty          = self.pur_qty.value()
        price        = self.pur_price.value()

        # Пополняем остаток
        self._adjust_stock(product_id, warehouse_id, qty)

        # Создаём заказ поставщику
        po = PurchaseOrder(
            supplier_id=supplier_id,
            status="received",
            total_amount=price * qty,
        )
        self.session.add(po)

    # --- Перемещение ---
    def _save_move(self):
        product_id    = self._get_combo_data(self.move_product, "Товар")
        from_wh_id    = self._get_combo_data(self.move_from,    "Склад отправки")
        to_wh_id      = self._get_combo_data(self.move_to,      "Склад назначения")
        qty           = self.move_qty.value()

        if from_wh_id == to_wh_id:
            raise ValueError("Склад отправки и назначения не могут совпадать")

        self._adjust_stock(product_id, from_wh_id, -qty)
        self._adjust_stock(product_id, to_wh_id,   qty)

    # --- Приход (инвентаризация) ---
    def _save_receipt(self):
        product_id   = self._get_combo_data(self.rec_product,   "Товар")
        warehouse_id = self._get_combo_data(self.rec_warehouse,  "Склад")
        qty          = self.rec_qty.value()
        cell         = self.rec_cell.text().strip() or None

        stock = (
            self.session.query(Stock)
            .filter_by(product_id=product_id, warehouse_id=warehouse_id)
            .first()
        )
        if stock is None:
            stock = Stock(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=0,
                cell_address=cell,
            )
            self.session.add(stock)
        stock.quantity += qty
        if cell:
            stock.cell_address = cell

    # --- Списание ---
    def _save_writeoff(self):
        product_id   = self._get_combo_data(self.wo_product,   "Товар")
        warehouse_id = self._get_combo_data(self.wo_warehouse,  "Склад")
        qty          = self.wo_qty.value()

        self._adjust_stock(product_id, warehouse_id, -qty)
