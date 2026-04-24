"""
Базовый класс для отчетов
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QDateEdit, QCheckBox,
    QHeaderView, QFileDialog, QMessageBox,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QBrush


class NumericTableWidgetItem(QTableWidgetItem):
    """
    QTableWidgetItem с правильной числовой сортировкой.
    Хранит float в UserRole+1; при сравнении использует числовое значение.
    """
    _SORT_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, display_text: str, numeric_value):
        super().__init__(display_text)
        self.setData(self._SORT_ROLE, float(numeric_value) if numeric_value is not None else 0.0)
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        try:
            my_val = self.data(self._SORT_ROLE)
            other_val = other.data(self._SORT_ROLE)
            if my_val is not None and other_val is not None:
                return float(my_val) < float(other_val)
        except (TypeError, ValueError):
            pass
        return super().__lt__(other)


class BaseReportWidget(QWidget):
    """Базовый класс для всех отчетов"""
    
    def __init__(self, session, parent=None):
        super().__init__(parent)
        
        self.session = session
        self.report_data = []
        self.report_headers = []
        self.report_title = "Отчет"
        
        self._setup_ui()
        self._setup_filters()
        self._connect_signals()
    
    def _setup_ui(self):
        """Создание базового интерфейса отчета"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Панель фильтров
        self.filter_group = QGroupBox("Параметры отчета")
        self.filter_layout = QVBoxLayout(self.filter_group)
        layout.addWidget(self.filter_group)
        
        # Кнопка формирования отчета
        btn_layout = QHBoxLayout()
        
        self.btn_generate = QPushButton("Сформировать отчет")
        self.btn_generate.setProperty("cssClass", "action")
        self.btn_generate.setMinimumWidth(200)
        self.btn_generate.setMinimumHeight(40)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.btn_generate.setFont(font)
        btn_layout.addWidget(self.btn_generate)
        
        btn_layout.addStretch()
        
        # Счетчик записей
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #666666; font-size: 12px;")
        btn_layout.addWidget(self.count_label)
        
        layout.addLayout(btn_layout)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(line)
        
        # Таблица результатов
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        layout.addWidget(self.table, 1)
        
        # Панель итогов
        self.totals_layout = QHBoxLayout()
        layout.addLayout(self.totals_layout)
        
        # Кнопка экспорта
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        self.btn_export = QPushButton("Экспорт в Excel")
        self.btn_export.setProperty("cssClass", "success")
        self.btn_export.clicked.connect(self.export_to_excel)
        export_layout.addWidget(self.btn_export)
        
        layout.addLayout(export_layout)
    
    def _setup_filters(self):
        """Настройка фильтров отчета (переопределяется в наследниках)"""
        pass
    
    def _connect_signals(self):
        """Подключение сигналов"""
        self.btn_generate.clicked.connect(self.generate_report)
    
    def add_filter_row(self, *widgets):
        """Добавить строку фильтров"""
        row_layout = QHBoxLayout()
        for widget in widgets:
            if isinstance(widget, str):
                label = QLabel(widget)
                label.setMinimumWidth(120)
                row_layout.addWidget(label)
            elif widget is None:
                row_layout.addStretch()
            else:
                row_layout.addWidget(widget)
        self.filter_layout.addLayout(row_layout)
    
    def create_date_filter(self, label: str, default_days_ago: int = 30):
        """Создать фильтр по дате"""
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd.MM.yyyy")
        date_edit.setDate(QDate.currentDate().addDays(-default_days_ago))
        return date_edit
    
    def create_combo_filter(self, items: list, include_all: bool = True):
        """Создать выпадающий фильтр"""
        combo = QComboBox()
        combo.setMinimumWidth(200)
        if include_all:
            combo.addItem("-- Все --", None)
        for item_id, item_name in items:
            combo.addItem(item_name, item_id)
        return combo
    
    def create_checkbox_filter(self, label: str, checked: bool = False):
        """Создать чекбокс фильтр"""
        checkbox = QCheckBox(label)
        checkbox.setChecked(checked)
        return checkbox
    
    def generate_report(self):
        """Формирование отчета (переопределяется в наследниках)"""
        pass
    
    def display_data(self, headers: list, data: list, totals: dict = None):
        """
        Отображение данных в таблице
        
        Args:
            headers: Список заголовков колонок
            data: Список строк данных
            totals: Словарь с итогами (индекс колонки -> значение)
        """
        self.report_headers = headers
        self.report_data = data
        
        self.table.blockSignals(True)
        self.table.clear()
        
        row_count = len(data) + (1 if totals else 0)
        
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(row_count)
        self.table.setHorizontalHeaderLabels(headers)
        
        # Заполняем данные
        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                if isinstance(value, (int, float)):
                    item = NumericTableWidgetItem(str(value), value)
                else:
                    item = QTableWidgetItem(str(value) if value is not None else "")

                self.table.setItem(row, col, item)
        
        # Итоговая строка
        if totals:
            totals_row = len(data)
            for col in range(len(headers)):
                if col in totals:
                    value = totals[col]
                    item = QTableWidgetItem(str(value))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                    if isinstance(value, (int, float)):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item = QTableWidgetItem("")
                
                # Фоновый цвет для итоговой строки
                item.setBackground(QBrush(QColor("#fff8f8")))
                self.table.setItem(totals_row, col, item)
            
            # Подпись "Итого"
            first_item = self.table.item(totals_row, 0)
            if first_item and not first_item.text():
                first_item.setText("ИТОГО:")
                first_item.setFont(QFont("", -1, QFont.Weight.Bold))
        
        # Автоподбор ширины
        self.table.resizeColumnsToContents()
        
        self.table.blockSignals(False)
        
        # Обновляем счетчик
        self.count_label.setText(f"Найдено записей: {len(data)}")
    
    def refresh_data(self):
        """Обновление данных (переформирование отчета)"""
        self.generate_report()
    
    def export_to_excel(self):
        """Экспорт отчета в Excel"""
        if not self.report_data:
            QMessageBox.warning(self, "Внимание", "Сначала сформируйте отчет")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет",
            f"{self.report_title}.xlsx",
            "Excel файлы (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            from utils.excel_export import export_report_to_excel
            
            # Собираем итоги из таблицы
            totals = {}
            totals_row = len(self.report_data)
            if self.table.rowCount() > totals_row:
                for col in range(self.table.columnCount()):
                    item = self.table.item(totals_row, col)
                    if item and item.text() and item.text() != "ИТОГО:":
                        try:
                            value = float(item.text().replace(" ", "").replace(",", "."))
                            totals[col] = value
                        except:
                            totals[col] = item.text()
            
            export_report_to_excel(
                self.report_headers,
                self.report_data,
                file_path,
                title=self.report_title,
                totals=totals if totals else None
            )
            
            QMessageBox.information(
                self, "Экспорт",
                f"Отчет успешно экспортирован:\n{file_path}"
            )
            
        except ImportError:
            QMessageBox.warning(
                self, "Ошибка",
                "Для экспорта установите библиотеку openpyxl:\npip install openpyxl"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")
    
    def clear_totals(self):
        """Очистка панели итогов"""
        while self.totals_layout.count():
            item = self.totals_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def add_total_label(self, label: str, value, color: str = None):
        """Добавить метку с итогом"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(label_widget)
        
        value_widget = QLabel(str(value))
        value_font = QFont()
        value_font.setBold(True)
        value_font.setPointSize(14)
        value_widget.setFont(value_font)
        if color:
            value_widget.setStyleSheet(f"color: {color};")
        else:
            value_widget.setStyleSheet("color: #cc0000;")
        layout.addWidget(value_widget)
        
        self.totals_layout.addWidget(frame)
