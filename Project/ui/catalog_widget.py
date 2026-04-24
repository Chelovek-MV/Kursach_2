"""
Виджет для работы со справочниками
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QMessageBox, QHeaderView, QDialog, QFormLayout,
    QDialogButtonBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import sys
sys.path.append('..')
from models import (
    Brand, Category, Product, Customer, Supplier, 
    Warehouse, Order, PurchaseOrder, Stock, OrderItem
)


class CatalogWidget(QWidget):
    """Виджет справочника с таблицей и поиском"""
    
    # Маппинг названий справочников на модели
    MODEL_MAP = {
        "products": Product,
        "brands": Brand,
        "categories": Category,
        "customers": Customer,
        "suppliers": Supplier,
        "warehouses": Warehouse,
        "orders": Order,
        "purchase_orders": PurchaseOrder,
        "stocks": Stock,
    }
    
    # Русские названия колонок
    COLUMN_NAMES = {
        "id": "ID",
        "name": "Наименование",
        "articul": "Артикул",
        "clean_articul": "Чистый артикул",
        "brand_id": "Бренд ID",
        "category_id": "Категория ID",
        "min_balance": "Мин. остаток",
        "full_name": "ФИО",
        "phone": "Телефон",
        "telegram_id": "Telegram ID",
        "discount_level": "Скидка %",
        "address": "Адрес",
        "api_key": "API ключ",
        "api_endpoint": "API адрес",
        "delivery_days": "Срок доставки (дней)",
        "customer_id": "Клиент ID",
        "status": "Статус",
        "payment_method": "Способ оплаты",
        "total_price": "Сумма",
        "total_amount": "Сумма",
        "supplier_id": "Поставщик ID",
        "product_id": "Товар ID",
        "warehouse_id": "Склад ID",
        "quantity": "Количество",
        "cell_address": "Ячейка",
    }
    
    def __init__(self, session, catalog_type: str, parent=None):
        super().__init__(parent)
        
        self.session = session
        self.catalog_type = catalog_type
        self.model_class = self.MODEL_MAP.get(catalog_type)
        self.current_data = []
        
        self._setup_ui()
        self.refresh_data()
    
    def _setup_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Панель поиска
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Поиск:")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст для поиска...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setMinimumWidth(300)
        search_layout.addWidget(self.search_input)
        
        search_layout.addStretch()
        
        # Счетчик записей
        self.count_label = QLabel("Записей: 0")
        self.count_label.setStyleSheet("color: #666666;")
        search_layout.addWidget(self.count_label)
        
        layout.addLayout(search_layout)
        
        # Таблица данных
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_record)
        
        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        layout.addWidget(self.table)
        
        # Панель кнопок
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Создать")
        self.btn_add.setProperty("cssClass", "action")
        self.btn_add.clicked.connect(self.add_record)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_edit = QPushButton("Изменить")
        self.btn_edit.clicked.connect(self.edit_record)
        btn_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self.delete_record)
        btn_layout.addWidget(self.btn_delete)
        
        btn_layout.addStretch()
        
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh_data)
        btn_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(btn_layout)
    
    def refresh_data(self):
        """Загрузка данных из БД"""
        if not self.model_class:
            return
        
        self.table.blockSignals(True)
        
        try:
            self.current_data = self.session.query(self.model_class).all()
            
            if not self.current_data:
                self.table.setRowCount(0)
                self.table.setColumnCount(0)
                self.count_label.setText("Записей: 0")
                return
            
            # Получаем колонки
            columns = list(self.model_class.__table__.columns.keys())
            
            # Русские названия
            headers = [self.COLUMN_NAMES.get(col, col) for col in columns]
            
            self.table.setColumnCount(len(columns))
            self.table.setRowCount(len(self.current_data))
            self.table.setHorizontalHeaderLabels(headers)
            
            # Сохраняем оригинальные названия колонок
            self._columns = columns
            
            # Заполняем таблицу
            for row, obj in enumerate(self.current_data):
                for col, column in enumerate(columns):
                    value = getattr(obj, column, "")
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    
                    # ID делаем нередактируемым
                    if column == "id":
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setForeground(Qt.GlobalColor.gray)
                    
                    self.table.setItem(row, col, item)
            
            # Автоподбор ширины колонок
            self.table.resizeColumnsToContents()
            
            self.count_label.setText(f"Записей: {len(self.current_data)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {e}")
        
        finally:
            self.table.blockSignals(False)
    
    def _on_search(self, text: str):
        """Фильтрация по поиску"""
        text = text.lower()
        
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
    
    def add_record(self):
        """Добавление новой записи"""
        if not self.model_class:
            return
        
        dialog = EditDialog(self.session, self.model_class, None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
    
    def edit_record(self):
        """Редактирование выбранной записи"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите запись для редактирования")
            return
        
        # Находим видимую строку
        visible_row = 0
        for i in range(self.table.rowCount()):
            if not self.table.isRowHidden(i):
                if i == row:
                    break
                visible_row += 1
        
        if row < len(self.current_data):
            obj = self.current_data[row]
            dialog = EditDialog(self.session, self.model_class, obj, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_data()
    
    def delete_record(self):
        """Удаление выбранной записи"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите запись для удаления")
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить выбранную запись?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                obj = self.current_data[row]
                self.session.delete(obj)
                self.session.commit()
                self.refresh_data()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Ошибка", f"Ошибка удаления: {e}")
    
    def export_to_excel(self):
        """Экспорт в Excel"""
        try:
            from utils.excel_export import export_table_to_excel
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить как", 
                f"{self.catalog_type}.xlsx",
                "Excel файлы (*.xlsx)"
            )
            
            if file_path:
                export_table_to_excel(self.table, file_path)
                QMessageBox.information(self, "Экспорт", f"Данные экспортированы в {file_path}")
        except ImportError:
            QMessageBox.warning(self, "Ошибка", "Для экспорта установите библиотеку openpyxl")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")


class EditDialog(QDialog):
    """Диалог редактирования записи"""
    
    def __init__(self, session, model_class, obj=None, parent=None):
        super().__init__(parent)
        
        self.session = session
        self.model_class = model_class
        self.obj = obj
        self.is_new = obj is None
        self.editors = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Создание интерфейса диалога"""
        self.setWindowTitle("Создание записи" if self.is_new else "Редактирование записи")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Форма с полями
        form_layout = QFormLayout()
        
        columns = self.model_class.__table__.columns
        
        for column in columns:
            col_name = column.name
            
            # Пропускаем ID для новых записей
            if col_name == "id" and self.is_new:
                continue
            
            # Получаем русское название
            label = CatalogWidget.COLUMN_NAMES.get(col_name, col_name)
            
            # Создаем редактор в зависимости от типа
            col_type = str(column.type)
            
            if "INTEGER" in col_type:
                editor = QSpinBox()
                editor.setRange(-999999, 999999)
                if self.obj and hasattr(self.obj, col_name):
                    value = getattr(self.obj, col_name)
                    if value is not None:
                        editor.setValue(int(value))
            elif "FLOAT" in col_type:
                editor = QDoubleSpinBox()
                editor.setRange(-999999, 999999)
                editor.setDecimals(2)
                if self.obj and hasattr(self.obj, col_name):
                    value = getattr(self.obj, col_name)
                    if value is not None:
                        editor.setValue(float(value))
            else:
                editor = QLineEdit()
                if self.obj and hasattr(self.obj, col_name):
                    value = getattr(self.obj, col_name)
                    if value is not None:
                        editor.setText(str(value))
            
            # ID только для чтения
            if col_name == "id":
                if isinstance(editor, QLineEdit):
                    editor.setReadOnly(True)
                else:
                    editor.setEnabled(False)
            
            self.editors[col_name] = editor
            form_layout.addRow(f"{label}:", editor)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        
        # Стилизация кнопки сохранения
        save_btn = btn_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("Сохранить")
        save_btn.setProperty("cssClass", "action")
        
        cancel_btn = btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("Отмена")
        
        layout.addWidget(btn_box)
    
    def _save(self):
        """Сохранение записи"""
        try:
            if self.is_new:
                self.obj = self.model_class()
                self.session.add(self.obj)
            
            for col_name, editor in self.editors.items():
                if col_name == "id":
                    continue
                
                if isinstance(editor, QSpinBox):
                    value = editor.value()
                elif isinstance(editor, QDoubleSpinBox):
                    value = editor.value()
                elif isinstance(editor, QLineEdit):
                    value = editor.text() or None
                else:
                    value = None
                
                setattr(self.obj, col_name, value)
            
            self.session.commit()
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")
