# service.py
import requests as r
import urllib3
import subprocess
import psutil
import time
import traceback
from obswebsocket import obsws, requests
from datetime import datetime
import asyncio
import sys
from typing import Optional, Tuple, Callable
from config import PlayerConfig, Config
import os
from PySide6.QtCore import QThread, Signal, QObject, QTimer, Qt, Slot
from league import LeagueAPI
from PySide6.QtWidgets import QMessageBox
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller, KeyCode, Key
from obs_manager import OBSManager

# Ajouter le répertoire courant au PYTHONPATH pour garantir que emergency_log est trouvé
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

keyboard = Controller()

class Service(QObject):
    # Variable de classe (statique) pour suivre l'état global
    _any_service_running = False

    # Définir des signaux pour la communication entre threads
    log_signal = Signal(str, str)

    def __init__(self, config: 'Config'):
        super().__init__()  # Initialiser la classe parent QObject
        
        # Importer le module emergency_log ici pour éviter des problèmes d'import circulaire
        try:
            from emergency_log import log_error, log_startup_attempt, log_info
            self._emergency_log = log_error
            self._log_startup = log_startup_attempt
            self._log_info = log_info
        except ImportError as e:
            # Fallback si le module n'est pas disponible
            print(f"ERROR: Could not import emergency_log in Service: {e}")
            def log_error(msg, exc=None):
                print(f"EMERGENCY: {msg}")
                if exc:
                    print(f"Exception: {str(exc)}")
            self._emergency_log = log_error
            self._log_startup = lambda: print("Service startup attempt")
            self._log_info = lambda msg: print(f"INFO: {msg}")
        
        try:
            self.config = config
            self.running = False
            self.isStreaming = False
            self.log_callback = None
            self.game_checker = None
            self.active_stream = None
            self.obs_manager = None
            
            # Configurer le signal de log pour une exécution thread-safe
            self.log_signal.connect(self._log_internal, Qt.QueuedConnection)
                
        except Exception as e:
            self._emergency_log("Error during Service initialization", e)

    def start(self):
        """Start the service"""
        # Ajouter un log pour tracer l'origine de l'appel
        import traceback
        call_stack = traceback.format_stack()
        self.log(f"Service.start() called from:\n{''.join(call_stack[:-1])}", "DEBUG")
        
        # Vérification globale pour empêcher plusieurs services de démarrer
        if Service._any_service_running:
            self.log("Another service instance is already running, ignoring start request", "WARNING")
            return True
            
        # Log la tentative de démarrage avec le système d'urgence
        try:
            # Vérifie si le service est déjà en cours d'exécution pour éviter les démarrages multiples
            if self.running:
                self.log("Service already running, ignoring start request", "WARNING")
                return True
            self._log_startup()
        except:
            pass
            
        try:
            self.log("-" * 50, "INFO")
            self.log("Starting service...", "INFO")
            
            # Initialement, marquer le service comme démarré
            self.running = True
            # Marquer qu'un service est en cours d'exécution globalement
            Service._any_service_running = True
            
            # Initialize OBS manager
            try:
                self.log("Initializing OBS manager", "INFO")
                self.obs_manager = OBSManager(
                    obs_path=self.config.obs_path,
                    obs_host=self.config.obs_host,
                    obs_port=self.config.obs_port,
                    obs_password=self.config.obs_password,
                    log_callback=self.log
                )
                self.log("OBS Manager initialized successfully", "SUCCESS")
            except Exception as obs_e:
                self.log(f"Warning: Failed to initialize OBS manager: {str(obs_e)}", "WARNING")
                # Continue despite error
            
            # Start game checker thread with enhanced protection
            self.log("Starting game checker thread...", "INFO")
            
            try:
                # Vérifier si un thread existe déjà et s'il est en cours d'exécution
                if self.game_checker and self.game_checker.isRunning():
                    self.log("Game checker thread already running", "WARNING")
                else:
                    # Create the thread with safety checks
                    self.game_checker = SafeGameCheckerThread(self)
                    
                    # Connect signals with protection
                    try:
                        self.game_checker.show_error.connect(self.show_error)
                    except Exception as sig_e:
                        self.log(f"Error connecting signals: {str(sig_e)}", "WARNING")
                    
                    # Start the thread safely
                    self.game_checker.start()
                    self.log("Game checker thread started successfully", "SUCCESS")
                    
            except Exception as e:
                self._emergency_log("Failed to start game checker thread", e)
                self.log(f"Error starting game checker thread: {str(e)}", "ERROR")
                # Service remains active, but thread couldn't start
            
            self.log("Service started", "SUCCESS")
            self.log("-" * 50, "INFO")
            
            return True
            
        except Exception as e:
            self._emergency_log("Unexpected error starting service", e)
            self.log(f"Unexpected error starting service: {str(e)}", "ERROR")
            self.running = False
            Service._any_service_running = False  # Libérer le verrou global
            return False

    def stop(self):
        """Stop the service"""
        if not self.running:
            return
            
        self.running = False
        Service._any_service_running = False  # Libérer le verrou global
        self.log("Service stopping...", "INFO")
        
        # Stop game checker thread
        if self.game_checker:
            try:
                self.game_checker.running = False  # Signal thread to stop
                self.game_checker.wait(1000)  # Wait up to 1 second
                self.game_checker = None
                self.log("Game checker thread stopped", "INFO")
            except Exception as e:
                self.log(f"Error stopping game checker: {str(e)}", "ERROR")
            
        # Disconnect from OBS
        if self.obs_manager:
            try:
                self.obs_manager.disconnect()
                self.log("Disconnected from OBS", "INFO")
            except Exception as e:
                self.log(f"Error disconnecting from OBS: {str(e)}", "ERROR")
            
        # Stop streaming if active
        if self.isStreaming:
            try:
                self.stop_streaming()
                self.log("Streaming stopped", "INFO")
            except Exception as e:
                self.log(f"Error stopping streaming: {str(e)}", "ERROR")
            self.active_stream = None
            
        self.log("Service stopped", "SUCCESS")

    def get_league_locale(self, league_path):
        """Get locale from League client settings"""
        try:
            config_dir = os.path.join(os.path.dirname(league_path), "Config")
            config_file = os.path.join(config_dir, "LeagueClientSettings.yaml")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for line in content.splitlines():
                        if "locale:" in line.lower():
                            try:
                                locale = line.split(':', 1)[1].strip().strip('"\'')
                                self.log(f"Found locale in config: {locale}", "INFO")
                                return locale
                            except:
                                pass
            
            self.log("Using default locale: en_US", "INFO")
            return "en_US"
        except Exception as e:
            self.log(f"Error getting locale: {str(e)}", "WARNING")
            return "en_US"

    def start_streaming(self, player_name: str, player_config: 'PlayerConfig'):
        """Start streaming for a specific player - fully functional version"""
        try:
            self.log(f"[STREAM-001] Starting streaming for {player_name}", "INFO")
            
            # Input validation
            if not player_name:
                self.log("[STREAM-002] Player name is empty or invalid", "ERROR")
                return False
                
            if not player_config:
                self.log(f"[STREAM-003] Player config for {player_name} is invalid or missing", "ERROR")
                return False
            
            # Already streaming check
            if self.isStreaming:
                self.log(f"[STREAM-004] Already streaming for {self.active_stream[0] if self.active_stream else 'unknown'}, ignoring request", "WARNING")
                return False
            
            # Get stream key and channel name
            stream_key = getattr(player_config, 'stream_key', '')
            channel_name = getattr(player_config, 'channel_name', 'unknown')
            
            if not stream_key:
                self.log(f"[STREAM-ERR] No stream key configured for {player_name}", "ERROR")
                return False
            
            # Configure OBS for streaming
            if self.obs_manager:
                try:
                    # Configure OBS with stream key
                    self.log(f"[STREAM-OBS1] Configuring OBS for streaming", "INFO")
                    self.obs_manager.set_stream_key(stream_key)
                    
                    # Start streaming in OBS
                    self.log(f"[STREAM-OBS2] Starting OBS streaming", "INFO")
                    self.obs_manager.start_streaming()
                    
                    self.log(f"[STREAM-OBS3] OBS streaming started successfully", "SUCCESS")
                except Exception as e:
                    self.log(f"[STREAM-ERR] Failed to configure OBS: {str(e)}", "ERROR")
                    return False
            else:
                self.log(f"[STREAM-WARN] OBS manager not available, streaming will be simulated", "WARNING")
            
            # Mark as streaming and set active stream
            self.isStreaming = True
            self.active_stream = (player_name, channel_name)
            
            # Log success
            self.log(f"[STREAM-009] Successfully started streaming for {player_name} on {channel_name}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"[STREAM-ERR] Error in start_streaming: {str(e)}", "ERROR")
            import traceback
            self.log(f"[STREAM-TRACE] {traceback.format_exc()}", "ERROR")
            return False

    def stop_streaming(self):
        """Stop streaming"""
        try:
            if not self.isStreaming:
                self.log("[STOPSTREAM-001] No active stream to stop", "INFO")
                return True
                
            # Get active stream info for logging
            stream_info = "unknown"
            if self.active_stream:
                try:
                    player_name, channel_name = self.active_stream
                    stream_info = f"{player_name} on {channel_name}"
                except:
                    pass
                
            self.log(f"[STOPSTREAM-002] Stopping stream for {stream_info}", "INFO")
            
            # Reset streaming state
            try:
                old_state = self.isStreaming
                old_stream = self.active_stream
                
                self.isStreaming = False
                self.active_stream = None
                
                self.log(f"[STOPSTREAM-003] Streaming state reset from {old_state} to {self.isStreaming}", "DEBUG")
            except Exception as e:
                self.log(f"[STOPSTREAM-ERR1] Error resetting streaming state: {str(e)}", "ERROR")
                
            # Kill any League process if running
            try:
                self.log("[STOPSTREAM-004] Attempting to kill League game process", "INFO")
                self.kill_league_game()
                self.log("[STOPSTREAM-005] League game process killed successfully", "SUCCESS")
            except Exception as e:
                self.log(f"[STOPSTREAM-ERR2] Error killing League game: {str(e)}", "ERROR")
                import traceback
                self.log(f"[STOPSTREAM-TRACE] {traceback.format_exc()}", "ERROR")
                
            self.log("[STOPSTREAM-006] Stream stopped successfully", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"[STOPSTREAM-CRIT] Critical error in stop_streaming: {str(e)}", "ERROR")
            import traceback
            self.log(f"[STOPSTREAM-TRACE] {traceback.format_exc()}", "ERROR")
            return False

    def kill_league_game(self):
        """Kill the League game process"""
        try:
            self.log("[KILL-001] Attempting to kill League game process", "INFO")
            
            found = False
            killed = False
            
            try:
                for proc in psutil.process_iter():
                    try:
                        if proc.name() == "League of Legends.exe":
                            found = True
                            self.log(f"[KILL-002] Found League process, PID: {proc.pid}", "INFO")
                            proc.kill()
                            killed = True
                            self.log(f"[KILL-003] Successfully killed League process {proc.pid}", "SUCCESS")
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        self.log(f"[KILL-ERR1] Access error for process: {str(e)}", "WARNING")
                        continue
                        
                if not found:
                    self.log("[KILL-004] No League of Legends.exe process found", "INFO")
                    
                if found and not killed:
                    self.log("[KILL-005] Found League process but failed to kill it", "WARNING")
                    
                return killed
                    
            except Exception as e:
                self.log(f"[KILL-ERR2] Error iterating processes: {str(e)}", "ERROR")
                import traceback
                self.log(f"[KILL-TRACE1] {traceback.format_exc()}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"[KILL-CRIT] Critical error killing spectator client: {str(e)}", "ERROR")
            import traceback
            self.log(f"[KILL-TRACE2] {traceback.format_exc()}", "ERROR")
            return False

    def is_player_streaming(self, player_name: str) -> bool:
        """Check if player is being streamed"""
        try:
            if not player_name:
                self.log("[PLAYERSTREAM-001] Empty player name provided", "WARNING")
                return False
            
            if not hasattr(self, 'isStreaming') or not hasattr(self, 'active_stream'):
                self.log("[PLAYERSTREAM-002] Service streaming attributes not initialized", "ERROR")
                return False
                
            if not self.isStreaming:
                self.log(f"[PLAYERSTREAM-003] No active streaming (for {player_name})", "DEBUG")
                return False
                
            if not self.active_stream:
                self.log("[PLAYERSTREAM-004] Streaming flag is true but no active_stream data", "WARNING")
                return False
            
            try:
                streamed_player, channel = self.active_stream
                is_streaming = streamed_player == player_name
                self.log(f"[PLAYERSTREAM-005] Check: {player_name} vs {streamed_player} = {is_streaming}", "DEBUG")
                return is_streaming
            except ValueError as e:
                self.log(f"[PLAYERSTREAM-006] Invalid active_stream format: {self.active_stream}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"[PLAYERSTREAM-ERR] Error in is_player_streaming: {str(e)}", "ERROR")
            import traceback
            self.log(f"[PLAYERSTREAM-TRACE] {traceback.format_exc()}", "ERROR")
            return False

    def log(self, message, level="INFO"):
        """Thread-safe logging function"""
        # Au lieu d'appeler directement _log_internal, émettre un signal
        self.log_signal.emit(message, level)
    
    @Slot(str, str)
    def _log_internal(self, message, level):
        """Actual logging implementation that will run in the GUI thread"""
        # La même implémentation que votre méthode log actuelle
        try:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            formatted_msg = f"[{level}] {message}"
            
            if level == "ERROR":
                print(f"{timestamp} \033[91m{formatted_msg}\033[0m")  # Red
                self._emergency_log(message)
            elif level == "WARNING":
                print(f"{timestamp} \033[93m{formatted_msg}\033[0m")  # Yellow
            elif level == "SUCCESS":
                print(f"{timestamp} \033[92m{formatted_msg}\033[0m")  # Green
            elif level == "DEBUG":
                print(f"{timestamp} \033[94m{formatted_msg}\033[0m")  # Blue
            else:
                print(f"{timestamp} {formatted_msg}")
                
            # Ajouter au log de la console UI si disponible
            if hasattr(self, 'console') and self.console is not None:
                self.console.append_log(message, level)
                
        except Exception as e:
            print(f"Error in logging: {str(e)}")

    def set_log_callback(self, callback):
        """Set the callback function for logging"""
        self.log_callback = callback

    def show_error(self, title: str, message: str):
        """Show an error message to the user"""
        QMessageBox.warning(None, title, message)

    def is_obs_running(self) -> bool:
        """Check if OBS is running"""
        if not self.obs_manager:
            return False
            
        try:
            return self.obs_manager.is_obs_running()
        except Exception as e:
            self.log(f"Error checking if OBS is running: {str(e)}", "ERROR")
            return False

    def launch_obs(self):
        """Launch OBS"""
        if not self.obs_manager:
            self.log("OBS manager not initialized", "ERROR")
            return
            
        try:
            self.obs_manager.launch_obs()
        except Exception as e:
            self.log(f"Error launching OBS: {str(e)}", "ERROR")

    def connect_obs(self):
        """Connect to OBS websocket"""
        if not self.obs_manager:
            self.log("OBS manager not initialized", "ERROR")
            return
            
        try:
            self.obs_manager.connect()
        except Exception as e:
            self.log(f"Error connecting to OBS: {str(e)}", "ERROR")

    def is_league_game_running(self) -> bool:
        """Check if League game process is running"""
        try:
            return "League of Legends.exe" in (p.name() for p in psutil.process_iter())
        except Exception as e:
            self.log(f"Error checking if League game is running: {str(e)}", "ERROR")
            return False

    def launch_spectate_client(self, spectate_cmd):
        """Tente de lancer le client spectateur de League of Legends avec une approche simplifiée"""
        
        try:
            self.log(f"Attempting to launch League with command: {spectate_cmd}", "INFO")
            
            # Vérifications de base
            if not spectate_cmd or not isinstance(spectate_cmd, list) or len(spectate_cmd) < 2:
                self.log(f"Invalid spectate command: {spectate_cmd}", "ERROR")
                return False
            
            exe_path = spectate_cmd[0]
            args = spectate_cmd[1]
            
            if not os.path.exists(exe_path):
                self.log(f"Executable not found: {exe_path}", "ERROR")
                return False
            
            # Obtenir le répertoire de travail (dossier contenant l'exécutable)
            work_dir = os.path.dirname(exe_path)
            self.log(f"Working directory: {work_dir}", "DEBUG")
            
            # MÉTHODE DIRECTE: Utiliser subprocess.Popen avec les arguments sous forme de liste
            try:
                self.log("Launching game using direct subprocess method", "INFO")
                # Construire la commande complète en une seule liste
                cmd_list = [exe_path, args]
                
                self.log(f"Command list: {cmd_list}", "DEBUG")
                
                # Lancer le processus avec un shell=False pour plus de sécurité
                process = subprocess.Popen(
                    cmd_list,
                    cwd=work_dir,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Vérifier si le processus s'est lancé correctement
                self.log(f"Process launched with PID: {process.pid}", "SUCCESS")
                
                # Attendre un court instant pour voir si le processus survit
                time.sleep(1)
                
                # Vérifier si le processus est toujours en cours d'exécution
                if process.poll() is None:
                    self.log("Process is still running after 1 second", "SUCCESS")
                    return True
                else:
                    return_code = process.poll()
                    stdout, stderr = process.communicate()
                    self.log(f"Process exited immediately with code: {return_code}", "ERROR")
                    self.log(f"STDOUT: {stdout.decode('utf-8', errors='ignore')}", "DEBUG")
                    self.log(f"STDERR: {stderr.decode('utf-8', errors='ignore')}", "DEBUG")
                    return False
                    
            except Exception as e:
                self.log(f"Exception in direct subprocess method: {e}", "ERROR")
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
                
            # Si nous arrivons ici, toutes les méthodes ont échoué
            self.log("All launch methods failed", "ERROR")
            return False
            
        except Exception as e:
            self.log(f"Fatal error in launch_spectate_client: {e}", "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False

    def launch_spectate_client_alternative(self, spectate_cmd):
        """Méthode alternative pour lancer le spectateur LoL"""
        try:
            # Vérifications de base
            if not spectate_cmd or not isinstance(spectate_cmd, list) or len(spectate_cmd) < 2:
                self.log(f"Invalid spectate command: {spectate_cmd}", "ERROR")
                return False
            
            exe_path = spectate_cmd[0]
            args = spectate_cmd[1]
            work_dir = os.path.dirname(exe_path)
            
            # Méthode 1: Utiliser os.startfile (Windows uniquement)
            if sys.platform == 'win32':
                self.log("Trying to start game with os.startfile", "INFO")
                # Créer un fichier batch temporaire
                batch_path = os.path.join(work_dir, "spectate_temp.bat")
                with open(batch_path, 'w') as f:
                    f.write(f'cd /d "{work_dir}"\n')
                    f.write(f'"{exe_path}" {args}\n')
                    
                self.log(f"Created batch file: {batch_path}", "DEBUG")
                os.startfile(batch_path)
                self.log("Process started with os.startfile", "SUCCESS")
                return True
            
            # Méthode 2: Utiliser subprocess avec shell=True
            self.log("Trying to start game with shell=True", "INFO")
            cmd = f'"{exe_path}" {args}'
            self.log(f"Shell command: {cmd}", "DEBUG")
            
            subprocess.Popen(
                cmd, 
                cwd=work_dir, 
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self.log("Process started with shell=True command", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Error in alternative launch method: {str(e)}", "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False

    def check_system_processes(self):
        """Vérifie les processus système pour diagnostiquer les problèmes potentiels"""
        try:
            self.log("Checking system processes for diagnostics", "INFO")
            
            # Lister tous les processus liés à League of Legends
            lol_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower() if proc_info['name'] else ""
                    if 'league' in proc_name or 'lol' in proc_name:
                        lol_processes.append({
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'cmdline': proc_info['cmdline']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                
            if lol_processes:
                self.log(f"Found {len(lol_processes)} League of Legends related processes:", "INFO")
                for proc in lol_processes:
                    self.log(f"PID: {proc['pid']}, Name: {proc['name']}, CMD: {proc['cmdline']}", "DEBUG")
            else:
                self.log("No League of Legends processes currently running", "INFO")
                
            # Vérifier l'utilisation du CPU/RAM
            system_info = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'available_memory_mb': psutil.virtual_memory().available / (1024 * 1024)
            }
            
            self.log(f"System resources: CPU: {system_info['cpu_percent']}%, "
                    f"RAM: {system_info['memory_percent']}%, "
                    f"Available memory: {system_info['available_memory_mb']:.2f} MB", "DEBUG")
                    
            return True
        except Exception as e:
            self.log(f"Error checking system processes: {str(e)}", "ERROR")
            return False

    def shutdown(self):
        """Shutdown service and all threads safely"""
        self.log("Service shutdown initiated", "INFO")
        
        # Arrêter d'abord le thread de vérification des jeux
        if hasattr(self, 'game_checker') and self.game_checker and self.game_checker.isRunning():
            self.log("Stopping game checker thread...", "INFO")
            self.game_checker.running = False
            self.game_checker.wait(5000)  # Attendre max 5 secondes
            if self.game_checker.isRunning():
                self.log("Force terminating game checker thread", "WARNING")
                self.game_checker.terminate()
        
        # Arrêter le streaming s'il est en cours
        if self.isStreaming:
            try:
                self.log("Stopping active stream...", "INFO")
                self.stop_streaming()
            except Exception as e:
                self.log(f"Error stopping stream during shutdown: {str(e)}", "ERROR")
        
        # Fermer proprement la connexion OBS si elle existe
        if hasattr(self, 'obs_manager') and self.obs_manager:
            try:
                self.log("Closing OBS connection...", "INFO")
                self.obs_manager.disconnect()
            except Exception as e:
                self.log(f"Error disconnecting from OBS: {str(e)}", "ERROR")
        
        self.log("Service shutdown complete", "INFO")

class SafeGameCheckerThread(QThread):
    """Safe implementation of game checker thread"""
    show_error = Signal(str, str)
    launch_spectate_signal = Signal(list)
    
    def __init__(self, service):
        try:
            super().__init__()
            self.service = service
            self.running = False
            
            # Connecter le signal aux méthodes du thread principal
            self.launch_spectate_signal.connect(self.service.launch_spectate_client, Qt.QueuedConnection)
            
        except Exception as e:
            print(f"[CRITICAL] Error initializing SafeGameCheckerThread: {str(e)}")
    
    def run(self):
        """Functional implementation that checks for active games and starts streaming"""
        try:
            self.service.log("Game checker thread starting", "INFO")
            self.running = True
            start_time = time.time()
            
            # Main service loop
            while self.running:
                try:
                    # Vérifier si le thread n'a pas été interrompu
                    if not self.running:
                        self.service.log("Thread stopping (interrupted)", "WARNING")
                        break
                        
                    # Log une fois par heure pour montrer que le thread est toujours actif
                    current_time = time.time()
                    if current_time - start_time > 3600:  # 1 heure
                        self.service.log("Game checker thread still active (hourly check)", "INFO")
                        start_time = current_time
                    
                    # Skip if already streaming
                    if self.service.isStreaming:
                        self.service.log("Already streaming, skipping check", "DEBUG")
                        time.sleep(10)  # Check less frequently when streaming
                        continue
                    
                    self.service.log("Checking for active games...", "INFO")
                    
                    # Create API instance with configured API key
                    if not self.service.config.riot_api_key:
                        self.service.log("No Riot API key configured", "ERROR")
                        time.sleep(30)  # Wait longer on error
                        continue
                    
                    # Get all enabled players sorted by priority
                    enabled_players = [(name, player) for name, player in self.service.config.players.items() 
                                      if player.enabled]
                    
                    if not enabled_players:
                        self.service.log("No enabled players configured", "WARNING")
                        time.sleep(30)
                        continue
                    
                    # Sort by priority (lower number = higher priority)
                    enabled_players.sort(key=lambda p: p[1].priority)
                    
                    # Check each player for active games
                    for player_name, player_config in enabled_players:
                        try:
                            self.service.log(f"Checking if {player_name} is in game", "INFO")
                            
                            # Initialize League API for this player's region
                            api = LeagueAPI(
                                api_key=self.service.config.riot_api_key,
                                region=player_config.region
                            )
                            api.set_logger(self.service.log)
                            
                            # Get the summoner ID
                            summoner_id = player_config.summoner_id
                            if not summoner_id:
                                self.service.log(f"No summoner ID for {player_name}", "WARNING")
                                continue
                            
                            # Get active game
                            self.service.log(f"Checking active game for {summoner_id}", "INFO")
                            game_info = api.get_active_game_by_summoner(summoner_id)
                            
                            if not game_info:
                                self.service.log(f"Player {player_name} is not in game", "INFO")
                                continue
                                
                            # Found active game!
                            game_id = game_info.get('gameId')
                            if not game_id:
                                self.service.log(f"Invalid game info returned for {player_name}", "ERROR")
                                continue
                                
                            self.service.log(f"Found active game for {player_name}: Game ID {game_id}", "SUCCESS")
                            
                            # Check if League path is configured
                            if not self.service.config.league_path or not os.path.exists(self.service.config.league_path):
                                self.service.log("League path is not correctly configured", "ERROR")
                                continue
                                
                            # Create spectate command
                            spectate_cmd = api.create_spectate_command(game_id, self.service.config.league_path)
                            
                            # Start spectating
                            self.service.log(f"Starting spectate with command: {spectate_cmd}", "INFO")
                            
                            try:
                                # Launch the spectate client
                                self.launch_spectate_signal.emit(spectate_cmd)
                                
                            except Exception as e:
                                self.service.log(f"Error launching spectate command: {str(e)}", "ERROR")
                                import traceback
                                trace = traceback.format_exc()
                                self.service.log(f"Stack trace: {trace}", "ERROR")
                                continue
                            
                            # Wait for game client to start
                            self.service.log("Waiting for game client to start...", "INFO")
                            max_wait = 60  # Wait up to 60 seconds
                            game_started = False
                            
                            for _ in range(max_wait):
                                if self.service.is_league_game_running():
                                    game_started = True
                                    self.service.log("League game client detected", "SUCCESS")
                                    break
                                time.sleep(1)
                                
                            if not game_started:
                                self.service.log("Timed out waiting for game client to start", "ERROR")
                                continue
                                
                            # Start streaming for this player
                            self.service.log(f"Setting up streaming for {player_name}", "INFO")
                            
                            # Connect to OBS if needed
                            if self.service.obs_manager and not self.service.is_obs_running():
                                self.service.log("Launching OBS...", "INFO")
                                self.service.launch_obs()
                                time.sleep(5)  # Wait for OBS to start
                            
                            if self.service.obs_manager:
                                try:
                                    self.service.connect_obs()
                                    self.service.log("Connected to OBS", "SUCCESS")
                                except Exception as e:
                                    self.service.log(f"Failed to connect to OBS: {str(e)}", "ERROR")
                            
                            # Start actual streaming
                            streaming_started = self.service.start_streaming(player_name, player_config)
                            
                            if streaming_started:
                                self.service.log(f"Successfully started streaming for {player_name}", "SUCCESS")
                                # Stream is now active, break out of player loop
                                break
                            else:
                                self.service.log(f"Failed to start streaming for {player_name}", "ERROR")
                                # Try to kill game and move to next player
                                self.service.kill_league_game()
                                
                        except Exception as e:
                            self.service.log(f"Error processing player {player_name}: {str(e)}", "ERROR")
                            import traceback
                            trace = traceback.format_exc()
                            self.service.log(f"Stack trace: {trace}", "ERROR")
                            continue
                    
                    # Wait before next check cycle
                    self.service.log("Waiting before next check cycle", "INFO")
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    self.service.log(f"Error in game checker loop: {str(e)}", "ERROR")
                    import traceback
                    trace = traceback.format_exc() 
                    self.service.log(f"Stack trace: {trace}", "ERROR")
                    time.sleep(60)  # Wait longer on error
                    
        except Exception as e:
            self.service.log(f"Critical error in game checker thread: {str(e)}", "ERROR")
            import traceback
            trace = traceback.format_exc()
            self.service.log(f"Stack trace: {trace}", "ERROR")
            
        finally:
            self.service.log("Game checker thread stopping", "WARNING")
            self.running = False
            
            # Clean up if thread is stopping
            if self.service.isStreaming:
                try:
                    self.service.stop_streaming()
                except Exception as e:
                    self.service.log(f"Error stopping stream during shutdown: {str(e)}", "ERROR")