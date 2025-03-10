# main.py
import sys
import os
import traceback

# Ajouter le répertoire courant au PYTHONPATH pour garantir que emergency_log est trouvé
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import le module emergency_log avant tout autre import pour s'assurer qu'il est disponible
try:
    from emergency_log import log_error, log_startup_attempt, log_info, log_debug
    # Log le démarrage de l'application
    log_startup_attempt()
except ImportError as e:
    print(f"WARNING: emergency_log module not available: {e}")
    def log_error(msg, exc=None):
        print(f"ERROR: {msg}")
        if exc:
            print(f"Exception: {str(exc)}")
            traceback.print_exc()
    
    def log_info(msg):
        print(f"INFO: {msg}")
        
    def log_debug(msg):
        print(f"DEBUG: {msg}")

# Import standard
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    from ui.main_window import MainWindow
    from service import Service
    from config import Config
except ImportError as e:
    log_error(f"Failed to import required modules", e)
    sys.exit(1)

def main():
    app = None
    service = None
    try:
        log_info("Application starting")
        
        # Initialize app
        app = QApplication(sys.argv)
        
        # Handler pour fermer proprement l'application
        def clean_shutdown():
            nonlocal service
            if service:
                log_info("Performing clean shutdown...")
                try:
                    # Arrêter proprement les threads et services
                    service.shutdown()
                except Exception as e:
                    log_error("Error during shutdown", e)
            log_info("Application shutdown complete")
        
        # Connecter au signal aboutToQuit de l'application
        app.aboutToQuit.connect(clean_shutdown)
        
        # Load config
        log_info("Loading configuration")
        config = Config()
        
        # Initialize service
        log_info("Initializing service")
        try:
            service = Service(config)
        except Exception as service_error:
            log_error("Failed to initialize service", service_error)
            raise
        
        # Create main window
        log_info("Creating main window")
        try:
            window = MainWindow(config, service)
            window.show()
        except Exception as window_error:
            log_error("Failed to create or show main window", window_error)
            raise
        
        log_info("Application started successfully")
        
        # Run the application
        return app.exec()
    except Exception as e:
        # Log toute erreur non capturée
        log_error("Unhandled exception in main", e)
        # Afficher un message d'erreur
        try:
            if app is not None:
                QMessageBox.critical(
                    None,
                    "Critical Error",
                    f"An unhandled error occurred:\n\n{str(e)}\n\nSee error_log.txt for details."
                )
        except Exception as dialog_error:
            log_error("Failed to show error dialog", dialog_error)
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        log_info(f"Application exiting with code {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        log_error("Fatal error outside main function", e)
        sys.exit(2)