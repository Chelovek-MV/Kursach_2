"""
Карточка клиента
ТР-5: ведение клиентской базы с привязкой истории заказов,
обслуживаемых транспортных средств и условий гарантийного обслуживания.
"""

from datetime import datetime, timedelta, date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QTabWidget, QFormLayout, QTextEdit,
    QDoubleSpinBox, QSpinBox, QComboBox, QDialog, QDialogButtonBox,
    QMessageBox, QAbstractItemView, QFrame, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QBrush


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem с правильной числовой сортировкой"""
    _ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, display: str, value):
        super().__init__(display)
        self.setData(self._ROLE, float(value) if value is not None else 0.0)
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        try:
            return float(self.data(self._ROLE)) < float(other.data(self._ROLE))
        except (TypeError, ValueError):
            return super().__lt__(other)

import sys
sys.path.append('..')
from models import Customer, Vehicle, Order, OrderItem, Product, Warranty


# ---------------------------------------------------------------------------
# Диалог добавления / редактирования гарантии
# ---------------------------------------------------------------------------

class WarrantyDialog(QDialog):
    """Диалог создания / редактирования гарантийного случая"""

    def __init__(self, session, customer: Customer, warranty: Warranty = None, parent=None):
        super().__init__(parent)
        self.session = session
        self.customer = customer
        self.warranty = warranty
        self.is_new = warranty is None
        self.setWindowTitle("Создание гарантии" if self.is_new else "Редактирование гарантии")
        self.setMinimumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Транспортное средство
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItem("-- Без привязки к ТС --", None)
        for v in self.customer.vehicles:
            label = f"{v.brand or ''} {v.model or ''} {v.year or ''} ({v.license_plate or v.vin or '—'})"
            self.vehicle_combo.addItem(label.strip(), v.id)
        form.addRow("Транспортное средство:", self.vehicle_combo)

        # Товар
        self.product_combo = QComboBox()
        self.product_combo.addItem("-- Выберите товар --", None)
        try:
            for p in self.session.query(Product).order_by(Product.articul).limit(5000).all():
                self.product_combo.addItem(f"{p.articul}  {p.name or ''}", p.id)
        except Exception:
            pass
        form.addRow("Запчасть:", self.product_combo)

        # Заказ
        self.order_combo = QComboBox()
        self.order_combo.addItem("-- Без привязки к заказу --", None)
        try:
            for o in self.session.query(Order).filter_by(
                customer_id=self.customer.id
            ).order_by(Order.id.desc()).limit(200).all():
                dt = o.created_at.strftime("%d.%m.%Y") if o.created_at else "—"
                self.order_combo.addItem(f"Заказ #{o.id} от {dt}", o.id)
        except Exception:
            pass
        form.addRow("Заказ:", self.order_combo)

        # Дата начала
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd.MM.yyyy")
        self.start_date.setDate(QDate.currentDate())
        form.addRow("Дата начала:", self.start_date)

        # Срок в месяцах
        self.months_spin = QSpinBox()
        self.months_spin.setRange(1, 120)
        self.months_spin.setValue(12)
        self.months_spin.setSuffix(" мес.")
        self.months_spin.valueChanged.connect(self._update_end_date)
        form.addRow("Срок гарантии:", self.months_spin)

        # Дата окончания (вычисляется автоматически)
        self.end_date_label = QLabel()
        self._update_end_date()
        form.addRow("Дата окончания:", self.end_date_label)

        # Статус
        self.status_combo = QComboBox()
        for code, label in [
            ("active", "Активна"),
            ("expired", "Истекла"),
            ("claimed", "Предъявлена"),
            ("closed", "Закрыта"),
        ]:
            self.status_combo.addItem(label, code)
        form.addRow("Статус:", self.status_combo)

        # Примечание
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(70)
        self.note_edit.setPlaceholderText("Условия гарантии, примечания...")
        form.addRow("Примечание:", self.note_edit)

        layout.addLayout(form)

        # Заполняем поля при редактировании
        if self.warranty:
            if self.warranty.vehicle_id:
                idx = self.vehicle_combo.findData(self.warranty.vehicle_id)
                if idx >= 0:
                    self.vehicle_combo.setCurrentIndex(idx)
            if self.warranty.product_id:
                idx = self.product_combo.findData(self.warranty.product_id)
                if idx >= 0:
                    self.product_combo.setCurrentIndex(idx)
            if self.warranty.order_id:
                idx = self.order_combo.findData(self.warranty.order_id)
                if idx >= 0:
                    self.order_combo.setCurrentIndex(idx)
            if self.warranty.start_date:
                self.start_date.setDate(QDate(
                    self.warranty.start_date.year,
                    self.warranty.start_date.month,
                    self.warranty.start_date.day,
                ))
            self.months_spin.setValue(self.warranty.warranty_months or 12)
            idx_s = self.status_combo.findData(self.warranty.status)
            if idx_s >= 0:
                self.status_combo.setCurrentIndex(idx_s)
            self.note_edit.setPlainText(self.warranty.note or "")

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = btn_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("Сохранить")
        save_btn.setProperty("cssClass", "action")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _update_end_date(self):
        months = self.months_spin.value()
        start = self.start_date.date().toPyDate()
        # Примерно: +months месяцев
        end = date(
            start.year + (start.month - 1 + months) // 12,
            (start.month - 1 + months) % 12 + 1,
            start.day,
        )
        self.end_date_label.setText(end.strftime("%d.%m.%Y"))

    def _save(self):
        product_id = self.product_combo.currentData()
        if not product_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запчасть.")
            return

        months = self.months_spin.value()
        start = self.start_date.date().toPyDate()
        end = date(
            start.year + (start.month - 1 + months) // 12,
            (start.month - 1 + months) % 12 + 1,
            start.day,
        )

        try:
            if self.is_new:
                w = Warranty(customer_id=self.customer.id)
                self.session.add(w)
            else:
                w = self.warranty

            w.vehicle_id = self.vehicle_combo.currentData()
            w.product_id = product_id
            w.order_id = self.order_combo.currentData()
            w.start_date = datetime.combine(start, datetime.min.time())
            w.end_date = datetime.combine(end, datetime.min.time())
            w.warranty_months = months
            w.status = self.status_combo.currentData()
            w.note = self.note_edit.toPlainText().strip() or None

            self.session.commit()
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")


# ---------------------------------------------------------------------------
# Основной виджет карточки клиента
# ---------------------------------------------------------------------------

class CustomerCardWidget(QWidget):
    """
    Карточка клиента со вкладками: реквизиты / транспортные средства /
    история заказов / гарантии.
    ТР-5
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._selected_customer: Customer | None = None
        self._setup_ui()
        self._load_customers()

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Заголовок
        title = QLabel("Клиентская база")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #cc0000;")
        layout.addWidget(title)

        # Горизонтальный сплиттер: список клиентов | карточка
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Левая панель: список клиентов ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        left_layout.addWidget(QLabel("Список клиентов:"))

        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("Поиск по имени, телефону...")
        self.customer_search.textChanged.connect(self._filter_customers)
        left_layout.addWidget(self.customer_search)

        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(3)
        self.customer_table.setHorizontalHeaderLabels(["ФИО", "Телефон", "Скидка"])
        self.customer_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.customer_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.customer_table.horizontalHeader().setStretchLastSection(True)
        self.customer_table.itemSelectionChanged.connect(self._on_customer_selected)
        left_layout.addWidget(self.customer_table, 1)

        btn_row_left = QHBoxLayout()
        self.btn_add_customer = QPushButton("+ Клиент")
        self.btn_add_customer.setProperty("cssClass", "action")
        self.btn_add_customer.clicked.connect(self._add_customer)
        btn_row_left.addWidget(self.btn_add_customer)
        self.btn_edit_customer = QPushButton("Изменить")
        self.btn_edit_customer.setEnabled(False)
        self.btn_edit_customer.clicked.connect(self._edit_customer)
        btn_row_left.addWidget(self.btn_edit_customer)
        left_layout.addLayout(btn_row_left)

        splitter.addWidget(left)

        # --- Правая панель: карточка ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(8)

        self.card_title = QLabel("Выберите клиента")
        font2 = QFont()
        font2.setPointSize(13)
        font2.setBold(True)
        self.card_title.setFont(font2)
        right_layout.addWidget(self.card_title)

        # Итоговые показатели клиента
        self.stats_row = QHBoxLayout()
        self.stat_orders = self._stat_box("Всего заказов", "—")
        self.stat_revenue = self._stat_box("Сумма покупок", "—")
        self.stat_vehicles = self._stat_box("Автомобилей", "—")
        self.stat_warranties = self._stat_box("Гарантий", "—")
        right_layout.addLayout(self.stats_row)

        # Вкладки
        self.tabs = QTabWidget()

        # Вкладка 1: Реквизиты
        self.tab_info = QWidget()
        self._setup_tab_info()
        self.tabs.addTab(self.tab_info, "Реквизиты")

        # Вкладка 2: ТС
        self.tab_vehicles = QWidget()
        self._setup_tab_vehicles()
        self.tabs.addTab(self.tab_vehicles, "Автомобили")

        # Вкладка 3: Заказы
        self.tab_orders = QWidget()
        self._setup_tab_orders()
        self.tabs.addTab(self.tab_orders, "История заказов")

        # Вкладка 4: Гарантии
        self.tab_warranties = QWidget()
        self._setup_tab_warranties()
        self.tabs.addTab(self.tab_warranties, "Гарантии")

        right_layout.addWidget(self.tabs, 1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([300, 800])

        layout.addWidget(splitter, 1)

    def _stat_box(self, label: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: white; border: 1px solid #cccccc; "
            "border-radius: 4px; padding: 4px; }"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(10, 4, 10, 4)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #666; font-size: 11px;")
        val = QLabel(value)
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        val.setFont(font)
        val.setStyleSheet("color: #cc0000;")
        fl.addWidget(lbl)
        fl.addWidget(val)
        frame.val_label = val
        self.stats_row.addWidget(frame)
        return frame

    # Вкладка "Реквизиты"
    def _setup_tab_info(self):
        layout = QFormLayout(self.tab_info)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(12, 12, 12, 12)

        self.info_name = QLabel("—")
        self.info_phone = QLabel("—")
        self.info_email = QLabel("—")
        self.info_telegram = QLabel("—")
        self.info_discount = QLabel("—")
        self.info_created = QLabel("—")
        self.info_note = QLabel("—")
        self.info_note.setWordWrap(True)

        for lbl, val in [
            ("ФИО:", self.info_name),
            ("Телефон:", self.info_phone),
            ("Email:", self.info_email),
            ("Telegram:", self.info_telegram),
            ("Скидка:", self.info_discount),
            ("Зарегистрирован:", self.info_created),
            ("Заметка:", self.info_note),
        ]:
            layout.addRow(lbl, val)

    # Вкладка "Автомобили"
    def _setup_tab_vehicles(self):
        layout = QVBoxLayout(self.tab_vehicles)
        layout.setContentsMargins(0, 6, 0, 0)

        btn_row = QHBoxLayout()
        self.btn_add_vehicle = QPushButton("+ Добавить ТС")
        self.btn_add_vehicle.setEnabled(False)
        self.btn_add_vehicle.clicked.connect(self._add_vehicle)
        btn_row.addWidget(self.btn_add_vehicle)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.vehicles_table = QTableWidget()
        self.vehicles_table.setColumnCount(7)
        self.vehicles_table.setHorizontalHeaderLabels([
            "VIN", "Госномер", "Марка", "Модель", "Год", "Комплект.", "Двигатель"
        ])
        self.vehicles_table.setAlternatingRowColors(True)
        self.vehicles_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vehicles_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.vehicles_table, 1)

    # Вкладка "История заказов"
    def _setup_tab_orders(self):
        layout = QVBoxLayout(self.tab_orders)
        layout.setContentsMargins(0, 6, 0, 0)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(6)
        self.orders_table.setHorizontalHeaderLabels([
            "Заказ #", "Дата", "Статус", "Оплата", "Позиций", "Сумма"
        ])
        self.orders_table.setAlternatingRowColors(True)
        self.orders_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.orders_table.setSortingEnabled(True)
        hdr = self.orders_table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.orders_table.doubleClicked.connect(self._on_order_double_clicked)
        layout.addWidget(self.orders_table, 1)

        # Детали выбранного заказа
        self.order_items_group = QGroupBox("Состав заказа")
        items_layout = QVBoxLayout(self.order_items_group)
        self.order_items_table = QTableWidget()
        self.order_items_table.setColumnCount(4)
        self.order_items_table.setHorizontalHeaderLabels([
            "Артикул", "Наименование", "Кол-во", "Цена"
        ])
        self.order_items_table.setMaximumHeight(160)
        self.order_items_table.horizontalHeader().setStretchLastSection(True)
        items_layout.addWidget(self.order_items_table)
        layout.addWidget(self.order_items_group)

    # Вкладка "Гарантии"
    def _setup_tab_warranties(self):
        layout = QVBoxLayout(self.tab_warranties)
        layout.setContentsMargins(0, 6, 0, 0)

        btn_row = QHBoxLayout()
        self.btn_add_warranty = QPushButton("+ Добавить гарантию")
        self.btn_add_warranty.setProperty("cssClass", "action")
        self.btn_add_warranty.setEnabled(False)
        self.btn_add_warranty.clicked.connect(self._add_warranty)
        btn_row.addWidget(self.btn_add_warranty)

        self.btn_edit_warranty = QPushButton("Изменить")
        self.btn_edit_warranty.setEnabled(False)
        self.btn_edit_warranty.clicked.connect(self._edit_warranty)
        btn_row.addWidget(self.btn_edit_warranty)

        self.btn_delete_warranty = QPushButton("Удалить")
        self.btn_delete_warranty.setEnabled(False)
        self.btn_delete_warranty.clicked.connect(self._delete_warranty)
        btn_row.addWidget(self.btn_delete_warranty)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.warranties_table = QTableWidget()
        self.warranties_table.setColumnCount(8)
        self.warranties_table.setHorizontalHeaderLabels([
            "ID", "Запчасть", "ТС", "Начало", "Окончание",
            "Мес.", "Статус", "Примечание"
        ])
        self.warranties_table.setAlternatingRowColors(True)
        self.warranties_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hdr = self.warranties_table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.warranties_table.itemSelectionChanged.connect(self._on_warranty_selected)
        layout.addWidget(self.warranties_table, 1)

    # ------------------------------------------------------------------
    # Загрузка данных
    # ------------------------------------------------------------------

    def _load_customers(self):
        try:
            self._all_customers = self.session.query(Customer).order_by(Customer.full_name).all()
            self._fill_customer_table(self._all_customers)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _fill_customer_table(self, customers: list):
        self.customer_table.setRowCount(len(customers))
        for row, c in enumerate(customers):
            self.customer_table.setItem(row, 0, QTableWidgetItem(c.full_name or "—"))
            self.customer_table.setItem(row, 1, QTableWidgetItem(c.phone or "—"))
            discount_item = QTableWidgetItem(f"{c.discount_level or 0:.0f}%")
            discount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.customer_table.setItem(row, 2, discount_item)
            self.customer_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, c.id)
        self.customer_table.resizeColumnsToContents()

    def _filter_customers(self, text: str):
        text = text.lower()
        filtered = [
            c for c in self._all_customers
            if text in (c.full_name or "").lower()
            or text in (c.phone or "").lower()
            or text in (c.email or "").lower()
        ]
        self._fill_customer_table(filtered)

    def _on_customer_selected(self):
        row = self.customer_table.currentRow()
        if row < 0:
            return
        item = self.customer_table.item(row, 0)
        if not item:
            return
        customer_id = item.data(Qt.ItemDataRole.UserRole)
        self._selected_customer = self.session.get(Customer, customer_id)
        if self._selected_customer:
            self._load_customer_card()
            self.btn_edit_customer.setEnabled(True)
            self.btn_add_vehicle.setEnabled(True)
            self.btn_add_warranty.setEnabled(True)

    def _load_customer_card(self):
        c = self._selected_customer
        if not c:
            return

        # Заголовок
        self.card_title.setText(c.full_name or "Без имени")

        # Реквизиты
        self.info_name.setText(c.full_name or "—")
        self.info_phone.setText(c.phone or "—")
        self.info_email.setText(c.email or "—")
        self.info_telegram.setText(c.telegram_id or "—")
        self.info_discount.setText(f"{c.discount_level or 0:.1f}%")
        self.info_created.setText(
            c.created_at.strftime("%d.%m.%Y") if c.created_at else "—"
        )
        self.info_note.setText(c.note or "—")

        # Автомобили
        vehicles = c.vehicles
        self.vehicles_table.setRowCount(len(vehicles))
        for row, v in enumerate(vehicles):
            vals = [
                v.vin or "—", v.license_plate or "—",
                v.brand or "—", v.model or "—",
                str(v.year) if v.year else "—",
                v.trim or "—", v.engine or "—",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, v.id)
                self.vehicles_table.setItem(row, col, item)
        self.vehicles_table.resizeColumnsToContents()

        # Заказы
        orders = c.orders
        self.orders_table.setRowCount(len(orders))
        total_revenue = 0.0
        for row, o in enumerate(orders):
            items_count = len(o.items) if o.items else 0
            total_price = o.total_price or 0
            total_revenue += total_price

            id_item = _NumericItem(str(o.id), o.id)
            id_item.setData(Qt.ItemDataRole.UserRole, o.id)
            self.orders_table.setItem(row, 0, id_item)
            dt = o.created_at.strftime("%d.%m.%Y") if o.created_at else "—"
            self.orders_table.setItem(row, 1, QTableWidgetItem(dt))
            self.orders_table.setItem(row, 2, QTableWidgetItem(
                self._translate_status(o.status)
            ))
            self.orders_table.setItem(row, 3, QTableWidgetItem(o.payment_method or "—"))
            self.orders_table.setItem(row, 4, _NumericItem(str(items_count), items_count))
            self.orders_table.setItem(
                row, 5,
                _NumericItem(f"{total_price:,.2f}".replace(",", " "), total_price)
            )

        self.orders_table.resizeColumnsToContents()

        # Гарантии
        self._load_warranties()

        # Статистика
        self.stat_orders.val_label.setText(str(len(orders)))
        self.stat_revenue.val_label.setText(
            f"{total_revenue:,.0f} руб.".replace(",", " ")
        )
        self.stat_vehicles.val_label.setText(str(len(vehicles)))
        self.stat_warranties.val_label.setText(str(len(c.warranties)))

    def _load_warranties(self):
        c = self._selected_customer
        if not c:
            return

        warranties = c.warranties
        self.warranties_table.setRowCount(len(warranties))
        now = datetime.utcnow()

        STATUS_LABELS = {
            "active": "Активна",
            "expired": "Истекла",
            "claimed": "Предъявлена",
            "closed": "Закрыта",
        }
        STATUS_COLORS = {
            "active": "#d4edda",
            "expired": "#fde8e8",
            "claimed": "#fff3cd",
            "closed": "#f8f9fa",
        }

        for row, w in enumerate(warranties):
            product_name = (
                f"{w.product.articul} {w.product.name or ''}"
                if w.product else "—"
            )
            vehicle_label = "—"
            if w.vehicle:
                v = w.vehicle
                vehicle_label = (
                    f"{v.brand or ''} {v.model or ''} {v.year or ''}"
                ).strip() or v.vin or "—"

            start_str = w.start_date.strftime("%d.%m.%Y") if w.start_date else "—"
            end_str = w.end_date.strftime("%d.%m.%Y") if w.end_date else "—"

            # Авто-обновление статуса: если прошла дата — expired
            if w.status == "active" and w.end_date and w.end_date < now:
                w.status = "expired"
                try:
                    self.session.commit()
                except Exception:
                    self.session.rollback()

            status_label = STATUS_LABELS.get(w.status, w.status or "—")
            bg_color = STATUS_COLORS.get(w.status, "#ffffff")

            row_data = [
                str(w.id),
                product_name.strip(),
                vehicle_label,
                start_str,
                end_str,
                str(w.warranty_months or "—"),
                status_label,
                w.note or "",
            ]

            for col, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, w.id)
                item.setBackground(QBrush(QColor(bg_color)))
                self.warranties_table.setItem(row, col, item)

        self.warranties_table.setColumnHidden(0, True)
        self.warranties_table.resizeColumnsToContents()

    # ------------------------------------------------------------------
    # Действия
    # ------------------------------------------------------------------

    def _add_customer(self):
        dlg = _CustomerEditDialog(self.session, None, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_customers()

    def _edit_customer(self):
        if not self._selected_customer:
            return
        dlg = _CustomerEditDialog(self.session, self._selected_customer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_customers()
            self._load_customer_card()

    def _add_vehicle(self):
        if not self._selected_customer:
            return
        dlg = _VehicleEditDialog(self.session, self._selected_customer.id, None, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(self._selected_customer)
            self._load_customer_card()

    def _on_order_double_clicked(self, index):
        row = index.row()
        order_id = self.orders_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        order = self.session.get(Order, order_id)
        if not order:
            return
        items = order.items or []
        self.order_items_table.setRowCount(len(items))
        for i, oi in enumerate(items):
            p = oi.product
            self.order_items_table.setItem(i, 0, QTableWidgetItem(p.articul if p else ""))
            self.order_items_table.setItem(i, 1, QTableWidgetItem(p.name if p else ""))
            self.order_items_table.setItem(i, 2, QTableWidgetItem(str(oi.quantity)))
            price_item = QTableWidgetItem(f"{oi.sell_price or 0:.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.order_items_table.setItem(i, 3, price_item)
        self.order_items_table.resizeColumnsToContents()

    def _add_warranty(self):
        if not self._selected_customer:
            return
        dlg = WarrantyDialog(self.session, self._selected_customer, None, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(self._selected_customer)
            self._load_warranties()

    def _edit_warranty(self):
        row = self.warranties_table.currentRow()
        if row < 0:
            return
        warranty_id = self.warranties_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        warranty = self.session.get(Warranty, warranty_id)
        if not warranty:
            return
        dlg = WarrantyDialog(self.session, self._selected_customer, warranty, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(self._selected_customer)
            self._load_warranties()

    def _delete_warranty(self):
        row = self.warranties_table.currentRow()
        if row < 0:
            return
        warranty_id = self.warranties_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Удаление", "Удалить эту гарантию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                w = self.session.get(Warranty, warranty_id)
                if w:
                    self.session.delete(w)
                    self.session.commit()
                self.session.refresh(self._selected_customer)
                self._load_warranties()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Ошибка", str(e))

    def _on_warranty_selected(self):
        has = bool(self.warranties_table.selectedItems())
        self.btn_edit_warranty.setEnabled(has)
        self.btn_delete_warranty.setEnabled(has)

    def _translate_status(self, status: str) -> str:
        return {
            "new": "Новый", "processing": "В обработке",
            "completed": "Выполнен", "cancelled": "Отменён",
        }.get(status, status or "—")

    def refresh_data(self):
        self._load_customers()
        if self._selected_customer:
            self.session.refresh(self._selected_customer)
            self._load_customer_card()


# ---------------------------------------------------------------------------
# Вспомогательные диалоги редактирования
# ---------------------------------------------------------------------------

class _CustomerEditDialog(QDialog):
    def __init__(self, session, customer: Customer | None, parent=None):
        super().__init__(parent)
        self.session = session
        self.customer = customer
        self.is_new = customer is None
        self.setWindowTitle("Новый клиент" if self.is_new else "Редактирование клиента")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit = QLineEdit(self.customer.full_name if self.customer else "")
        self.phone_edit = QLineEdit(self.customer.phone if self.customer else "")
        self.email_edit = QLineEdit(self.customer.email if self.customer else "")
        self.tg_edit = QLineEdit(self.customer.telegram_id if self.customer else "")
        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, 100)
        self.discount_spin.setSuffix("%")
        self.discount_spin.setValue(self.customer.discount_level if self.customer else 0)
        self.note_edit = QTextEdit(self.customer.note if self.customer else "")
        self.note_edit.setMaximumHeight(70)

        form.addRow("ФИО:", self.name_edit)
        form.addRow("Телефон:", self.phone_edit)
        form.addRow("Email:", self.email_edit)
        form.addRow("Telegram:", self.tg_edit)
        form.addRow("Скидка:", self.discount_spin)
        form.addRow("Заметка:", self.note_edit)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        btn_box.button(QDialogButtonBox.StandardButton.Save).setProperty("cssClass", "action")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _save(self):
        try:
            c = self.customer if not self.is_new else Customer(
                created_at=datetime.utcnow()
            )
            c.full_name = self.name_edit.text().strip() or None
            c.phone = self.phone_edit.text().strip() or None
            c.email = self.email_edit.text().strip() or None
            c.telegram_id = self.tg_edit.text().strip() or None
            c.discount_level = self.discount_spin.value()
            c.note = self.note_edit.toPlainText().strip() or None
            if self.is_new:
                self.session.add(c)
            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", str(e))


class _VehicleEditDialog(QDialog):
    def __init__(self, session, customer_id: int, vehicle: Vehicle | None, parent=None):
        super().__init__(parent)
        self.session = session
        self.customer_id = customer_id
        self.vehicle = vehicle
        self.is_new = vehicle is None
        self.setWindowTitle("Добавить ТС" if self.is_new else "Редактировать ТС")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        v = self.vehicle
        self.vin_edit = QLineEdit(v.vin if v else "")
        self.plate_edit = QLineEdit(v.license_plate if v else "")
        self.brand_edit = QLineEdit(v.brand if v else "")
        self.model_edit = QLineEdit(v.model if v else "")
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2100)
        self.year_spin.setValue(v.year if v and v.year else datetime.now().year)
        self.trim_edit = QLineEdit(v.trim if v else "")
        self.engine_edit = QLineEdit(v.engine if v else "")

        form.addRow("VIN:", self.vin_edit)
        form.addRow("Госномер:", self.plate_edit)
        form.addRow("Марка:", self.brand_edit)
        form.addRow("Модель:", self.model_edit)
        form.addRow("Год:", self.year_spin)
        form.addRow("Комплектация:", self.trim_edit)
        form.addRow("Двигатель:", self.engine_edit)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        btn_box.button(QDialogButtonBox.StandardButton.Save).setProperty("cssClass", "action")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _save(self):
        try:
            vehicle = self.vehicle if not self.is_new else Vehicle(
                customer_id=self.customer_id
            )
            vehicle.vin = self.vin_edit.text().strip() or None
            vehicle.license_plate = self.plate_edit.text().strip() or None
            vehicle.brand = self.brand_edit.text().strip() or None
            vehicle.model = self.model_edit.text().strip() or None
            vehicle.year = self.year_spin.value()
            vehicle.trim = self.trim_edit.text().strip() or None
            vehicle.engine = self.engine_edit.text().strip() or None
            if self.is_new:
                self.session.add(vehicle)
            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", str(e))
