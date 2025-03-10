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
            
            self.running = True
            
            # Initialize OBS manager
            self.obs_manager = OBSManager(
                obs_path=self.config.obs_path,
                obs_host=self.config.obs_host,
                obs_port=self.config.obs_port,
                obs_password=self.config.obs_password,
                log_callback=self.log  # Utiliser self.log directement
            )
            
            # Start game checker thread
            self.log("Starting game checker thread...", "INFO")
            try:
                self.game_checker = GameCheckerThread(self)
                self.game_checker.show_error.connect(self.show_error)
                self.game_checker.start()
            except Exception as e:
                self._emergency_log("Failed to start game checker thread", e)
                self.log(f"Failed to start game checker thread: {str(e)}", "ERROR")
                self.running = False
                return False
            
            self.log("Service started", "SUCCESS")
            self.log("-" * 50, "INFO")
            
            return True  # Return true to indicate service started successfully
            
        except Exception as e:
            self._emergency_log("Unexpected error starting service", e)
            self.log(f"Unexpected error starting service: {str(e)}", "ERROR")
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
                        for task in asyncio.all_tasks(loop):
                            task.cancel()
                        # Run the event loop one last time to process cancellations
                        loop.run_until_complete(asyncio.sleep(0))
                        loop.close()
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
        if self.isStreaming:
            return
        
        self.log(f"Starting to stream {player_name}'s game", "INFO")
        
        try:
            # Get active game info using cached summoner info
            league = LeagueAPI(
                api_key=self.config.riot_api_key,
                region=player_config.region
            )
            league.set_logger(self.log)
            
            if not player_config.summoner_info or "accountInfo" not in player_config.summoner_info:
                self.log(f"No cached summoner info found for {player_name}", "ERROR")
                return
                
            summoner_id = player_config.summoner_info["accountInfo"]["id"]
            active_game = league.loop.run_until_complete(league._get_active_game(summoner_id))
            
            if not active_game or "gameId" not in active_game:
                self.log("No active game found", "ERROR")
                return
            
            # Verify League path exists
            if not os.path.exists(self.config.league_path):
                self.log(f"League path not found: {self.config.league_path}", "ERROR")
                return
            
            # Verify League executable exists
            league_exe = os.path.join(self.config.league_path, "League of Legends.exe")
            if not os.path.exists(league_exe):
                self.log(f"League executable not found at: {league_exe}", "ERROR")
                return
            
            # Déterminer la locale à partir de LeagueClientSettings.yaml si possible
            locale = self.get_league_locale(self.config.league_path)
            locale_param = f'"-Locale={locale}"' if locale else ""
            
            # Construct spectator command with all les arguments du .bat
            region_prefix = player_config.region.split('1')[0].lower()
            parent_dir = os.path.dirname(self.config.league_path)
            
            spectator_command = (
                f'cd /d "{self.config.league_path}" & '
                f'"League of Legends.exe" '
                f'"spectator spectator.{region_prefix}1.lol.pvp.net:8080 '
                f'{active_game["observers"]["encryptionKey"]} '
                f'{active_game["gameId"]} '
                f'{region_prefix.upper()}1" '
                f'-UseRads -GameBaseDir=.. {locale_param} -SkipBuild -EnableCrashpad=true -EnableLNP'
            )
            
            self.log("Launching spectator client with command:", "INFO")
            self.log(spectator_command, "INFO")
            
            # Launch spectator
            try:
                process = subprocess.Popen(spectator_command, shell=True, 
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Check for immediate errors
                stdout, stderr = process.communicate(timeout=1)
                if stderr:
                    self.log(f"Spectator process error: {stderr.decode()}", "ERROR")
                    return
                    
            except subprocess.TimeoutExpired:
                pass  # Expected - means process is running
            except Exception as e:
                self.log(f"Error launching spectator: {str(e)}", "ERROR")
                return
            
            # Wait for game process to start
            start_time = time.time()
            game_started = False
            
            while time.time() - start_time < 45:
                if self.is_league_game_running():
                    game_started = True
                    break
                time.sleep(1)
            
            if not game_started:
                self.log("League game process not found after wait", "ERROR")
                return
            
            # Wait for game to initialize
            start_time = time.time()
            game_ready = False
            
            while time.time() - start_time < 60:  # Increased from 30 to 60 seconds
                time.sleep(5)
                if not self.requires_game_restart():
                    game_ready = True
                    break
            
            if not game_ready:
                self.log("Game failed to initialize properly", "ERROR")
                self.kill_league_game()
                return
            
            # Set streaming state and focus camera
            self.isStreaming = True
            self.active_stream = (player_name, player_config.channel_name)
            
            # Wait for game API to be fully ready
            self.log("Waiting for game API to initialize...", "INFO")
            start_time = time.time()
            api_ready = False
            
            while time.time() - start_time < 30:
                try:
                    url = "https://127.0.0.1:2999/liveclientdata/playerlist"
                    resp = r.get(url, timeout=2, verify=False).json()
                    if isinstance(resp, list) and len(resp) > 0:
                        api_ready = True
                        break
                except:
                    pass
                time.sleep(2)
            
            if not api_ready:
                self.log("Game API failed to initialize", "ERROR")
                self.kill_league_game()
                return
                
            # Give the API an extra moment to stabilize
            time.sleep(3)
            
            # Focus camera on the player
            game_name = player_config.summoner_info["riotId"]["gameName"]
            self.focus_player_camera(game_name)
            
            self.log(f"Successfully spectating {player_name}'s game", "SUCCESS")
            
        except Exception as e:
            self.log(f"Error in start_streaming: {str(e)}", "ERROR")
            self.kill_league_game()

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


class GameCheckerThread(QThread):
    game_check_status = Signal(str, str)  # Signal to update status (message, level)
    show_error = Signal(str, str)  # Signal for showing error popups
    
    def __init__(self, service):
        try:
            super().__init__()
            self.service = service
            self.running = False
            self.loop = None
            self.last_error_time = 0  # To prevent spam of error messages
            
        except Exception as e:
            print(f"[CRITICAL] Error initializing GameCheckerThread: {str(e)}")
            try:
                if hasattr(self.service, 'log'):
                    self.service.log(f"Error initializing GameCheckerThread: {str(e)}", "ERROR")
            except:
                pass  # Ne rien faire si même cette tentative échoue

    def stop(self):
        """Stop the thread"""
        self.running = False
        if self.loop and not self.loop.is_closed():
            try:
                # Cancel all running tasks
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
            except Exception as e:
                self.service.log(f"Error cancelling tasks: {str(e)}", "ERROR")

    async def check_games(self) -> list[tuple[str, 'PlayerConfig']]:
        """Async method to check all configured players for active games"""
        if not self.service.running:
            return []
            
        first_player = True
        
        for player_name, config in self.service.config.players.items():
            if not config.enabled:
                continue
                
            try:
                if not first_player:
                    self.service.log("-" * 50, "INFO")
                first_player = False
                
                self.service.log(f"Checking for active game: {player_name} ({config.summoner_id})", "INFO")
                
                league = LeagueAPI(
                    api_key=self.service.config.riot_api_key,
                    region=config.region
                )
                league.set_logger(self.service.log)
                
                if not config.summoner_info or "accountInfo" not in config.summoner_info:
                    self.service.log(f"No cached summoner info found for {player_name}", "ERROR")
                    continue
                    
                encrypted_summoner_id = config.summoner_info["accountInfo"]["id"]
                game = await league._get_active_game(encrypted_summoner_id)
                
                if game and game.get("gameId"):
                    game_length = game.get("gameLength", 0)
                    # Check if game length is reasonable (between 1 and 90 minutes)
                    if 60 <= game_length <= 5400:  # 5400 seconds = 90 minutes
                        # Verify game mode is spectatable
                        if game.get("gameMode") in ["CLASSIC", "ARAM"]:  # Add other valid modes as needed
                            self.service.log(f"Found valid game for {player_name}", "INFO")
                            return [(player_name, config)]
                        else:
                            self.service.log(f"Game mode {game.get('gameMode')} is not spectatable", "INFO")
                    else:
                        self.service.log(f"Game length {game_length}s is outside valid range (60s-5400s)", "INFO")
                
                # Use response headers for rate limiting if available
                await asyncio.sleep(3)  # Default rate limit
                
            except Exception as e:
                error_msg = str(e)
                if "API Key expired" in error_msg:
                    self.show_error.emit(
                        "API Key Error",
                        "Your Riot API key has expired. Please update it in the settings."
                    )
                    self.service.running = False
                    break
                self.service.log(f"Error checking {player_name}: {error_msg}", "ERROR")
        
        if not first_player:
            self.service.log("-" * 50, "INFO")
                
        return []  # No valid games found

    def run(self):
        """Main thread loop"""
        try:
            self.running = True
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            CYCLE_DELAY = 35  # Delay between check cycles in seconds
            SPECTATOR_CHECK_DELAY = 5  # Delay between spectator status checks
            
            while self.running:
                try:
                    if self.service.is_league_game_running():
                        # If spectator is running, just monitor it
                        if not self.service.isStreaming:
                            self.service.isStreaming = True  # Mark as streaming to pause game checks
                        
                        # Just wait while spectator is running
                        self.loop.run_until_complete(asyncio.sleep(SPECTATOR_CHECK_DELAY))
                    else:
                        # No spectator running, do normal game checks
                        if self.service.isStreaming:
                            self.service.log("Spectator window closed, resuming game checks", "INFO")
                            self.service.isStreaming = False  # Allow game checks to resume
                            
                        # Normal game checking cycle
                        active_games = self.loop.run_until_complete(self.check_games())
                        
                        if active_games:
                            # Sort by priority
                            active_games.sort(key=lambda x: x[1].priority)
                            player_name, player_config = active_games[0]
                            
                            # Start spectating for this player
                            if not self.service.isStreaming:
                                self.service.start_streaming(player_name, player_config)
                                continue
                        else:
                            self.service.log(f"Waiting {CYCLE_DELAY} seconds until next check cycle...", "INFO")
                            self.service.log("-" * 50, "INFO")
                            self.loop.run_until_complete(asyncio.sleep(CYCLE_DELAY))
                            
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.service.log(f"Error in game checker loop: {str(e)}", "ERROR")
                    # Sleep a bit before retrying
                    if self.loop and not self.loop.is_closed():
                        self.loop.run_until_complete(asyncio.sleep(5))
                    
        except Exception as e:
            self.service.log(f"Critical error in game checker thread: {str(e)}", "ERROR")
            self.running = False
            
        # Cleanup
        try:
            if self.loop and not self.loop.is_closed():
                # Cancel all tasks
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
                
                try:
                    # Run the loop one final time to process cancellations
                    self.loop.run_until_complete(asyncio.sleep(0))
                    self.loop.close()
                except Exception as e:
                    self.service.log(f"Error cleaning up game checker thread: {str(e)}", "ERROR")
        except Exception as e:
            # Catch any exceptions in the outer try block
            self.service.log(f"Error during final cleanup: {str(e)}", "ERROR")

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