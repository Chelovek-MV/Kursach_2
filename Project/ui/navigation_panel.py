"""
Панель навигации
Дерево с разделами: Справочники, Поиск, CRM, Документы, Отчеты
"""

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class NavigationPanel(QTreeWidget):
    """Панель навигации с деревом разделов"""

    # Сигнал при выборе пункта меню (раздел, пункт)
    item_selected = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(False)

        self._setup_navigation()
        self._connect_signals()

    def _setup_navigation(self):
        """Создание структуры навигации"""

        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(11)

        # -------------------------------------------------------
        # Справочники
        # -------------------------------------------------------
        self.catalogs_section = QTreeWidgetItem(self, ["Справочники"])
        self.catalogs_section.setFont(0, header_font)
        self.catalogs_section.setExpanded(True)

        for item_id, item_name in [
            ("products",   "Товары"),
            ("brands",     "Бренды"),
            ("categories", "Категории"),
            ("suppliers",  "Поставщики"),
            ("warehouses", "Склады"),
        ]:
            item = QTreeWidgetItem(self.catalogs_section, [item_name])
            item.setData(0, 100, ("catalog", item_id))

        # -------------------------------------------------------
        # Поиск (ТР-1, ТР-2)
        # -------------------------------------------------------
        self.search_section = QTreeWidgetItem(self, ["Поиск"])
        self.search_section.setFont(0, header_font)
        self.search_section.setExpanded(True)

        for item_id, item_name in [
            ("vin_search",  "Поиск по VIN"),
            ("cross_ref",   "Кросс-номера / аналоги"),
        ]:
            item = QTreeWidgetItem(self.search_section, [item_name])
            item.setData(0, 100, ("search", item_id))

        # -------------------------------------------------------
        # CRM (ТР-5)
        # -------------------------------------------------------
        self.crm_section = QTreeWidgetItem(self, ["CRM / Клиенты"])
        self.crm_section.setFont(0, header_font)
        self.crm_section.setExpanded(True)

        for item_id, item_name in [
            ("customer_card", "Клиенты / Карточка"),
        ]:
            item = QTreeWidgetItem(self.crm_section, [item_name])
            item.setData(0, 100, ("crm", item_id))

        # -------------------------------------------------------
        # Документы
        # -------------------------------------------------------
        self.documents_section = QTreeWidgetItem(self, ["Документы"])
        self.documents_section.setFont(0, header_font)
        self.documents_section.setExpanded(True)

        for item_id, item_name in [
            ("orders",          "Заказы клиентов"),
            ("purchase_orders", "Закупки"),
            ("stocks",          "Остатки на складах"),
        ]:
            item = QTreeWidgetItem(self.documents_section, [item_name])
            item.setData(0, 100, ("document", item_id))

        # -------------------------------------------------------
        # Отчеты (ТР-3, ТР-4)
        # -------------------------------------------------------
        self.reports_section = QTreeWidgetItem(self, ["Отчеты"])
        self.reports_section.setFont(0, header_font)
        self.reports_section.setExpanded(True)

        for item_id, item_name in [
            ("stock_report",    "Остатки товаров"),
            ("sales_report",    "Продажи"),
            ("profit_report",   "Прибыльность"),
            ("movement_report", "Движение товаров"),
            ("dynamics_report", "Динамика продаж"),
            ("turnover_report", "Оборачиваемость запасов"),
        ]:
            item = QTreeWidgetItem(self.reports_section, [item_name])
            item.setData(0, 100, ("report", item_id))

    def _connect_signals(self):
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, 100)
        if data:
            section, item_id = data
            self.item_selected.emit(section, item_id)
        else:
            item.setExpanded(not item.isExpanded())

    def select_item(self, section: str, item_id: str):
        """Программный выбор элемента"""
        sections = {
            "catalog":  self.catalogs_section,
            "search":   self.search_section,
            "crm":      self.crm_section,
            "document": self.documents_section,
            "report":   self.reports_section,
        }
        parent = sections.get(section)
        if not parent:
            return
        for i in range(parent.childCount()):
            child = parent.child(i)
            data = child.data(0, 100)
            if data and data[1] == item_id:
                self.setCurrentItem(child)
                break
