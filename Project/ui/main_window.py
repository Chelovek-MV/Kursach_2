"""
Главное окно приложения
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStackedWidget, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction, QKeySequence
from PyQt6.QtGui import QShortcut

from .styles import MAIN_STYLE
from .navigation_panel import NavigationPanel
from .toolbar import MainToolBar


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self, session):
        super().__init__()

        self.session = session
        self.current_widget = None

        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()

        self._show_welcome()

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.setWindowTitle("Управление автозапчастями")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(MAIN_STYLE)

    def _setup_menu(self):
        menubar = self.menuBar()

        # Файл
        file_menu = menubar.addMenu("Файл")

        action_export = QAction("Экспорт в Excel", self)
        action_export.setShortcut(QKeySequence("Ctrl+E"))
        action_export.triggered.connect(self._on_export)
        file_menu.addAction(action_export)

        file_menu.addSeparator()

        action_exit = QAction("Выход", self)
        action_exit.setShortcut(QKeySequence("Ctrl+Q"))
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        # Справочники
        catalog_menu = menubar.addMenu("Справочники")
        for name, item_id in [
            ("Товары",      "products"),
            ("Бренды",      "brands"),
            ("Категории",   "categories"),
            ("Поставщики",  "suppliers"),
            ("Склады",      "warehouses"),
        ]:
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, i=item_id: self._open_section("catalog", i)
            )
            catalog_menu.addAction(action)

        # Поиск
        search_menu = menubar.addMenu("Поиск")
        for name, item_id in [
            ("Поиск по VIN",          "vin_search"),
            ("Кросс-номера / аналоги", "cross_ref"),
        ]:
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, i=item_id: self._open_section("search", i)
            )
            search_menu.addAction(action)

        # CRM
        crm_menu = menubar.addMenu("CRM")
        for name, item_id in [
            ("Клиенты / Карточка", "customer_card"),
        ]:
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, i=item_id: self._open_section("crm", i)
            )
            crm_menu.addAction(action)

        # Отчеты
        reports_menu = menubar.addMenu("Отчеты")
        for name, item_id in [
            ("Остатки товаров",         "stock_report"),
            ("Продажи",                  "sales_report"),
            ("Прибыльность",             "profit_report"),
            ("Движение товаров",         "movement_report"),
            ("Динамика продаж",          "dynamics_report"),
            ("Оборачиваемость запасов",  "turnover_report"),
        ]:
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, i=item_id: self._open_section("report", i)
            )
            reports_menu.addAction(action)

        # Помощь
        help_menu = menubar.addMenu("Помощь")
        action_about = QAction("О программе", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar = MainToolBar()
        main_layout.addWidget(self.toolbar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.nav_panel = NavigationPanel()
        self.nav_panel.setMinimumWidth(200)
        self.nav_panel.setMaximumWidth(370)
        self.splitter.addWidget(self.nav_panel)

        self.content_stack = QStackedWidget()
        self.splitter.addWidget(self.content_stack)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setSizes([260, 1140])

        main_layout.addWidget(self.splitter)

        self.statusBar().showMessage("Готово")

    def _setup_shortcuts(self):
        sc = QShortcut(QKeySequence("Ctrl+O"), self)
        sc.activated.connect(lambda: self._on_quick_op("sale"))

        sc_vin = QShortcut(QKeySequence("Ctrl+V"), self)
        sc_vin.activated.connect(lambda: self._open_section("search", "vin_search"))

    def _connect_signals(self):
        self.nav_panel.item_selected.connect(self._open_section)

        self.toolbar.action_add.connect(self._on_add)
        self.toolbar.action_edit.connect(self._on_edit)
        self.toolbar.action_delete.connect(self._on_delete)
        self.toolbar.action_refresh.connect(self._on_refresh)
        self.toolbar.action_export.connect(self._on_export)
        self.toolbar.action_quick_op.connect(self._on_quick_op)

    def _show_welcome(self):
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Управление автозапчастями")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #cc0000;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Выберите раздел в панели навигации слева")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: #666666; margin-top: 20px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        hints = QLabel(
            "\n\nБыстрый доступ:\n"
            "• Ctrl+O  — быстрая операция (продажа, закупка, ...)\n"
            "• Ctrl+V  — поиск по VIN\n"
            "• Ctrl+E  — экспорт в Excel\n\n"
            "Разделы:\n"
            "• Поиск — поиск по VIN, кросс-номера и аналоги\n"
            "• CRM / Клиенты — карточка клиента, ТС, гарантии\n"
            "• Отчеты — продажи, оборачиваемость запасов, динамика"
        )
        hints_font = QFont()
        hints_font.setPointSize(12)
        hints.setFont(hints_font)
        hints.setStyleSheet("color: #888888;")
        hints.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hints)

        self.content_stack.addWidget(welcome)
        self.content_stack.setCurrentWidget(welcome)

        self.toolbar.set_welcome_mode()
        self.toolbar.set_title("Добро пожаловать")

    # ------------------------------------------------------------------
    # Маршрутизация
    # ------------------------------------------------------------------

    def _open_section(self, section: str, item_id: str):
        """Открыть раздел по секции и идентификатору"""

        from .catalog_widget import CatalogWidget
        from reports.stock_report import StockReportWidget
        from reports.sales_report import SalesReportWidget
        from reports.profit_report import ProfitReportWidget
        from reports.movement_report import MovementReportWidget
        from reports.dynamics_report import DynamicsReportWidget
        from reports.turnover_report import TurnoverReportWidget
        from .vin_search_widget import VinSearchWidget
        from .cross_ref_widget import CrossRefWidget
        from .customer_card_widget import CustomerCardWidget

        titles = {
            # Справочники
            "products":         "Справочник: Товары",
            "brands":           "Справочник: Бренды",
            "categories":       "Справочник: Категории",
            "customers":        "Справочник: Клиенты",
            "suppliers":        "Справочник: Поставщики",
            "warehouses":       "Справочник: Склады",
            # Поиск
            "vin_search":       "Поиск по VIN",
            "cross_ref":        "Кросс-номера и аналоги",
            # CRM
            "customer_card":    "Клиенты / Карточка клиента",
            # Документы
            "orders":           "Документы: Заказы клиентов",
            "purchase_orders":  "Документы: Закупки",
            "stocks":           "Документы: Остатки на складах",
            # Отчеты
            "stock_report":     "Отчет: Остатки товаров",
            "sales_report":     "Отчет: Продажи",
            "profit_report":    "Отчет: Прибыльность",
            "movement_report":  "Отчет: Движение товаров",
            "dynamics_report":  "Отчет: Динамика продаж",
            "turnover_report":  "Отчет: Оборачиваемость запасов",
        }

        title = titles.get(item_id, item_id)
        self.toolbar.set_title(title)

        # --- Создание виджета ---
        if section == "catalog":
            widget = CatalogWidget(self.session, item_id)
            self.toolbar.set_catalog_mode()

        elif section == "document":
            widget = CatalogWidget(self.session, item_id)
            self.toolbar.set_catalog_mode()

        elif section == "search":
            if item_id == "vin_search":
                widget = VinSearchWidget(self.session)
            elif item_id == "cross_ref":
                widget = CrossRefWidget(self.session)
            else:
                return
            self.toolbar.set_report_mode()

        elif section == "crm":
            widget = CustomerCardWidget(self.session)
            self.toolbar.set_catalog_mode()

        elif section == "report":
            report_map = {
                "stock_report":    StockReportWidget,
                "sales_report":    SalesReportWidget,
                "profit_report":   ProfitReportWidget,
                "movement_report": MovementReportWidget,
                "dynamics_report": DynamicsReportWidget,
                "turnover_report": TurnoverReportWidget,
            }
            cls = report_map.get(item_id)
            if not cls:
                return
            widget = cls(self.session)
            self.toolbar.set_report_mode()

        else:
            return

        # Заменяем виджет в стеке
        if self.current_widget:
            self.content_stack.removeWidget(self.current_widget)
            self.current_widget.deleteLater()

        self.current_widget = widget
        self.content_stack.addWidget(widget)
        self.content_stack.setCurrentWidget(widget)

        self.statusBar().showMessage(f"Открыт раздел: {title}")

    # ------------------------------------------------------------------
    # Действия тулбара
    # ------------------------------------------------------------------

    def _on_quick_op(self, operation_type: str = "sale"):
        from .dialogs.quick_operation_dialog import QuickOperationDialog

        op_labels = {
            "sale":     "Продажа",
            "purchase": "Закупка",
            "move":     "Перемещение",
            "receipt":  "Приход",
            "writeoff": "Списание",
        }

        dialog = QuickOperationDialog(self.session, operation_type, self)
        if dialog.exec():
            label = op_labels.get(operation_type, operation_type)
            self.statusBar().showMessage(f"Операция «{label}» успешно проведена")
            if self.current_widget and hasattr(self.current_widget, "refresh_data"):
                self.current_widget.refresh_data()

    def _on_add(self):
        if self.current_widget and hasattr(self.current_widget, "add_record"):
            self.current_widget.add_record()

    def _on_edit(self):
        if self.current_widget and hasattr(self.current_widget, "edit_record"):
            self.current_widget.edit_record()

    def _on_delete(self):
        if self.current_widget and hasattr(self.current_widget, "delete_record"):
            self.current_widget.delete_record()

    def _on_refresh(self):
        if self.current_widget and hasattr(self.current_widget, "refresh_data"):
            self.current_widget.refresh_data()
            self.statusBar().showMessage("Данные обновлены")

    def _on_export(self):
        if self.current_widget and hasattr(self.current_widget, "export_to_excel"):
            self.current_widget.export_to_excel()

    def _show_about(self):
        QMessageBox.about(
            self,
            "О программе",
            "<h2>Управление автозапчастями</h2>"
            "<p>Версия 2.0</p>"
            "<p>Система учёта и управления магазином автозапчастей</p>"
            "<ul>"
            "<li>Поиск по VIN с расшифровкой через NHTSA API</li>"
            "<li>Кросс-номера и аналоги запчастей</li>"
            "<li>Складской учёт с адресным хранением</li>"
            "<li>Автоформирование заявок поставщику</li>"
            "<li>Динамика продаж, оборачиваемость запасов</li>"
            "<li>Клиентская база с историей ТС и гарантий</li>"
            "</ul>"
        )
