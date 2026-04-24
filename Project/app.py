"""
Управление автозапчастями
Главная точка входа в приложение
"""

import sys
from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt

from db import SessionLocal
from ui.main_window import MainWindow


def main():
    """Запуск приложения"""
    
    # Создаем приложение
    app = QApplication(sys.argv)
    
    # Настройка шрифта по умолчанию
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Название приложения
    app.setApplicationName("Управление автозапчастями")
    app.setOrganizationName("AutoParts")
    
    try:
        # Создаем сессию БД
        session = SessionLocal()
        
        # Создаем и показываем главное окно
        window = MainWindow(session)
        window.show()
        
        # Запускаем цикл обработки событий
        result = app.exec()
        
        # Закрываем сессию при выходе
        session.close()
        
        return result
        
    except Exception as e:
        QMessageBox.critical(
            None,
            "Ошибка запуска",
            f"Не удалось запустить приложение:\n\n{str(e)}\n\n"
            "Проверьте подключение к базе данных."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
