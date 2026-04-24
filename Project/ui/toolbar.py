"""
Панель инструментов
"""

from PyQt6.QtWidgets import (
    QToolBar, QToolButton, QWidget, QHBoxLayout, QLabel, QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QAction


class MainToolBar(QToolBar):
    """Главная панель инструментов"""
    
    # Сигналы для действий
    action_add = pyqtSignal()
    action_edit = pyqtSignal()
    action_delete = pyqtSignal()
    action_refresh = pyqtSignal()
    action_export = pyqtSignal()
    # Сигнал быстрой операции передаёт тип операции строкой
    action_quick_op = pyqtSignal(str)

    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setMovable(False)
        self.setFloatable(False)
        
        self._setup_toolbar()
    
    def _setup_toolbar(self):
        """Создание элементов панели"""

        # ---- Кнопка быстрой операции (выпадающее меню) ----
        self.btn_quick_op = QToolButton()
        self.btn_quick_op.setText("+ Операция")
        self.btn_quick_op.setToolTip("Быстро создать операцию (Ctrl+O)")
        self.btn_quick_op.setStyleSheet(
            "QToolButton {"
            "  background-color: #cc0000;"
            "  color: white;"
            "  border: 1px solid #990000;"
            "  border-radius: 4px;"
            "  padding: 5px 14px;"
            "  font-weight: bold;"
            "}"
            "QToolButton:hover {"
            "  background-color: #ff3333;"
            "  border-color: #cc0000;"
            "}"
            "QToolButton:pressed {"
            "  background-color: #990000;"
            "}"
            "QToolButton::menu-indicator { width: 0; }"
        )
        self.btn_quick_op.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # Выпадающее меню с типами операций
        quick_menu = QMenu(self.btn_quick_op)

        op_items = [
            ("sale",      "Продажа"),
            ("purchase",  "Закупка"),
            ("move",      "Перемещение"),
            ("receipt",   "Приход (инвентаризация)"),
            ("writeoff",  "Списание"),
        ]

        for op_type, op_label in op_items:
            act = QAction(op_label, quick_menu)
            act.triggered.connect(
                lambda checked=False, t=op_type: self.action_quick_op.emit(t)
            )
            quick_menu.addAction(act)

        self.btn_quick_op.setMenu(quick_menu)
        # Клик по основной части кнопки открывает диалог продажи по умолчанию
        self.btn_quick_op.clicked.connect(
            lambda: self.action_quick_op.emit("sale")
        )

        self.addWidget(self.btn_quick_op)
        self.addSeparator()

        # Кнопка "Создать"
        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setToolTip("Создать новую запись (Ctrl+N)")
        self.btn_add.clicked.connect(self.action_add.emit)
        self.addWidget(self.btn_add)
        
        # Кнопка "Изменить"
        self.btn_edit = QToolButton()
        self.btn_edit.setText("Изменить")
        self.btn_edit.setToolTip("Изменить выбранную запись (Enter)")
        self.btn_edit.clicked.connect(self.action_edit.emit)
        self.addWidget(self.btn_edit)
        
        # Кнопка "Удалить"
        self.btn_delete = QToolButton()
        self.btn_delete.setText("Удалить")
        self.btn_delete.setToolTip("Удалить выбранную запись (Delete)")
        self.btn_delete.clicked.connect(self.action_delete.emit)
        self.addWidget(self.btn_delete)
        
        self.addSeparator()
        
        # Кнопка "Обновить"
        self.btn_refresh = QToolButton()
        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setToolTip("Обновить данные (F5)")
        self.btn_refresh.clicked.connect(self.action_refresh.emit)
        self.addWidget(self.btn_refresh)
        
        self.addSeparator()
        
        # Кнопка "Экспорт"
        self.btn_export = QToolButton()
        self.btn_export.setText("Экспорт в Excel")
        self.btn_export.setToolTip("Экспортировать в Excel (Ctrl+E)")
        self.btn_export.clicked.connect(self.action_export.emit)
        self.addWidget(self.btn_export)
        
        # Растягивающийся элемент
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, 
                            spacer.sizePolicy().Policy.Preferred)
        self.addWidget(spacer)
        
        # Заголовок текущего раздела
        self.title_label = QLabel("Добро пожаловать")
        self.title_label.setObjectName("headerLabel")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #cc0000; padding-right: 20px;")
        self.addWidget(self.title_label)
    
    def set_title(self, title: str):
        """Установка заголовка"""
        self.title_label.setText(title)
    
    def set_catalog_mode(self):
        """Режим справочника - все кнопки активны"""
        self.btn_add.setEnabled(True)
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.btn_export.setEnabled(True)
    
    def set_report_mode(self):
        """Режим отчета - только обновление и экспорт"""
        self.btn_add.setEnabled(False)
        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_refresh.setEnabled(True)
        self.btn_export.setEnabled(True)
    
    def set_welcome_mode(self):
        """Режим приветствия - все отключено"""
        self.btn_add.setEnabled(False)
        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_export.setEnabled(False)
