"""Module de logging d'urgence qui fonctionne indépendamment du reste de l'application"""
import os
import sys
import traceback
from datetime import datetime

# Définir explicitement les fonctions exportées par ce module
__all__ = ['log_error', 'log_startup_attempt', 'log_info', 'log_debug']

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "error_log.txt")

def _write_log(msg):
    """Écrire un message dans le fichier de log avec un timestamp"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            f.write(f"{timestamp} {msg}\n")
    except Exception as e:
        print(f"Failed to write to error log: {str(e)}")

def log_error(msg, exc=None):
    """Log une erreur avec détails d'exception optionnels"""
    error_msg = f"ERROR: {msg}"
    _write_log(error_msg)
    if exc:
        _write_log(f"Exception: {str(exc)}")
        _write_log(f"Type: {type(exc).__name__}")
        tb = traceback.format_exc()
        _write_log(f"Stack trace:\n{tb}")
    print(error_msg)

def log_info(msg):
    """Log un message d'information"""
    info_msg = f"INFO: {msg}"
    _write_log(info_msg)
    print(info_msg)

def log_debug(msg):
    """Log un message de débogage"""
    debug_msg = f"DEBUG: {msg}"
    _write_log(debug_msg)
    print(debug_msg)

def log_startup_attempt():
    """Log une tentative de démarrage du service"""
    _write_log("Service startup attempt")

def log_info(msg):
    """
    Log un message d'information.
    
    Args:
        msg (str): Le message à enregistrer
    """
    import datetime
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    
    # Enregistrer dans le fichier de log existant
    try:
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{timestamp} INFO: {msg}\n")
    except Exception as e:
        print(f"ERROR writing to error_log.txt: {e}")
    
    # Afficher dans la console
    print(f"{timestamp} INFO: {msg}") 