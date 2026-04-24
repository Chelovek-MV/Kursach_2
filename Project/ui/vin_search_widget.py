"""
Виджет поиска по VIN-коду
ТР-1: поиск запчастей по VIN с автоматической идентификацией модели, года, комплектации
"""

import json
import urllib.request
import urllib.error
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QSplitter, QComboBox, QFormLayout,
    QDialog, QDialogButtonBox, QSpinBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

import sys
sys.path.append('..')
from models import Vehicle, Customer, VinDecodeCache, Stock, Product, Brand


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


# ---------------------------------------------------------------------------
# Фоновый поток: декодирование VIN через nhtsa.dot.gov (бесплатно, без ключа)
# ---------------------------------------------------------------------------

class VinDecodeThread(QThread):
    """Асинхронная расшифровка VIN через API NHTSA"""

    decoded = pyqtSignal(dict)   # успех: словарь с данными
    failed = pyqtSignal(str)     # ошибка: сообщение

    def __init__(self, vin: str, parent=None):
        super().__init__(parent)
        self.vin = vin.strip().upper()

    def run(self):
        try:
            url = (
                f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/"
                f"{self.vin}?format=json"
            )
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = {r["Variable"]: r["Value"] for r in data.get("Results", [])}

            decoded = {
                "vin": self.vin,
                "make": results.get("Make") or "",
                "model": results.get("Model") or "",
                "year": self._safe_int(results.get("Model Year")),
                "trim": results.get("Trim") or "",
                "engine": self._build_engine(results),
                "country": results.get("Plant Country") or "",
                "plant": results.get("Plant City") or "",
                "raw": json.dumps(results, ensure_ascii=False),
            }

            self.decoded.emit(decoded)

        except urllib.error.URLError:
            # Нет сети — делаем локальную расшифровку по WMI
            local = self._local_decode(self.vin)
            self.decoded.emit(local)
        except Exception as e:
            self.failed.emit(str(e))

    # ------------------------------------------------------------------

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _build_engine(self, r: dict) -> str:
        parts = []
        disp = r.get("Displacement (L)")
        if disp:
            parts.append(f"{disp}L")
        cylinders = r.get("Number of Cylinders")
        if cylinders:
            parts.append(f"V{cylinders}")
        fuel = r.get("Fuel Type - Primary")
        if fuel:
            parts.append(fuel)
        return " / ".join(parts)

    def _local_decode(self, vin: str) -> dict:
        """Базовая расшифровка по WMI (первые 3 символа) без сети"""
        wmi_map = {
            # Россия
            "XTA": ("LADA / ВАЗ", "RU"),
            "X7L": ("LADA Largus", "RU"),
            "XTT": ("ГАЗ", "RU"),
            "X96": ("ГАЗ", "RU"),
            "X89": ("УАЗ", "RU"),
            # Япония
            "JTD": ("Toyota", "JP"),
            "JHM": ("Honda", "JP"),
            "JN1": ("Nissan", "JP"),
            "JA3": ("Mitsubishi", "JP"),
            "JS1": ("Suzuki", "JP"),
            # Германия
            "WBA": ("BMW", "DE"),
            "WVW": ("Volkswagen", "DE"),
            "WDD": ("Mercedes-Benz", "DE"),
            "WAU": ("Audi", "DE"),
            # США
            "1HG": ("Honda", "US"),
            "1G1": ("Chevrolet", "US"),
            "2T1": ("Toyota", "US"),
            # Корея
            "KMH": ("Hyundai", "KR"),
            "KNA": ("Kia", "KR"),
        }

        # Год по 10-му символу VIN (ISO 3779)
        year_map = {
            "A": 1980, "B": 1981, "C": 1982, "D": 1983, "E": 1984,
            "F": 1985, "G": 1986, "H": 1987, "J": 1988, "K": 1989,
            "L": 1990, "M": 1991, "N": 1992, "P": 1993, "R": 1994,
            "S": 1995, "T": 1996, "V": 1997, "W": 1998, "X": 1999,
            "Y": 2000, "1": 2001, "2": 2002, "3": 2003, "4": 2004,
            "5": 2005, "6": 2006, "7": 2007, "8": 2008, "9": 2009,
            "A": 2010, "B": 2011, "C": 2012, "D": 2013, "E": 2014,
            "F": 2015, "G": 2016, "H": 2017, "J": 2018, "K": 2019,
            "L": 2020, "M": 2021, "N": 2022, "P": 2023, "R": 2024,
        }

        wmi = vin[:3].upper() if len(vin) >= 3 else ""
        make, country = wmi_map.get(wmi, ("", ""))
        year_char = vin[9].upper() if len(vin) >= 10 else ""
        year = year_map.get(year_char)

        return {
            "vin": vin,
            "make": make,
            "model": "",
            "year": year,
            "trim": "",
            "engine": "",
            "country": country,
            "plant": "",
            "raw": "{}",
        }


# ---------------------------------------------------------------------------
# Диалог привязки ТС к клиенту
# ---------------------------------------------------------------------------

class AddVehicleDialog(QDialog):
    """Диалог сохранения ТС с привязкой к клиенту"""

    def __init__(self, session, vin_data: dict, parent=None):
        super().__init__(parent)
        self.session = session
        self.vin_data = vin_data
        self.setWindowTitle("Сохранить автомобиль")
        self.setMinimumWidth(440)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Привязать ТС к клиенту")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Клиент
        self.customer_combo = QComboBox()
        self.customer_combo.addItem("-- Создать нового --", None)
        for c in self.session.query(Customer).order_by(Customer.full_name).all():
            self.customer_combo.addItem(
                f"{c.full_name or 'Без имени'} ({c.phone or '-'})", c.id
            )
        form.addRow("Клиент:", self.customer_combo)

        # VIN (нередактируемый)
        self.vin_edit = QLineEdit(self.vin_data.get("vin", ""))
        self.vin_edit.setReadOnly(True)
        form.addRow("VIN:", self.vin_edit)

        # Марка / модель / год (заполнены ав��оматически, можно скорректировать)
        self.make_edit = QLineEdit(self.vin_data.get("make", ""))
        form.addRow("Марка:", self.make_edit)

        self.model_edit = QLineEdit(self.vin_data.get("model", ""))
        form.addRow("Модель:", self.model_edit)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2100)
        self.year_spin.setValue(self.vin_data.get("year") or datetime.now().year)
        form.addRow("Год:", self.year_spin)

        self.trim_edit = QLineEdit(self.vin_data.get("trim", ""))
        form.addRow("Комплектация:", self.trim_edit)

        self.engine_edit = QLineEdit(self.vin_data.get("engine", ""))
        form.addRow("Двигатель:", self.engine_edit)

        self.plate_edit = QLineEdit()
        self.plate_edit.setPlaceholderText("например: А123БВ777")
        form.addRow("Госномер:", self.plate_edit)

        layout.addLayout(form)

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

    def _save(self):
        try:
            customer_id = self.customer_combo.currentData()

            if customer_id is None:
                # Создаём нового клиента
                new_customer = Customer(
                    full_name="Новый клиент",
                    created_at=datetime.utcnow()
                )
                self.session.add(new_customer)
                self.session.flush()
                customer_id = new_customer.id

            vehicle = Vehicle(
                customer_id=customer_id,
                vin=self.vin_edit.text().strip() or None,
                license_plate=self.plate_edit.text().strip() or None,
                brand=self.make_edit.text().strip() or None,
                model=self.model_edit.text().strip() or None,
                year=self.year_spin.value() or None,
                trim=self.trim_edit.text().strip() or None,
                engine=self.engine_edit.text().strip() or None,
            )
            self.session.add(vehicle)
            self.session.commit()
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")


# ---------------------------------------------------------------------------
# Основной виджет
# ---------------------------------------------------------------------------

class VinSearchWidget(QWidget):
    """
    Виджет поиска по VIN.
    ТР-1: поиск запчастей по артикулу/наименованию/VIN с автоматической
    идентификацией модели, года выпуска и комплектации.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._decode_thread = None
        self._current_vin_data = {}
        self._setup_ui()

    # ------------------------------------------------------------------
    # Интерфейс
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # --- Заголовок ---
        title = QLabel("Поиск по VIN-коду")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #cc0000;")
        layout.addWidget(title)

        # --- Строка ввода VIN ---
        vin_row = QHBoxLayout()

        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Введите VIN (17 символов)...")
        self.vin_input.setMaxLength(17)
        self.vin_input.setMinimumHeight(36)
        font_input = QFont()
        font_input.setPointSize(13)
        font_input.setFamily("Courier New")
        self.vin_input.setFont(font_input)
        self.vin_input.returnPressed.connect(self._on_decode)
        vin_row.addWidget(self.vin_input, 1)

        self.btn_decode = QPushButton("Расшифровать VIN")
        self.btn_decode.setMinimumHeight(36)
        self.btn_decode.setProperty("cssClass", "action")
        self.btn_decode.clicked.connect(self._on_decode)
        vin_row.addWidget(self.btn_decode)

        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setMinimumHeight(36)
        self.btn_clear.clicked.connect(self._clear)
        vin_row.addWidget(self.btn_clear)

        layout.addLayout(vin_row)

        # --- Счётчик символов ---
        self.vin_len_label = QLabel("0 / 17 символов")
        self.vin_len_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.vin_input.textChanged.connect(self._update_vin_counter)
        layout.addWidget(self.vin_len_label)

        # --- Блок результатов расшифровки ---
        self.decode_group = QGroupBox("Данные автомобиля")
        decode_layout = QFormLayout(self.decode_group)
        decode_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def _make_val_label():
            lbl = QLabel("—")
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            return lbl

        self.lbl_make = _make_val_label()
        self.lbl_model = _make_val_label()
        self.lbl_year = _make_val_label()
        self.lbl_trim = _make_val_label()
        self.lbl_engine = _make_val_label()
        self.lbl_country = _make_val_label()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #888888; font-size: 11px;")

        decode_layout.addRow("Марка:", self.lbl_make)
        decode_layout.addRow("Модель:", self.lbl_model)
        decode_layout.addRow("Год выпуска:", self.lbl_year)
        decode_layout.addRow("Комплектация:", self.lbl_trim)
        decode_layout.addRow("Двигатель:", self.lbl_engine)
        decode_layout.addRow("Страна:", self.lbl_country)
        decode_layout.addRow("", self.lbl_status)

        # Кнопки для работы с ТС
        btn_row = QHBoxLayout()
        self.btn_save_vehicle = QPushButton("Сохранить ТС / привязать к клиенту")
        self.btn_save_vehicle.setEnabled(False)
        self.btn_save_vehicle.setProperty("cssClass", "success")
        self.btn_save_vehicle.clicked.connect(self._save_vehicle)
        btn_row.addWidget(self.btn_save_vehicle)
        btn_row.addStretch()
        decode_layout.addRow("", btn_row)

        self.decode_group.setVisible(False)
        layout.addWidget(self.decode_group)

        # --- Разделитель ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #cccccc;")
        layout.addWidget(sep)

        # --- Поиск подходящих запчастей ---
        parts_label = QLabel("Подходящие запчасти на складе")
        font2 = QFont()
        font2.setPointSize(13)
        font2.setBold(True)
        parts_label.setFont(font2)
        layout.addWidget(parts_label)

        # Строка поиска запчастей (артикул / наименование)
        parts_search_row = QHBoxLayout()

        self.parts_search = QLineEdit()
        self.parts_search.setPlaceholderText("Дополнительно: поиск по артикулу или наименованию...")
        self.parts_search.returnPressed.connect(self._search_parts)
        parts_search_row.addWidget(self.parts_search, 1)

        self.btn_search_parts = QPushButton("Найти запчасти")
        self.btn_search_parts.clicked.connect(self._search_parts)
        parts_search_row.addWidget(self.btn_search_parts)

        layout.addLayout(parts_search_row)

        # Таблица запчастей
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(6)
        self.parts_table.setHorizontalHeaderLabels([
            "Артикул", "Наименование", "Бренд", "Склад", "Ячейка", "Остаток"
        ])
        self.parts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.parts_table.setAlternatingRowColors(True)
        self.parts_table.setSortingEnabled(True)
        hdr = self.parts_table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.parts_table, 1)

        self.parts_count_label = QLabel("Результатов: 0")
        self.parts_count_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(self.parts_count_label)

        # --- ТС с этим VIN в базе системы ---
        hist_header_row = QHBoxLayout()
        hist_label = QLabel("ТС с этим VIN в базе системы")
        font3 = QFont()
        font3.setPointSize(12)
        font3.setBold(True)
        hist_label.setFont(font3)
        hist_header_row.addWidget(hist_label)
        hist_header_row.addStretch()

        self.btn_edit_vehicle = QPushButton("Редактировать ТС")
        self.btn_edit_vehicle.setEnabled(False)
        self.btn_edit_vehicle.clicked.connect(self._edit_selected_vehicle)
        hist_header_row.addWidget(self.btn_edit_vehicle)

        layout.addLayout(hist_header_row)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Клиент", "Телефон", "Госномер", "Год", "Комплектация", "Двигатель"
        ])
        self.history_table.setMaximumHeight(160)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.itemSelectionChanged.connect(self._on_history_selected)
        hdr2 = self.history_table.horizontalHeader()
        hdr2.setStretchLastSection(True)
        layout.addWidget(self.history_table)

    # ------------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------------

    def _update_vin_counter(self, text: str):
        n = len(text)
        self.vin_len_label.setText(f"{n} / 17 символов")
        color = "#28a745" if n == 17 else ("#cc0000" if n > 17 else "#888888")
        self.vin_len_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _on_decode(self):
        vin = self.vin_input.text().strip().upper()
        if len(vin) != 17:
            QMessageBox.warning(self, "Ошибка", "VIN должен содержать ровно 17 символов.")
            return

        # Проверяем кеш
        cached = self.session.query(VinDecodeCache).filter_by(vin=vin).first()
        if cached:
            self._apply_decode_result({
                "vin": cached.vin,
                "make": cached.make or "",
                "model": cached.model or "",
                "year": cached.year,
                "trim": cached.trim or "",
                "engine": cached.engine or "",
                "country": cached.country or "",
                "plant": cached.plant or "",
                "raw": cached.raw_data or "{}",
            }, from_cache=True)
            return

        self.btn_decode.setEnabled(False)
        self.btn_decode.setText("Расшифровка...")
        self.lbl_status.setText("Запрос к API NHTSA...")

        self._decode_thread = VinDecodeThread(vin)
        self._decode_thread.decoded.connect(self._on_decoded)
        self._decode_thread.failed.connect(self._on_decode_failed)
        self._decode_thread.start()

    def _on_decoded(self, data: dict):
        self.btn_decode.setEnabled(True)
        self.btn_decode.setText("Расшифровать VIN")

        # Сохраняем в кеш
        try:
            existing = self.session.query(VinDecodeCache).filter_by(vin=data["vin"]).first()
            if not existing:
                cache_entry = VinDecodeCache(
                    vin=data["vin"],
                    make=data.get("make"),
                    model=data.get("model"),
                    year=data.get("year"),
                    trim=data.get("trim"),
                    engine=data.get("engine"),
                    country=data.get("country"),
                    plant=data.get("plant"),
                    raw_data=data.get("raw"),
                    decoded_at=datetime.utcnow(),
                )
                self.session.add(cache_entry)
                self.session.commit()
        except Exception:
            self.session.rollback()

        self._apply_decode_result(data, from_cache=False)

    def _on_decode_failed(self, error_msg: str):
        self.btn_decode.setEnabled(True)
        self.btn_decode.setText("Расшифровать VIN")

        # API недоступен — показываем локальную расшифровку и данные из БД
        vin = self.vin_input.text().strip().upper()
        local = VinDecodeThread(vin)._local_decode(vin)
        local["_api_error"] = error_msg
        self._apply_decode_result(local, from_cache=False)

    def _apply_decode_result(self, data: dict, from_cache: bool = False):
        vin = data.get("vin", "")

        # 1. Если марка пустая — пробуем взять из таблицы Vehicle (уже сохранённые ТС)
        if not data.get("make"):
            vehicle_in_db = (
                self.session.query(Vehicle)
                .filter(Vehicle.vin == vin)
                .first()
            )
            if vehicle_in_db:
                if vehicle_in_db.brand:
                    data["make"] = vehicle_in_db.brand
                if vehicle_in_db.model and not data.get("model"):
                    data["model"] = vehicle_in_db.model
                if vehicle_in_db.year and not data.get("year"):
                    data["year"] = vehicle_in_db.year
                if vehicle_in_db.trim and not data.get("trim"):
                    data["trim"] = vehicle_in_db.trim
                if vehicle_in_db.engine and not data.get("engine"):
                    data["engine"] = vehicle_in_db.engine

        # 2. Если марка всё ещё пустая — WMI-расшифровка по первым 3 символам
        if not data.get("make"):
            local = VinDecodeThread(vin)._local_decode(vin)
            for key in ("make", "country"):
                if not data.get(key) and local.get(key):
                    data[key] = local[key]
            if not data.get("year") and local.get("year"):
                data["year"] = local["year"]

        self._current_vin_data = data

        make = data.get("make") or ""
        model = data.get("model") or ""
        year = data.get("year")
        trim = data.get("trim") or ""
        engine = data.get("engine") or ""
        country = data.get("country") or ""
        api_error = data.get("_api_error")

        self.lbl_make.setText(make or "—")
        self.lbl_model.setText(model or "—")
        self.lbl_year.setText(str(year) if year else "—")
        self.lbl_trim.setText(trim or "—")
        self.lbl_engine.setText(engine or "—")
        self.lbl_country.setText(country or "—")

        # Источник расшифровки
        if from_cache:
            source_text = "из кеша VIN"
            color = "#888888"
        elif api_error:
            source_text = f"нет связи с API, данные из базы / WMI"
            color = "#e67e22"
        elif not make and not model:
            source_text = "частичная (только WMI-код)"
            color = "#e67e22"
        else:
            source_text = "API NHTSA"
            color = "#28a745"

        self.lbl_status.setText(f"VIN: {vin}  |  источник: {source_text}")
        self.lbl_status.setStyleSheet(f"color: {color}; font-size: 11px;")

        # Показываем блок данных
        self.decode_group.setVisible(True)
        self.btn_save_vehicle.setEnabled(True)

        # Показать ТС с таким VIN в базе
        self._load_vin_history(data["vin"])

        # Автопоиск запчастей по марке/модели
        if data.get("make"):
            self.parts_search.setText(data.get("model") or data.get("make") or "")
            self._search_parts()

    def _load_vin_history(self, vin: str):
        """Загрузить из БД ТС с данным VIN"""
        vehicles = self.session.query(Vehicle).filter_by(vin=vin).all()
        self.history_table.setRowCount(len(vehicles))
        for row, v in enumerate(vehicles):
            customer = v.customer
            items = [
                customer.full_name if customer else "—",
                customer.phone if customer else "—",
                v.license_plate or "—",
                str(v.year) if v.year else "—",
                v.trim or "—",
                v.engine or "—",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                # Сохраняем vehicle_id в каждой ячейке для последующего редактирования
                item.setData(Qt.ItemDataRole.UserRole, v.id)
                self.history_table.setItem(row, col, item)

        self.history_table.resizeColumnsToContents()
        self.btn_edit_vehicle.setEnabled(False)

    def _on_history_selected(self):
        has = bool(self.history_table.selectedItems())
        self.btn_edit_vehicle.setEnabled(has)

    def _edit_selected_vehicle(self):
        """Открыть диалог редактирования выбранного ТС"""
        row = self.history_table.currentRow()
        if row < 0:
            return
        item = self.history_table.item(row, 0)
        if not item:
            return
        vehicle_id = item.data(Qt.ItemDataRole.UserRole)
        vehicle = self.session.get(Vehicle, vehicle_id)
        if not vehicle:
            return

        from .customer_card_widget import _VehicleEditDialog
        dlg = _VehicleEditDialog(self.session, vehicle.customer_id, vehicle, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(vehicle)
            self._load_vin_history(self._current_vin_data.get("vin", ""))
            QMessageBox.information(self, "Сохранено", "Данные автомобиля обновлены.")

    def _search_parts(self):
        """Поиск запчастей на складе по артикулу/наименованию"""
        query_text = self.parts_search.text().strip()

        q = (
            self.session.query(
                Product.articul,
                Product.name,
                Brand.name.label("brand_name"),
                Stock.quantity,
                Stock.cell_address,
            )
            .join(Brand, Brand.id == Product.brand_id)
            .join(Stock, Stock.product_id == Product.id)
            .filter(Stock.quantity > 0)
        )

        if query_text:
            q = q.filter(
                Product.articul.ilike(f"%{query_text}%")
                | Product.name.ilike(f"%{query_text}%")
            )

        results = q.order_by(Stock.quantity.desc()).limit(200).all()

        self.parts_table.setRowCount(len(results))
        for row, r in enumerate(results):
            self.parts_table.setItem(row, 0, QTableWidgetItem(r.articul or ""))
            self.parts_table.setItem(row, 1, QTableWidgetItem(r.name or ""))
            self.parts_table.setItem(row, 2, QTableWidgetItem(r.brand_name or ""))
            self.parts_table.setItem(row, 3, QTableWidgetItem(""))
            self.parts_table.setItem(row, 4, QTableWidgetItem(r.cell_address or ""))
            qty = int(r.quantity) if r.quantity is not None else 0
            qty_item = _NumericItem(str(qty), qty)
            self.parts_table.setItem(row, 5, qty_item)

        self.parts_table.resizeColumnsToContents()
        self.parts_count_label.setText(f"Результатов: {len(results)}")

    def _save_vehicle(self):
        if not self._current_vin_data:
            return
        dlg = AddVehicleDialog(self.session, self._current_vin_data, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_vin_history(self._current_vin_data.get("vin", ""))
            QMessageBox.information(self, "Сохранено", "Автомобиль сохранён и привязан к клиенту.")

    def _clear(self):
        self.vin_input.clear()
        self._current_vin_data = {}
        for lbl in (self.lbl_make, self.lbl_model, self.lbl_year,
                    self.lbl_trim, self.lbl_engine, self.lbl_country):
            lbl.setText("—")
        self.lbl_status.setText("")
        self.btn_save_vehicle.setEnabled(False)
        self.decode_group.setVisible(False)
        self.parts_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.parts_count_label.setText("Результатов: 0")
        self.parts_search.clear()

    def refresh_data(self):
        pass
