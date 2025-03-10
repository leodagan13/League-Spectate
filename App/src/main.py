# main.py
import sys
import os

# Ajouter le répertoire courant au PYTHONPATH pour garantir que emergency_log est trouvé
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import le module emergency_log avant tout autre import pour s'assurer qu'il est disponible
try:
    from emergency_log import log_error, log_startup_attempt
    # Log le démarrage de l'application
    log_startup_attempt()
except ImportError as e:
    print(f"WARNING: emergency_log module not available: {e}")
    def log_error(msg, exc=None):
        print(f"ERROR: {msg}")
        if exc:
            print(f"Exception: {str(exc)}")

# Import standard
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from service import Service
from config import Config

def main():
    try:
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
        return app.exec()
    except Exception as e:
        # Log toute erreur non capturée
        log_error("Unhandled exception in main", e)
        # Afficher un message d'erreur
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Critical Error",
            f"An unhandled error occurred:\n\n{str(e)}\n\nSee error_log.txt for details."
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())