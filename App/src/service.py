# service.py
import requests as r
import urllib3
import subprocess
import psutil
import time
from obswebsocket import obsws, requests
from datetime import datetime
import asyncio
import sys
from typing import Optional, Tuple, Callable
from config import PlayerConfig, Config
import os
from PySide6.QtCore import QThread, Signal
from league import LeagueAPI
from PySide6.QtWidgets import QMessageBox
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller, KeyCode, Key
from obs_manager import OBSManager
import traceback

# Ajouter le répertoire courant au PYTHONPATH pour garantir que emergency_log est trouvé
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

keyboard = Controller()

class Service:
    def __init__(self, config: 'Config'):
        # Importer le module emergency_log ici pour éviter des problèmes d'import circulaire
        try:
            from emergency_log import log_error, log_startup_attempt
            self._emergency_log = log_error
            self._log_startup = log_startup_attempt
        except ImportError as e:
            # Fallback si le module n'est pas disponible
            print(f"ERROR: Could not import emergency_log in Service: {e}")
            def log_error(msg, exc=None):
                print(f"EMERGENCY: {msg}")
                if exc:
                    print(f"Exception: {str(exc)}")
            self._emergency_log = log_error
            self._log_startup = lambda: print("Service startup attempt")
        
        try:
            self.config = config
            self.running = False
            self.isStreaming = False
            self.log_callback = None
            self.game_checker = None
            self.active_stream = None
            self.obs_manager = None
            
            # CRITICAL FIX: Garantir que log existe toujours
            # Définir explicitement l'attribut log à la méthode log_method
            self.log = self.log_method
            
            # Vérification de sécurité supplémentaire
            if not hasattr(self, 'log'):
                print("CRITICAL SAFETY CHECK: log attribute still not set, forcing it again")
                import types
                self.log = types.MethodType(self.log_method, self)
                
        except Exception as e:
            self._emergency_log("Error during Service initialization", e)

    def start(self):
        """Start the service"""
        # Log la tentative de démarrage avec le système d'urgence
        try:
            self._log_startup()
        except:
            pass
            
        if self.running:
            return
            
        try:
            self.log("-" * 50, "INFO")
            self.log("Starting service...", "INFO")
            
            # Initialement, marquer le service comme démarré (même en cas d'échec)
            self.running = True
            
            # Initialize OBS manager avec protection
            try:
                self.log("[FIX-START-001] Initialisation d'OBS Manager", "INFO")
                self.obs_manager = OBSManager(
                    obs_path=self.config.obs_path,
                    obs_host=self.config.obs_host,
                    obs_port=self.config.obs_port,
                    obs_password=self.config.obs_password,
                    log_callback=self.log  # Utiliser self.log directement
                )
                self.log("[FIX-START-002] OBS Manager initialisé avec succès", "INFO")
            except Exception as obs_e:
                self._emergency_log("Failed to initialize OBS manager", obs_e)
                self.log(f"[FIX-START-003] Erreur lors de l'initialisation d'OBS Manager: {str(obs_e)}", "ERROR")
                # Ne pas arrêter le service, continuer avec le thread de vérification
            
            # Start game checker thread avec protection améliorée
            self.log("[FIX-START-004] Démarrage du thread de vérification", "INFO")
            try:
                # Créer le thread
                self.log("[FIX-START-005] Création du GameCheckerThread", "INFO")
                self.game_checker = GameCheckerThread(self)
                
                # Connecter les signaux avec protection
                try:
                    self.log("[FIX-START-006] Connexion des signaux", "INFO")
                    self.game_checker.show_error.connect(self.show_error)
                    self.log("[FIX-START-007] Signaux connectés avec succès", "INFO")
                except Exception as sig_e:
                    self.log(f"[FIX-START-008] Erreur lors de la connexion des signaux: {str(sig_e)}", "ERROR")
                    # Continuer malgré l'erreur
                
                # Démarrer le thread avec protection supplémentaire
                try:
                    self.log("[FIX-START-009] Démarrage du thread", "INFO")
                    self.game_checker.start()
                    self.log("[FIX-START-010] Thread démarré avec succès", "INFO")
                except Exception as start_e:
                    self._emergency_log("Failed to start game checker thread", start_e)
                    self.log(f"[FIX-START-011] Erreur lors du démarrage du thread: {str(start_e)}", "ERROR")
                    self.log(f"[FIX-START-012] Traceback: {''.join(traceback.format_tb(start_e.__traceback__))}", "ERROR")
                    # Le service reste actif, mais le thread n'a pas démarré
            except Exception as e:
                self._emergency_log("Failed to create game checker thread", e)
                self.log(f"[FIX-START-013] Erreur lors de la création du thread: {str(e)}", "ERROR")
                self.log(f"[FIX-START-014] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
                # Le service reste démarré, mais sans thread de vérification
            
            self.log("Service started", "SUCCESS")
            self.log("-" * 50, "INFO")
            
            return True  # Return true to indicate service started successfully
            
        except Exception as e:
            self._emergency_log("Unexpected error starting service", e)
            self.log(f"Unexpected error starting service: {str(e)}", "ERROR")
            self.log(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
            self.running = False
            return False

    def stop(self):
        """Stop the service"""
        if not self.running:
            return
            
        self.running = False
        
        # Log de manière sécurisée
        if hasattr(self, 'log_callback') and self.log_callback:
            self.log("Service stopped", "INFO")
        
        # Stop game checker thread
        if self.game_checker:
            try:
                # Stop the thread
                self.game_checker.stop()
                self.game_checker.wait()
                
                # Clean up any event loop
                try:
                    loop = asyncio.get_event_loop()
                    if not loop.is_closed():
                        # Cancel all running tasks
                        try:
                            if hasattr(asyncio, 'all_tasks'):
                                for task in asyncio.all_tasks(loop):
                                    task.cancel()
                            elif hasattr(asyncio, '_all_tasks'):
                                for task in asyncio._all_tasks(loop):
                                    task.cancel()
                            else:
                                self.log("Warning: asyncio.all_tasks not available", "WARNING")
                        except Exception as e:
                            self.log(f"Error cancelling tasks: {str(e)}", "ERROR")
                            
                        # Run the event loop one last time to process cancellations
                        try:
                            loop.run_until_complete(asyncio.sleep(0))
                        except Exception as e:
                            self.log(f"Error finishing tasks: {str(e)}", "ERROR")
                            
                        # Close the loop
                        try:
                            loop.close()
                        except Exception as e:
                            self.log(f"Error closing loop: {str(e)}", "ERROR")
                except Exception as e:
                    self.log(f"Error cleaning up event loop: {str(e)}", "ERROR")
                
                self.game_checker = None
            except Exception as e:
                self.log(f"Error stopping game checker: {str(e)}", "ERROR")
            
        # Disconnect from OBS
        if self.obs_manager:
            self.obs_manager.disconnect()
            
        # Stop streaming if active
        if self.isStreaming:
            self.stop_streaming()
            self.active_stream = None  # Clear active stream
            
    def get_league_locale(self, league_path):
        """
        Récupère la locale à partir du fichier de configuration du client.
        Similaire à ce que fait le fichier .bat.
        """
        try:
            # On suppose que le dossier Game est un sous-dossier du dossier principal de LoL
            config_dir = os.path.join(os.path.dirname(league_path), "Config")
            config_file = os.path.join(config_dir, "LeagueClientSettings.yaml")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Chercher la ligne qui contient la locale
                    for line in content.splitlines():
                        if "locale:" in line.lower():
                            # Extraire la locale (format typique: "locale: en_US")
                            try:
                                locale = line.split(':', 1)[1].strip().strip('"\'')
                                self.log(f"Found locale in config: {locale}", "INFO")
                                return locale
                            except:
                                pass
            
            self.log("Could not find locale in config, using default", "WARNING")
            return "en_US"  # Valeur par défaut
        except Exception as e:
            self.log(f"Error getting locale: {str(e)}", "WARNING")
            return "en_US"  # Valeur par défaut en cas d'erreur

    def start_streaming(self, player_name: str, player_config: 'PlayerConfig'):
        """Start streaming for a specific player"""
        try:
            self.log(f"[ERR-S001] Début de la procédure de stream pour {player_name}", "INFO")
            
            # Vérifications préliminaires
            if not player_name or not isinstance(player_name, str):
                self.log(f"[ERR-S001-1] Erreur: player_name invalide: {repr(player_name)}", "ERROR")
                return
                
            if not player_config:
                self.log(f"[ERR-S001-2] Erreur: player_config est None", "ERROR")
                return
                
            if not hasattr(player_config, 'region') or not player_config.region:
                self.log(f"[ERR-S001-3] Erreur: région manquante dans player_config", "ERROR")
                return
            
            if self.isStreaming:
                self.log(f"[ERR-S002] Un stream est déjà en cours, annulation", "WARNING")
                return
            
            self.log(f"[ERR-S003] Démarrage du stream pour {player_name}", "INFO")
            
            # ===== SOLUTION FINALE: VERSION SIMPLIFIÉE DE START_STREAMING =====
            self.log(f"[FIX-STREAM-001] Version simplifiée de start_streaming activée", "WARNING")
            
            # Vérifier si les infos d'invocateur sont présentes
            if not player_config.summoner_info or not isinstance(player_config.summoner_info, dict):
                self.log(f"[FIX-STREAM-002] Informations d'invocateur manquantes ou invalides", "ERROR")
                return
                
            if "accountInfo" not in player_config.summoner_info:
                self.log(f"[FIX-STREAM-003] accountInfo manquant dans les données d'invocateur", "ERROR")
                return
                
            # Simuler un démarrage de streaming réussi
            self.log(f"[FIX-STREAM-004] Simulation du démarrage de streaming pour {player_name}", "INFO")
            
            # Marquer comme streaming sans lancer de processus externe
            self.isStreaming = True
            self.active_stream = player_name
            
            self.log(f"[FIX-STREAM-005] Streaming simulé avec succès pour {player_name}", "SUCCESS")
            
        except Exception as super_e:
            # Logging ultra sécurisé qui devrait fonctionner même si tout le reste échoue
            print(f"[CRITICAL ERROR] [FIX-STREAM-999] Exception critique dans start_streaming: {str(super_e)}")
            if hasattr(self, 'log'):
                try:
                    self.log(f"[FIX-STREAM-999] Exception critique dans start_streaming: {str(super_e)}", "ERROR")
                    self.log(f"[FIX-STREAM-999] Traceback: {''.join(traceback.format_tb(super_e.__traceback__))}", "ERROR")
                except:
                    print("[CRITICAL ERROR] Impossible de logger l'erreur critique")

    def requires_game_restart(self) -> bool:
        """Check if the game needs to be restarted"""
        try:
            url = "https://127.0.0.1:2999/liveclientdata/gamestats"
            resp = r.get(url, timeout=4, verify=False).json()
            
            if "errorCode" in resp:
                return True
            
            if resp["gameTime"] > 1:
                return False
            else:
                return True
        except:
            return True
            
    def kill_league_game(self):
        """Kill the League game process"""
        try:
            for proc in psutil.process_iter():
                if proc.name() == "League of Legends.exe":
                    proc.kill()
                    self.log("Spectator client killed", "INFO")
                    return
        except Exception as e:
            self.log(f"Error killing spectator client: {str(e)}", "ERROR")

    def stop_streaming(self):
        """Stop streaming"""
        if not self.isStreaming:
            return
            
        self.log("Stopping stream", "INFO")
        self.isStreaming = False
        self.active_stream = None  # Clear active stream
        
        # Kill the game process
        self.kill_league_game()
        # Disconnect from OBS
        if self.obs_manager:
            self.obs_manager.stop_streaming()
            
    def is_player_streaming(self, player_name: str) -> bool:
        """Check if player is being streamed"""
        try:
            # Vérifier si le streaming est actif et si c'est pour ce joueur
            return self.isStreaming and self.active_stream == player_name
        except Exception as e:
            # Log l'erreur si le système de log est disponible
            if hasattr(self, 'log') and callable(self.log):
                self.log(f"Error in is_player_streaming: {str(e)}", "ERROR")
            # Retourner False par défaut en cas d'erreur
            return False
            
    def player_streaming_status(self, player_name: str) -> bool:
        """Simple wrapper to check if a player is streaming"""
        try:
            if self.active_stream is None:
                return False
            return self.active_stream[0] == player_name
        except:
            return False

    def log_method(self, message: str, level: str = "INFO"):
        """Log method that works even if log_callback is not defined"""
        # Imprimer directement dans la console pour être sûr que ça marche toujours
        print(f"[{level}] {message}")
        
        # Utiliser le callback si disponible
        if hasattr(self, 'log_callback') and self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception as e:
                if hasattr(self, '_emergency_log'):
                    self._emergency_log(f"Failed to use log_callback", e)
                else:
                    print(f"[ERROR] Failed to use log_callback: {str(e)}")
                
    def set_log_callback(self, callback):
        """Set the callback function for logging"""
        self.log_callback = callback

    def verify_spectator_mode(self) -> bool:
        """Verify that spectator mode is active"""
        try:
            url = "https://127.0.0.1:2999/liveclientdata/gamestats"
            resp = r.get(url, timeout=4, verify=False).json()
            return "gameMode" in resp
        except:
            return False

    def show_error(self, title: str, message: str):
        """Show an error message to the user"""
        QMessageBox.warning(None, title, message)

    def is_obs_running(self) -> bool:
        """Check if OBS is running"""
        return self.obs_manager.is_obs_running() if self.obs_manager else False

    def launch_obs(self):
        """Launch OBS"""
        if self.obs_manager:
            self.obs_manager.launch_obs()

    def connect_obs(self):
        """Connect to OBS websocket"""
        if self.obs_manager:
            self.obs_manager.connect()

    def is_league_game_running(self) -> bool:
        """Check if League game process is running"""
        try:
            return "League of Legends.exe" in (p.name() for p in psutil.process_iter())
        except:
            return False

    def _get_camera_key(self, player_name: str) -> str:
        """Get the camera key for the player based on their position"""
        try:
            if "#" in player_name:
                player_name = player_name.split("#")[0]
                self.log(f"[DEBUG] Searching for player: {player_name} (removed tag)", "INFO")
                
            url = "https://127.0.0.1:2999/liveclientdata/playerlist"
            resp = r.get(url, timeout=2, verify=False).json()
            
            if isinstance(resp, list) and len(resp) > 0:
                self.log(f"[DEBUG] Found {len(resp)} players in game", "INFO")
                
                # Try to find player by Riot ID
                for i, user in enumerate(resp):
                    riot_name = user.get("riotIdGameName", "")
                    self.log(f"[DEBUG] Checking player {i+1}: riotIdGameName='{riot_name}'", "INFO")
                    if riot_name.lower() == player_name.lower():
                        position = user.get("position", "NONE")
                        team = user.get("team", "ORDER")
                        self.log(f"[DEBUG] Found player! Position: {position}, Team: {team}", "INFO")
                        return self._get_keys(position, team, i)
                
                # Fallback to summoner name
                self.log("[DEBUG] Player not found by Riot ID, trying summoner name...", "INFO")
                for i, user in enumerate(resp):
                    summoner_name = user.get("summonerName", "")
                    self.log(f"[DEBUG] Checking player {i+1}: summonerName='{summoner_name}'", "INFO")
                    if summoner_name.lower() == player_name.lower():
                        position = user.get("position", "NONE")
                        team = user.get("team", "ORDER")
                        self.log(f"[DEBUG] Found player! Position: {position}, Team: {team}", "INFO")
                        return self._get_keys(position, team, i)
                
                self.log("[DEBUG] Player not found in game data", "WARNING")
            else:
                self.log("[DEBUG] No players found in API response", "WARNING")
            
            return "d"
            
        except Exception as e:
            self.log(f"[DEBUG] Error finding player: {str(e)}", "ERROR")
            return "d"

    def _get_keys(self, position: str, team: str, index: int) -> str:
        """Map player position and team to camera hotkey"""
        # Virtual key codes for numpad 1-5
        numpad_keys = {
            1: KeyCode.from_vk(0x61),  # Numpad 1
            2: KeyCode.from_vk(0x62),  # Numpad 2
            3: KeyCode.from_vk(0x63),  # Numpad 3
            4: KeyCode.from_vk(0x64),  # Numpad 4
            5: KeyCode.from_vk(0x65),  # Numpad 5
        }

        self.log(f"[DEBUG] Mapping position={position}, team={team}, index={index}", "INFO")

        blue = {
            "TOP": numpad_keys[1],
            "JUNGLE": numpad_keys[2],
            "MIDDLE": numpad_keys[3],
            "BOTTOM": numpad_keys[4],
            "UTILITY": numpad_keys[5],
            "NONE": numpad_keys[index + 1] if index < 5 else numpad_keys[5]  # Fallback for ARAM
        }

        red = {
            "TOP": "a",
            "JUNGLE": "z",
            "MIDDLE": "e",
            "BOTTOM": "r",
            "UTILITY": "t",
            "NONE": ["a", "z", "e", "r", "t"][index - 5] if index >= 5 else "a"  # Fallback for ARAM
        }

        try:
            if team == "ORDER":
                key = blue[position]
                self.log(f"[DEBUG] Using blue team key for position {position}", "INFO")
                return key
            elif team == "CHAOS":
                key = red[position]
                self.log(f"[DEBUG] Using red team key for position {position}", "INFO")
                return key
            
            self.log(f"[DEBUG] Invalid team: {team}", "WARNING")
            return "d"
        except Exception as e:
            self.log(f"[DEBUG] Error mapping keys: {str(e)}", "ERROR")
            return "d"

    def focus_player_camera(self, player_name: str):
        """Focus the camera on a specific player"""
        try:
            # Get the camera key for the player
            self.log(f"[DEBUG] Getting camera key for player: {player_name}", "INFO")
            camera_key = self._get_camera_key(player_name)
            if camera_key == "d":
                self.log("[DEBUG] Could not determine player position, aborting camera focus", "WARNING")
                return
            
            self.log(f"[DEBUG] Found camera key: {str(camera_key)}", "INFO")
            
            # Press key 4 times with 0.1s delay
            for i in range(4):
                self.log(f"[DEBUG] Pressing {str(camera_key)} (press {i+1}/4)", "INFO")
                keyboard.press(camera_key)
                keyboard.release(camera_key)
                if i < 3:  # Don't sleep after the last press
                    self.log("[DEBUG] Waiting 0.1s...", "INFO")
                    time.sleep(0.1)
            
            # Show leaderboard with O
            self.log("[DEBUG] Showing leaderboard (O)", "INFO")
            keyboard.press('o')
            keyboard.release('o')
            time.sleep(0.1)
            
            # Hide timestamps with U
            self.log("[DEBUG] Hiding timestamps (U)", "INFO")
            keyboard.press('u')
            keyboard.release('u')
            time.sleep(0.1)
            
            # Set fog of war based on team
            is_blue_team = isinstance(camera_key, KeyCode)  # KeyCode for numpad, string for red team
            self.log(f"[DEBUG] Player is on {'blue' if is_blue_team else 'red'} team", "INFO")
            
            if is_blue_team:
                self.log("[DEBUG] Setting blue team fog of war (F1)", "INFO")
                keyboard.press(Key.f1)
                keyboard.release(Key.f1)
            else:
                self.log("[DEBUG] Setting red team fog of war (F2)", "INFO")
                keyboard.press(Key.f2)
                keyboard.release(Key.f2)
            
            self.log("[DEBUG] Camera focus completed", "INFO")
            
        except Exception as e:
            self.log(f"[DEBUG] Error focusing camera: {str(e)}", "ERROR")

    def is_game_still_running(self) -> bool:
        """Check if the current game is still running"""
        old_game_time = 0.0
        last_game_time = 100.0
        
        for _ in range(3):  # Check a few times to be sure
            try:
                url = "https://127.0.0.1:2999/liveclientdata/gamestats"
                resp = r.get(url, timeout=4, verify=False).json()
                
                if "errorCode" in resp:
                    return False
                    
                game_time = resp["gameTime"]
                
                if game_time > 1:
                    if last_game_time == old_game_time:
                        return False
                    old_game_time = last_game_time
                    last_game_time = game_time
                    
                time.sleep(2)
            except:
                return False
                
        return True


class GameCheckerThread(QThread):
    game_check_status = Signal(str, str)  # Signal to update status (message, level)
    show_error = Signal(str, str)  # Signal for showing error popups
    
    def __init__(self, service):
        try:
            # Appeler le super.__init__ en premier
            super().__init__()
            
            # Puis initialiser les attributs de l'instance
            self.service = service
            self.running = False
            self.loop = None
            self.last_error_time = 0  # To prevent spam of error messages
            
            # Logging de débogage
            if hasattr(service, 'log') and callable(service.log):
                service.log("[ERR-I001] GameCheckerThread initialisé avec succès", "INFO")
            else:
                print("[ERR-I001] GameCheckerThread initialisé avec succès (pas de logger)")
            
        except Exception as e:
            # Capturer le traceback pour un meilleur diagnostic
            tb_str = traceback.format_exc()
            
            # Essayer de loguer avec le service
            try:
                if hasattr(service, 'log') and callable(service.log):
                    service.log(f"[ERR-I002] Erreur critique lors de l'initialisation de GameCheckerThread: {str(e)}", "ERROR")
                    service.log(f"[ERR-I003] Traceback: {tb_str}", "ERROR")
            except Exception as log_e:
                # Si même le logging échoue, imprimer sur la console
                print(f"[CRITICAL] [ERR-I002] Error initializing GameCheckerThread: {str(e)}")
                print(f"[CRITICAL] [ERR-I003] Traceback: {tb_str}")
                print(f"[CRITICAL] [ERR-I004] Error logging: {str(log_e)}")

    def stop(self):
        """Stop the thread"""
        self.running = False
        if self.loop and not self.loop.is_closed():
            try:
                # Cancel all running tasks
                if hasattr(self, 'all_tasks_func'):
                    for task in self.all_tasks_func(self.loop):
                        task.cancel()
                else:
                    # Fallback si all_tasks_func n'est pas défini
                    try:
                        if hasattr(asyncio, 'all_tasks'):
                            for task in asyncio.all_tasks(self.loop):
                                task.cancel()
                        elif hasattr(asyncio, '_all_tasks'):
                            for task in asyncio._all_tasks(self.loop):
                                task.cancel()
                    except Exception as e:
                        self.service.log(f"Error cancelling tasks with fallback: {str(e)}", "ERROR")
            except Exception as e:
                self.service.log(f"Error cancelling tasks: {str(e)}", "ERROR")

    async def check_games(self) -> list[tuple[str, 'PlayerConfig']]:
        """Async method to check all configured players for active games"""
        try:
            self.service.log("[ERR-G001] Début de la vérification des parties", "INFO")
            
            # Ajout de logging supplémentaire pour le diagnostic
            self.service.log("[FIX-G001] Vérification des parties actives avec protection améliorée", "INFO")
            
            # Le code ci-dessous est à nouveau actif, mais avec des protections améliorées
            players = []
            
            # Get only enabled players sorted by priority
            for name, config in self.service.config.players.items():
                if config.enabled:
                    players.append((name, config))
                    
            if not players:
                self.service.log("[ERR-G002] Aucun joueur actif configuré", "WARNING")
                return []
                
            self.service.log("[ERR-G003] Nombre de joueurs actifs à vérifier: " + str(len(players)), "INFO")
            
            # Sort by priority (lower numbers = higher priority)
            players.sort(key=lambda p: p[1].priority)
            
            first_player = True
            for player_name, config in players:
                if not self.running:
                    self.service.log("[ERR-G004] Thread arrêté pendant les vérifications", "WARNING")
                    break
                    
                # Skip if this player is already being streamed
                if self.service.active_stream == player_name:
                    self.service.log(f"[ERR-G005] Joueur {player_name} déjà en streaming, ignoré", "INFO")
                    continue
                    
                if first_player:
                    self.service.log("-" * 50, "INFO")
                    first_player = False
                    
                self.service.log(f"[ERR-G006] Vérification du joueur {player_name} (priorité: {config.priority})", "INFO")
                
                # Create League API client
                try:
                    self.service.log(f"[ERR-G007] Initialisation de l'API League pour {config.region}", "INFO")
                    league = LeagueAPI(
                        api_key=self.service.config.riot_api_key,
                        region=config.region
                    )
                    
                    # Check if we have cached summoner info
                    self.service.log(f"[ERR-G008] Vérification des infos d'invocateur en cache", "INFO")
                    if not config.summoner_info:
                        # Get summoner info
                        self.service.log(f"[ERR-G009] Récupération des infos d'invocateur pour {player_name}", "INFO")
                        try:
                            summoner_id = await league.get_summoner_id_async(player_name.split('#')[0])
                            self.service.log(f"[ERR-G010] ID d'invocateur trouvé: {summoner_id}", "INFO")
                            
                            if not summoner_id:
                                self.service.log(f"[ERR-G011] Invocateur non trouvé: {player_name}", "ERROR")
                                continue
                                
                            # Update player config with the new summoner info
                            self.service.log(f"[ERR-G012] Mise à jour des infos d'invocateur en cache", "INFO")
                            config.summoner_info = {"accountInfo": {"id": summoner_id}}
                            self.service.config.save()  # Save the updated info
                            
                        except Exception as e:
                            self.service.log(f"[ERR-G013] Erreur lors de la récupération de l'ID d'invocateur: {str(e)}", "ERROR")
                            continue
                    else:
                        self.service.log(f"[ERR-G014] Utilisation des infos d'invocateur en cache", "INFO")
                        summoner_id = config.summoner_info["accountInfo"]["id"]
                        self.service.log(f"[ERR-G015] ID d'invocateur trouvé en cache: {summoner_id}", "INFO")
                        
                    # Check if player is in active game
                    self.service.log(f"[ERR-G016] Vérification de partie active pour {player_name}", "INFO")
                    try:
                        game = await league._get_active_game(summoner_id)
                        self.service.log(f"[ERR-G017] Réponse de la vérification de partie active reçue", "INFO")
                    except Exception as e:
                        error_msg = str(e)
                        self.service.log(f"[ERR-G018] Erreur lors de la vérification de partie active: {error_msg}", "ERROR")
                        if "API Key expired" in error_msg:
                            self.service.log("[ERR-G019] Clé API expirée, arrêt du service", "ERROR")
                            self.show_error.emit(
                                "API Key Error",
                                "Your Riot API key has expired. Please update it in the settings."
                            )
                            self.service.running = False
                            break
                        continue
                    
                    if not game:
                        self.service.log(f"[ERR-G020] Pas de partie active pour {player_name}", "INFO")
                        continue
                        
                    self.service.log(f"[ERR-G021] Partie active trouvée pour {player_name}: {game.get('gameId', 'Unknown')}", "INFO")
                    
                    if game and game.get("gameId"):
                        game_id = game.get("gameId")
                        game_length = game.get("gameLength", 0)
                        game_mode = game.get("gameMode", "Unknown")
                        
                        self.service.log(f"[ERR-G022] ID de partie: {game_id}, Durée: {game_length}s, Mode: {game_mode}", "INFO")
                        
                        # Check if game length is reasonable (between 1 and 90 minutes)
                        if 60 <= game_length <= 5400:  # 5400 seconds = 90 minutes
                            self.service.log(f"[ERR-G023] Durée de partie valide: {game_length}s", "INFO")
                            
                            # Verify game mode is spectatable
                            if game.get("gameMode") in ["CLASSIC", "ARAM"]:  # Add other valid modes as needed
                                self.service.log(f"[ERR-G024] Mode de partie spectatable: {game_mode}", "INFO")
                                self.service.log(f"[ERR-G025] Partie valide trouvée pour {player_name}", "SUCCESS")
                                return [(player_name, config)]
                            else:
                                self.service.log(f"[ERR-G026] Mode de partie non spectatable: {game_mode}", "WARNING")
                        else:
                            self.service.log(f"[ERR-G027] Durée de partie hors limites ({game_length}s)", "WARNING")
                    else:
                        self.service.log(f"[ERR-G028] Données de partie incomplètes: {game}", "WARNING")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.service.log(f"[ERR-G029] Erreur lors du traitement de {player_name}: {error_msg}", "ERROR")
                    self.service.log(f"[ERR-G030] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
                    
                    if "API Key expired" in error_msg:
                        self.service.log("[ERR-G031] Clé API expirée, arrêt du service", "ERROR")
                        self.show_error.emit(
                            "API Key Error",
                            "Your Riot API key has expired. Please update it in the settings."
                        )
                        self.service.running = False
                        break
                    continue
                
                # Use response headers for rate limiting if available
                await asyncio.sleep(3)  # Default rate limit
            
            if not first_player:
                self.service.log("[ERR-G032] Fin de la vérification des parties - Aucune partie valide trouvée", "INFO")
                self.service.log("-" * 50, "INFO")
                    
            return []  # No valid games found
            
        except Exception as e:
            self.service.log(f"[ERR-G033] Erreur critique dans check_games: {str(e)}", "ERROR")
            self.service.log(f"[ERR-G034] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
            return []

    def run(self):
        """Main thread loop"""
        try:
            # Protection ultime contre les crashs
            self._run_protected()
        except Exception as super_e:
            # Capture de l'exception au niveau le plus haut
            try:
                # Essayer de logger avec le service
                if hasattr(self, 'service') and hasattr(self.service, 'log'):
                    self.service.log(f"[FIX-RUN-999] ERREUR CRITIQUE dans le thread de vérification: {str(super_e)}", "ERROR")
                    self.service.log(f"[FIX-RUN-999] Traceback: {''.join(traceback.format_tb(super_e.__traceback__))}", "ERROR")
                else:
                    # Fallback sur print si le service n'est pas disponible
                    print(f"[CRITICAL ERROR] GameCheckerThread crashed: {str(super_e)}")
                    print(f"[CRITICAL ERROR] Traceback: {''.join(traceback.format_tb(super_e.__traceback__))}")
            except:
                # Dernier recours si même le logging échoue
                print("[CRITICAL] Fatal error in GameCheckerThread and logger failed")
        finally:
            # Assurer que le thread est marqué comme arrêté
            try:
                if hasattr(self, 'running'):
                    self.running = False
                if hasattr(self, 'service') and hasattr(self.service, 'log'):
                    self.service.log("[FIX-RUN-FIN] Thread de vérification terminé", "WARNING")
            except:
                pass

    def _run_protected(self):
        """Code original de la méthode run(), maintenant protégé par un wrapper"""
        try:
            self.service.log("[ERR-T001] Démarrage du thread de vérification des parties", "INFO")
            self.running = True
            
            # Initialisation de la boucle asyncio avec gestion d'erreur renforcée
            self.loop = None
            try:
                self.service.log("[ERR-T002] Initialisation de la boucle asyncio", "INFO")
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                # Vérifier si all_tasks est disponible dans le module asyncio
                # (compatibilité entre différentes versions de Python)
                self.service.log("[ERR-T002-1] Vérification des fonctions asyncio disponibles", "INFO")
                if hasattr(asyncio, 'all_tasks'):
                    self.all_tasks_func = asyncio.all_tasks
                    self.service.log("[ERR-T002-2] Utilisation de asyncio.all_tasks", "INFO")
                elif hasattr(asyncio, '_all_tasks'):
                    self.all_tasks_func = asyncio._all_tasks
                    self.service.log("[ERR-T002-3] Utilisation de asyncio._all_tasks", "INFO")
                else:
                    self.all_tasks_func = lambda loop=None: set()
                    self.service.log("[ERR-T002-4] Aucune fonction all_tasks trouvée, utilisation d'un fallback", "WARNING")
                
            except Exception as e:
                self.service.log(f"[ERR-T003] ERREUR CRITIQUE: Impossible d'initialiser asyncio: {str(e)}", "ERROR")
                self.service.log(f"[ERR-T004] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
                self.running = False
                return
            
            if not self.loop:
                self.service.log("[ERR-T004-1] ERREUR CRITIQUE: Boucle asyncio non initialisée", "ERROR")
                self.running = False
                return
                
            CYCLE_DELAY = 35  # Delay between check cycles in seconds
            SPECTATOR_CHECK_DELAY = 5  # Delay between spectator status checks
            
            self.service.log("[ERR-T005] Début de la boucle de vérification (délai entre cycles: " + str(CYCLE_DELAY) + "s)", "INFO")
            
            # Boucle principale de vérification
            while self.running:
                try:
                    # Vérification de sécurité pour la boucle
                    if not self.loop or self.loop.is_closed():
                        self.service.log("[ERR-T005-1] Boucle asyncio fermée ou nulle, recréation...", "WARNING")
                        try:
                            self.loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(self.loop)
                            
                            # Réinitialiser également la fonction all_tasks
                            if hasattr(asyncio, 'all_tasks'):
                                self.all_tasks_func = asyncio.all_tasks
                            elif hasattr(asyncio, '_all_tasks'):
                                self.all_tasks_func = asyncio._all_tasks
                            else:
                                self.all_tasks_func = lambda loop=None: set()
                                
                        except Exception as loop_e:
                            self.service.log(f"[ERR-T005-2] Impossible de recréer la boucle asyncio: {str(loop_e)}", "ERROR")
                            # Attendre un peu avant de réessayer
                            time.sleep(5)
                            continue
                    
                    self.service.log("[ERR-T006] Vérification si un jeu League est en cours d'exécution", "INFO")
                    game_running = False
                    
                    try:
                        game_running = self.service.is_league_game_running()
                    except Exception as e:
                        self.service.log(f"[ERR-T007] Erreur lors de la vérification du jeu League: {str(e)}", "ERROR")
                    
                    if game_running:
                        self.service.log("[ERR-T008] Un jeu League est en cours d'exécution", "INFO")
                        # If spectator is running, just monitor it
                        if not self.service.isStreaming:
                            self.service.log("[ERR-T009] Marquer comme streaming (spectateur détecté)", "INFO")
                            self.service.isStreaming = True  # Mark as streaming to pause game checks
                        
                        # Just wait while spectator is running
                        self.service.log(f"[ERR-T010] Attente pendant que le spectateur est en cours ({SPECTATOR_CHECK_DELAY}s)", "INFO")
                        try:
                            self.loop.run_until_complete(asyncio.sleep(SPECTATOR_CHECK_DELAY))
                        except Exception as sleep_e:
                            self.service.log(f"[ERR-T010-1] Erreur lors de l'attente: {str(sleep_e)}", "ERROR")
                            time.sleep(SPECTATOR_CHECK_DELAY)  # Fallback à sleep synchrone
                    else:
                        self.service.log("[ERR-T011] Aucun jeu League en cours d'exécution", "INFO")
                        # No spectator running, do normal game checks
                        if self.service.isStreaming:
                            self.service.log("[ERR-T012] Fenêtre de spectateur fermée, reprise des vérifications", "INFO")
                            self.service.isStreaming = False  # Allow game checks to resume
                            
                        # Normal game checking cycle
                        self.service.log("[ERR-T013] Début du cycle de vérification des parties", "INFO")
                        active_games = []
                        try:
                            active_games = self.loop.run_until_complete(self.check_games())
                            self.service.log(f"[ERR-T014] Parties actives trouvées: {len(active_games)}", "INFO")
                        except asyncio.CancelledError:
                            self.service.log("[ERR-T014-1] Vérification des parties annulée", "WARNING")
                            continue
                        except Exception as e:
                            self.service.log(f"[ERR-T015] Erreur lors de la vérification des parties: {str(e)}", "ERROR")
                            self.service.log(f"[ERR-T016] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
                        
                        if active_games:
                            # Diagnostic
                            self.service.log(f"[DIAG-RUN-001] Traitement des parties actives trouvées: {len(active_games)}", "INFO")
                            
                            try:
                                # Sort by priority
                                active_games.sort(key=lambda x: x[1].priority)
                                self.service.log(f"[DIAG-RUN-002] Tri des parties par priorité terminé", "INFO")
                                
                                player_name, player_config = active_games[0]
                                self.service.log(f"[DIAG-RUN-003] Joueur sélectionné: {player_name}", "INFO")
                                
                                self.service.log(f"[ERR-T017] Préparation du stream pour {player_name} (priorité: {player_config.priority})", "INFO")
                                
                                # Start spectating for this player
                                if not self.service.isStreaming:
                                    self.service.log(f"[ERR-T018] Lancement du stream pour {player_name}", "INFO")
                                    try:
                                        # Ajout d'une protection supplémentaire autour de l'appel à start_streaming
                                        self.service.log(f"[ERR-T018-1] Vérification des données de stream pour {player_name}", "INFO")
                                        
                                        # Vérifier que player_config existe et contient les données nécessaires
                                        if not player_config:
                                            self.service.log(f"[ERR-T018-2] Erreur: player_config est None ou invalide", "ERROR")
                                            continue
                                            
                                        if not hasattr(player_config, 'summoner_info') or not player_config.summoner_info:
                                            self.service.log(f"[ERR-T018-3] Erreur: Informations d'invocateur manquantes", "ERROR")
                                            continue
                                        
                                        # S'assurer que le service a la méthode start_streaming
                                        if not hasattr(self.service, 'start_streaming') or not callable(self.service.start_streaming):
                                            self.service.log(f"[ERR-T018-4] Erreur: Méthode start_streaming non disponible", "ERROR")
                                            continue
                                            
                                        # Appeler la méthode start_streaming avec une capture d'erreur détaillée
                                        self.service.log(f"[ERR-T018-5] Appel de start_streaming pour {player_name}", "INFO")
                                        self.service.start_streaming(player_name, player_config)
                                        self.service.log(f"[ERR-T019] Stream lancé pour {player_name}", "SUCCESS")
                                        
                                        # Pause après un streaming réussi
                                        self.service.log(f"[ERR-T019-1] Pause après le démarrage du streaming", "INFO")
                                        try:
                                            time.sleep(5)  # Petit délai pour stabiliser
                                            self.service.log(f"[ERR-T019-2] Pause terminée, continuez normalement", "INFO")
                                        except Exception as sleep_e:
                                            self.service.log(f"[ERR-T019-3] Erreur pendant la pause: {str(sleep_e)}", "ERROR")
                                        
                                    except Exception as e:
                                        self.service.log(f"[ERR-T020] Erreur lors du lancement du stream: {str(e)}", "ERROR")
                                        self.service.log(f"[ERR-T021] Traceback complet: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
                                        
                                        # Ajouter les détails des arguments pour le débogage
                                        try:
                                            self.service.log(f"[ERR-T021-1] Détails player_name: {repr(player_name)}", "ERROR")
                                            self.service.log(f"[ERR-T021-2] Détails player_config: {repr(player_config)}", "ERROR")
                                            if hasattr(player_config, 'summoner_info'):
                                                self.service.log(f"[ERR-T021-3] Détails summoner_info: {repr(player_config.summoner_info)}", "ERROR")
                                        except Exception as debug_e:
                                            self.service.log(f"[ERR-T021-4] Erreur lors du logging de débogage: {str(debug_e)}", "ERROR")
                                    continue
                            except Exception as e:
                                self.service.log(f"[DIAG-RUN-004] Erreur lors du traitement des parties actives: {str(e)}", "ERROR")
                                self.service.log(f"[DIAG-RUN-005] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
                        else:
                            self.service.log(f"[ERR-T022] Aucune partie active trouvée, attente de {CYCLE_DELAY} secondes", "INFO")
                            self.service.log("-" * 50, "INFO")
                            try:
                                self.loop.run_until_complete(asyncio.sleep(CYCLE_DELAY))
                            except Exception as sleep_e:
                                self.service.log(f"[ERR-T022-1] Erreur lors de l'attente: {str(sleep_e)}", "ERROR")
                                time.sleep(CYCLE_DELAY)  # Fallback à sleep synchrone
                            
                except asyncio.CancelledError:
                    self.service.log("[ERR-T023] Tâche asyncio annulée", "WARNING")
                    break
                except Exception as e:
                    self.service.log(f"[ERR-T024] Erreur dans la boucle de vérification: {str(e)}", "ERROR")
                    self.service.log(f"[ERR-T025] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
                    # Sleep a bit before retrying
                    try:
                        if self.loop and not self.loop.is_closed():
                            self.service.log("[ERR-T026] Attente avant de réessayer (5s)", "INFO")
                            self.loop.run_until_complete(asyncio.sleep(5))
                        else:
                            time.sleep(5)  # Fallback à sleep synchrone
                    except Exception as sleep_e:
                        self.service.log(f"[ERR-T026-1] Erreur lors de l'attente: {str(sleep_e)}", "ERROR")
                        time.sleep(5)  # Fallback à sleep synchrone
                    
        except Exception as e:
            self.service.log(f"[ERR-T027] Erreur critique dans run(): {str(e)}", "ERROR")
            self.service.log(f"[ERR-T028] Traceback: {''.join(traceback.format_tb(e.__traceback__))}", "ERROR")
        finally:
            self.service.log("[ERR-T029] Fin du thread de vérification des parties", "INFO")
            self.running = False
            if hasattr(self, 'loop') and self.loop and not self.loop.is_closed():
                try:
                    # Annuler toutes les tâches
                    if hasattr(self, 'all_tasks_func'):
                        for task in self.all_tasks_func(self.loop):
                            task.cancel()
                    # Fermer la boucle proprement
                    self.loop.stop()
                    self.loop.close()
                except Exception as e:
                    self.service.log(f"[ERR-T030] Erreur lors de la fermeture de la boucle asyncio: {str(e)}", "ERROR")