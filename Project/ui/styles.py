"""
Стили интерфейса
Цветовая схема: светло-серый фон, красные акценты
"""

# Основные цвета
COLORS = {
    'background': '#f0f0f0',
    'primary': '#cc0000',
    'primary_hover': '#ff3333',
    'primary_dark': '#990000',
    'white': '#ffffff',
    'border': '#cccccc',
    'border_dark': '#999999',
    'text': '#333333',
    'text_light': '#666666',
    'selection': '#ffcccc',
    'header_bg': '#cc0000',
    'success': '#28a745',
    'warning': '#ffc107',
}

# Главный стиль приложения
MAIN_STYLE = """
/* Главное окно */
QMainWindow {
    background-color: #f0f0f0;
}

/* Виджеты */
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #333333;
}

/* Панель навигации (дерево) */
QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 5px;
    outline: none;
}

QTreeWidget::item {
    padding: 8px 5px;
    border-radius: 3px;
}

QTreeWidget::item:hover {
    background-color: #ffeeee;
}

QTreeWidget::item:selected {
    background-color: #ff7575;
    color: white;
}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {
    border-image: none;
    image: url(none);
}

QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {
    border-image: none;
    image: url(none);
}

/* Заголовки секций */
QTreeWidget::item:has-children {
    font-weight: bold;
    color: #cc0000;
}

/* Таблицы */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    gridline-color: #e0e0e0;
    selection-background-color: #ffcccc;
    selection-color: #333333;
}

QTableWidget::item {
    padding: 5px;
}

QTableWidget::item:selected {
    background-color: #ffcccc;
    color: #333333;
}

QHeaderView::section {
    background-color: #cc0000;
    color: white;
    padding: 8px 5px;
    border: none;
    border-right: 1px solid #990000;
    border-bottom: 1px solid #990000;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #ff3333;
}

/* Кнопки */
QPushButton {
    background-color: #e8e8e8;
    border: 1px solid #999999;
    border-radius: 4px;
    padding: 8px 20px;
    font-weight: normal;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #d0d0d0;
    border-color: #cc0000;
}

QPushButton:pressed {
    background-color: #c0c0c0;
}

QPushButton:disabled {
    background-color: #f0f0f0;
    color: #999999;
    border-color: #cccccc;
}

/* Кнопки действий (красные) */
QPushButton#actionButton, QPushButton[cssClass="action"] {
    background-color: #cc0000;
    color: white;
    border: 1px solid #990000;
    font-weight: bold;
}

QPushButton#actionButton:hover, QPushButton[cssClass="action"]:hover {
    background-color: #ff3333;
}

QPushButton#actionButton:pressed, QPushButton[cssClass="action"]:pressed {
    background-color: #990000;
}

/* Кнопки успеха (зеленые) */
QPushButton#successButton, QPushButton[cssClass="success"] {
    background-color: #28a745;
    color: white;
    border: 1px solid #1e7e34;
    font-weight: bold;
}

QPushButton#successButton:hover, QPushButton[cssClass="success"]:hover {
    background-color: #34ce57;
}

/* Группы (GroupBox) */
QGroupBox {
    font-weight: bold;
    border: 2px solid #cc0000;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    background-color: #cc0000;
    color: white;
    border-radius: 3px;
    left: 10px;
}

/* Поля ввода */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #cc0000;
    border-width: 2px;
}

QLineEdit:disabled {
    background-color: #f5f5f5;
    color: #999999;
}

/* Выпадающие списки */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px 10px;
    min-width: 120px;
}

QComboBox:focus {
    border-color: #cc0000;
}

QComboBox::drop-down {
    border: none;
    width: 25px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    selection-background-color: #cc0000;
    selection-color: white;
}

/* Дата */
QDateEdit {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px 10px;
}

QDateEdit:focus {
    border-color: #cc0000;
}

QDateEdit::drop-down {
    border: none;
    width: 25px;
}

/* Чекбоксы */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #999999;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #cc0000;
    border-color: #cc0000;
}

QCheckBox::indicator:hover {
    border-color: #cc0000;
}

/* Вкладки */
QTabWidget::pane {
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #e8e8e8;
    border: 1px solid #cccccc;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 20px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 1px solid #ffffff;
    font-weight: bold;
    color: #cc0000;
}

QTabBar::tab:hover:!selected {
    background-color: #ffeeee;
}

/* Скроллбары */
QScrollBar:vertical {
    border: none;
    background-color: #f0f0f0;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #cccccc;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #cc0000;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    border: none;
    background-color: #f0f0f0;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #cccccc;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #cc0000;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Статусбар */
QStatusBar {
    background-color: #e8e8e8;
    border-top: 1px solid #cccccc;
    padding: 5px;
}

/* Тулбар */
QToolBar {
    background-color: #f0f0f0;
    border: none;
    border-bottom: 1px solid #cccccc;
    padding: 5px;
    spacing: 5px;
}

QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 10px;
}

QToolButton:hover {
    background-color: #ffeeee;
    border-color: #cc0000;
}

QToolButton:pressed {
    background-color: #ffcccc;
}

/* Лейблы */
QLabel {
    color: #333333;
}

QLabel#headerLabel {
    font-size: 18px;
    font-weight: bold;
    color: #cc0000;
    padding: 10px 0;
}

QLabel#sectionLabel {
    font-size: 14px;
    font-weight: bold;
    color: #666666;
}

/* Сплиттер */
QSplitter::handle {
    background-color: #cccccc;
}

QSplitter::handle:hover {
    background-color: #cc0000;
}

/* Итоговая строка в таблице */
QTableWidget#totalsRow {
    background-color: #fff8f8;
    font-weight: bold;
}

/* Меню */
QMenuBar {
    background-color: #f0f0f0;
    border-bottom: 1px solid #cccccc;
}

QMenuBar::item {
    padding: 8px 15px;
}

QMenuBar::item:selected {
    background-color: #cc0000;
    color: white;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #cccccc;
}

QMenu::item {
    padding: 8px 30px;
}

QMenu::item:selected {
    background-color: #cc0000;
    color: white;
}

QMenu::separator {
    height: 1px;
    background-color: #cccccc;
    margin: 5px 0;
}
"""

# Стиль для диалоговых окон
DIALOG_STYLE = """
QDialog {
    background-color: #f0f0f0;
}

QDialog QLabel {
    font-size: 13px;
}

QDialog QLineEdit {
    min-width: 200px;
}
"""

# Стиль для панели фильтров отчета
FILTER_PANEL_STYLE = """
QWidget#filterPanel {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 6px;
    padding: 10px;
}
"""
