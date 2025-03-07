# main.py
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from service import Service
from config import Config

def main():
    # Initialize app
    app = QApplication(sys.argv)
    
    # Load config
    config = Config()
    
    # Initialize service
    service = Service(config)
    
    # Create main window
    window = MainWindow(config, service)
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()