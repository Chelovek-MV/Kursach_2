"""
Виджет управления кросс-номерами (аналогами запчастей)
ТР-2: автоматическое сопоставление оригинальных номеров с аналогами
      с учётом взаимозаменяемости и применимости.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QComboBox, QDialog, QFormLayout, QDialogButtonBox,
    QMessageBox, QCheckBox, QFrame, QSplitter, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QBrush

import sys
sys.path.append('..')
from models import Product, Brand, CrossReference, Stock


# Типы связей
RELATION_TYPES = [
    ("equivalent", "Полный аналог (взаимозаменяемый)"),
    ("compatible", "Совместим (применим)"),
    ("supersedes", "Заменяет (оригинал устарел)"),
]

RELATION_COLORS = {
    "equivalent": "#d4edda",   # зелёный
    "compatible": "#fff3cd",   # жёлтый
    "supersedes": "#cce5ff",   # синий
}


class AddCrossRefDialog(QDialog):
    """Диалог добавления кросс-номера"""

    def __init__(self, session, product: Product, parent=None):
        super().__init__(parent)
        self.session = session
        self.product = product
        self.setWindowTitle("Добавить аналог / кросс-номер")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        info = QLabel(
            f"Источник: <b>{self.product.articul}</b> "
            f"({(self.product.brand.name if self.product.brand else '')})"
            f" — {self.product.name or ''}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Выбор товара-аналога
        self.analog_combo = QComboBox()
        self.analog_combo.setEditable(True)
        self.analog_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.analog_combo.lineEdit().setPlaceholderText("Начните вводить артикул или название...")
        self._load_products()
        form.addRow("Аналог:", self.analog_combo)

        # Тип связи
        self.type_combo = QComboBox()
        for code, label in RELATION_TYPES:
            self.type_combo.addItem(label, code)
        form.addRow("Тип замены:", self.type_combo)

        # Источник информации
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Каталог, поставщик, ручной ввод...")
        form.addRow("Источник:", self.source_edit)

        # Проверена ли замена
        self.verified_check = QCheckBox("Замена проверена и подтверждена")
        form.addRow("", self.verified_check)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = btn_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("Добавить")
        save_btn.setProperty("cssClass", "action")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_products(self):
        try:
            products = (
                self.session.query(Product)
                .filter(Product.id != self.product.id)
                .order_by(Product.articul)
                .limit(5000)
                .all()
            )
            for p in products:
                brand_name = p.brand.name if p.brand else ""
                label = f"{p.articul}  {brand_name}  {p.name or ''}".strip()
                self.analog_combo.addItem(label, p.id)
        except Exception:
            pass

    def _save(self):
        analog_id = self.analog_combo.currentData()
        if not analog_id:
            QMessageBox.warning(self, "Ошибка", "Выберите товар-аналог из списка.")
            return

        if analog_id == self.product.id:
            QMessageBox.warning(self, "Ошибка", "Нельзя создать кросс-номер товара с самим собой.")
            return

        try:
            # Проверяем что такая пара ещё не существует
            existing = (
                self.session.query(CrossReference)
                .filter(
                    (
                        (CrossReference.product_id_1 == self.product.id) &
                        (CrossReference.product_id_2 == analog_id)
                    ) | (
                        (CrossReference.product_id_1 == analog_id) &
                        (CrossReference.product_id_2 == self.product.id)
                    )
                )
                .first()
            )
            if existing:
                QMessageBox.warning(self, "Дублирование", "Такой кросс-номер уже существует.")
                return

            ref = CrossReference(
                product_id_1=self.product.id,
                product_id_2=analog_id,
                relation_type=self.type_combo.currentData(),
                source=self.source_edit.text().strip() or None,
                is_verified=self.verified_check.isChecked(),
            )
            self.session.add(ref)
            self.session.commit()
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")


class CrossRefWidget(QWidget):
    """
    Виджет управления кросс-номерами.
    ТР-2: сопоставление оригиналов с аналогами, типы взаимозаменяемости,
    отображение наличия аналогов на складе.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._selected_product = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Заголовок
        title = QLabel("Кросс-номера и аналоги запчастей")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #cc0000;")
        layout.addWidget(title)

        # Легенда
        legend_row = QHBoxLayout()
        for code, label in RELATION_TYPES:
            badge = QLabel(f"  {label}  ")
            badge.setStyleSheet(
                f"background-color: {RELATION_COLORS[code]}; "
                f"border: 1px solid #cccccc; border-radius: 3px; "
                f"padding: 2px 4px; font-size: 11px;"
            )
            legend_row.addWidget(badge)
        legend_row.addStretch()
        layout.addLayout(legend_row)

        # Сплиттер: левая панель (поиск товара) + правая (кросс-номера)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- ЛЕВАЯ ПАНЕЛЬ: поиск товара ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(8)

        search_label = QLabel("Поиск товара:")
        search_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(search_label)

        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Артикул или наименование...")
        self.product_search.textChanged.connect(self._search_products)
        left_layout.addWidget(self.product_search)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(3)
        self.products_table.setHorizontalHeaderLabels(["Артикул", "Бренд", "Наименование"])
        self.products_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.products_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.products_table.horizontalHeader().setStretchLastSection(True)
        self.products_table.itemSelectionChanged.connect(self._on_product_selected)
        left_layout.addWidget(self.products_table, 1)

        splitter.addWidget(left_widget)

        # --- ПРАВАЯ ПАНЕЛЬ: кросс-номера выбранного товара ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(8)

        self.selected_label = QLabel("Выберите товар слева")
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.selected_label.setFont(font2)
        right_layout.addWidget(self.selected_label)

        # Кнопки управления
        btn_row = QHBoxLayout()

        self.btn_add_ref = QPushButton("+ Добавить аналог")
        self.btn_add_ref.setProperty("cssClass", "action")
        self.btn_add_ref.setEnabled(False)
        self.btn_add_ref.clicked.connect(self._add_cross_ref)
        btn_row.addWidget(self.btn_add_ref)

        self.btn_delete_ref = QPushButton("Удалить")
        self.btn_delete_ref.setEnabled(False)
        self.btn_delete_ref.clicked.connect(self._delete_cross_ref)
        btn_row.addWidget(self.btn_delete_ref)

        self.btn_toggle_verified = QPushButton("Отметить проверенным")
        self.btn_toggle_verified.setEnabled(False)
        self.btn_toggle_verified.clicked.connect(self._toggle_verified)
        btn_row.addWidget(self.btn_toggle_verified)

        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        # Таблица аналогов
        self.cross_table = QTableWidget()
        self.cross_table.setColumnCount(8)
        self.cross_table.setHorizontalHeaderLabels([
            "ID", "Артикул аналога", "Бренд", "Наименование",
            "Тип замены", "Источник", "Проверен", "На складе"
        ])
        self.cross_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cross_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.cross_table.setAlternatingRowColors(True)
        self.cross_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hdr = self.cross_table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.cross_table.itemSelectionChanged.connect(self._on_ref_selected)
        right_layout.addWidget(self.cross_table, 1)

        # Итог
        self.cross_count_label = QLabel("Аналогов: 0")
        self.cross_count_label.setStyleSheet("color: #666666; font-size: 11px;")
        right_layout.addWidget(self.cross_count_label)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([350, 550])

        layout.addWidget(splitter, 1)

        # Загружаем все товары при старте
        self._search_products("")

    # ------------------------------------------------------------------
    # Поиск товаров
    # ------------------------------------------------------------------

    def _search_products(self, text: str):
        try:
            q = self.session.query(Product).join(Brand, Brand.id == Product.brand_id)
            if text.strip():
                q = q.filter(
                    Product.articul.ilike(f"%{text}%")
                    | Product.name.ilike(f"%{text}%")
                    | Brand.name.ilike(f"%{text}%")
                )
            products = q.order_by(Product.articul).limit(300).all()

            self.products_table.setRowCount(len(products))
            for row, p in enumerate(products):
                self.products_table.setItem(row, 0, QTableWidgetItem(p.articul or ""))
                self.products_table.setItem(
                    row, 1,
                    QTableWidgetItem(p.brand.name if p.brand else "")
                )
                self.products_table.setItem(row, 2, QTableWidgetItem(p.name or ""))
                # Сохраняем id в первой ячейке
                self.products_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, p.id)

            self.products_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_product_selected(self):
        rows = self.products_table.selectedItems()
        if not rows:
            return
        row = self.products_table.currentRow()
        product_id = self.products_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._selected_product = self.session.get(Product, product_id)
        if self._selected_product:
            brand = self._selected_product.brand.name if self._selected_product.brand else ""
            self.selected_label.setText(
                f"{self._selected_product.articul}  [{brand}]  {self._selected_product.name or ''}"
            )
            self.btn_add_ref.setEnabled(True)
            self._load_cross_refs()

    # ------------------------------------------------------------------
    # Кросс-номера
    # ------------------------------------------------------------------

    def _load_cross_refs(self):
        if not self._selected_product:
            return

        pid = self._selected_product.id

        # Берём пары в обе стороны
        refs_1 = (
            self.session.query(CrossReference)
            .filter(CrossReference.product_id_1 == pid)
            .all()
        )
        refs_2 = (
            self.session.query(CrossReference)
            .filter(CrossReference.product_id_2 == pid)
            .all()
        )

        # Нормализуем: all_refs = list of (ref, analog_product)
        all_refs = []
        for ref in refs_1:
            analog = self.session.get(Product, ref.product_id_2)
            if analog:
                all_refs.append((ref, analog))
        for ref in refs_2:
            analog = self.session.get(Product, ref.product_id_1)
            if analog:
                all_refs.append((ref, analog))

        self.cross_table.setRowCount(len(all_refs))

        type_labels = {code: label for code, label in RELATION_TYPES}

        for row, (ref, analog) in enumerate(all_refs):
            brand_name = analog.brand.name if analog.brand else ""

            # Наличие на складе
            stock_total = (
                self.session.query(Stock)
                .filter_by(product_id=analog.id)
                .all()
            )
            on_stock = sum(s.quantity for s in stock_total if s.quantity)

            items_data = [
                (str(ref.id), None),
                (analog.articul or "", None),
                (brand_name, None),
                (analog.name or "", None),
                (type_labels.get(ref.relation_type, ref.relation_type or ""), ref.relation_type),
                (ref.source or "", None),
                ("Да" if ref.is_verified else "Нет", None),
                (str(on_stock) if on_stock else "0", None),
            ]

            for col, (val, _extra) in enumerate(items_data):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, ref.id)

                # Цвет строки по типу замены
                bg = RELATION_COLORS.get(ref.relation_type or "", "#ffffff")
                item.setBackground(QBrush(QColor(bg)))

                # Выравнивание числовых
                if col in (0, 7):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )

                # Выделить проверенные
                if col == 6 and ref.is_verified:
                    item.setForeground(QBrush(QColor("#28a745")))

                self.cross_table.setItem(row, col, item)

        self.cross_table.setColumnHidden(0, True)  # скрываем ID
        self.cross_table.resizeColumnsToContents()
        self.cross_count_label.setText(f"Аналогов: {len(all_refs)}")

    def _on_ref_selected(self):
        has = bool(self.cross_table.selectedItems())
        self.btn_delete_ref.setEnabled(has)
        self.btn_toggle_verified.setEnabled(has)

    def _add_cross_ref(self):
        if not self._selected_product:
            return
        dlg = AddCrossRefDialog(self.session, self._selected_product, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_cross_refs()

    def _delete_cross_ref(self):
        row = self.cross_table.currentRow()
        if row < 0:
            return
        ref_id = self.cross_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Удаление", "Удалить этот кросс-номер?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                ref = self.session.get(CrossReference, ref_id)
                if ref:
                    self.session.delete(ref)
                    self.session.commit()
                self._load_cross_refs()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Ошибка", str(e))

    def _toggle_verified(self):
        row = self.cross_table.currentRow()
        if row < 0:
            return
        ref_id = self.cross_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            ref = self.session.get(CrossReference, ref_id)
            if ref:
                ref.is_verified = not ref.is_verified
                self.session.commit()
            self._load_cross_refs()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", str(e))

    def refresh_data(self):
        self._search_products(self.product_search.text())
        if self._selected_product:
            self._load_cross_refs()
