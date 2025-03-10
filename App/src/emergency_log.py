"""Module de logging d'urgence qui fonctionne indépendamment du reste de l'application"""
import os
import sys
import traceback
from datetime import datetime

# Définir explicitement les fonctions exportées par ce module
__all__ = ['log_error', 'log_startup_attempt']

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "error_log.txt")

def log_error(message, exception=None):
    """Log une erreur dans le fichier de log et la console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Construire le message complet
    full_message = f"[{timestamp}] ERROR: {message}"
    
    # Ajouter des détails de l'exception si fournie
    if exception:
        full_message += f"\nException: {str(exception)}"
        full_message += f"\nType: {type(exception).__name__}"
        full_message += f"\nStack trace:\n{''.join(traceback.format_tb(exception.__traceback__))}"
    
    # Écrire dans la console
    print(full_message, file=sys.stderr)
    
    # Écrire dans le fichier
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(full_message + "\n\n")
    except Exception as e:
        print(f"Impossible d'écrire dans le fichier de log: {str(e)}", file=sys.stderr)

def log_startup_attempt():
    """Log une tentative de démarrage du service"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}] Service startup attempt"
    
    # Écrire dans la console
    print(message)
    
    # Écrire dans le fichier
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        print(f"Impossible d'écrire dans le fichier de log: {str(e)}", file=sys.stderr) 