# config.py
import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any

# Chemin absolu du fichier de configuration
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

@dataclass
class PlayerConfig:
    summoner_id: str
    stream_key: str
    channel_name: str
    region: str = "euw1"
    priority: int = 0
    enabled: bool = True
    summoner_info: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {
            "summoner_id": self.summoner_id,
            "stream_key": self.stream_key,
            "channel": self.channel_name,
            "region": self.region,
            "priority": self.priority,
            "enabled": self.enabled,
            "summoner_info": self.summoner_info
        }


class Config:
    def __init__(self):
        # Utilisation de la constante globale pour le chemin du fichier
        self.file_path = SETTINGS_FILE
        
        # Valeurs par défaut
        self.obs_path = ""
        self.obs_host = "localhost"
        self.obs_port = 4455
        self.obs_password = ""
        self.riot_api_key = ""
        self.league_path = "C:\\Riot Games\\League of Legends\\Game"
        self.players: Dict[str, PlayerConfig] = {}
        
        # Tenter de charger, mais sans erreur si impossible
        try:
            self.load()
        except Exception as e:
            print(f"Erreur de chargement: {e}")
            print("Utilisation des valeurs par défaut")

    def add_player(self, name: str, summoner_id: str, stream_key: str, 
                  channel_name: str, region: str = "euw1", priority: int = 0,
                  summoner_info: Optional[Dict[str, Any]] = None):
        self.players[name] = PlayerConfig(
            summoner_id=summoner_id,
            stream_key=stream_key,
            channel_name=channel_name,
            region=region,
            priority=priority,
            enabled=True,
            summoner_info=summoner_info
        )
        self.save()

    def remove_player(self, name: str):
        if name in self.players:
            del self.players[name]
            self.save()

    def get_player_by_summoner_id(self, summoner_id: str) -> Optional[tuple[str, PlayerConfig]]:
        for name, player in self.players.items():
            if player.summoner_id == summoner_id:
                return (name, player)
        return None
        
    def save(self):
        try:
            data = {
                "obs_path": self.obs_path,
                "obs_host": self.obs_host,
                "obs_port": self.obs_port,
                "obs_password": self.obs_password,
                "riot_api_key": self.riot_api_key,
                "league_path": self.league_path,
                "players": {
                    name: player.to_dict()
                    for name, player in self.players.items()
                }
            }
            
            # Créer le répertoire parent si nécessaire
            directory = os.path.dirname(self.file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Erreur de sauvegarde: {e}")
            return False

    def load(self):
        try:
            if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.obs_path = data.get("obs_path", self.obs_path)
                self.obs_host = data.get("obs_host", self.obs_host)
                self.obs_port = data.get("obs_port", self.obs_port)
                self.obs_password = data.get("obs_password", self.obs_password)
                self.riot_api_key = data.get("riot_api_key", self.riot_api_key)
                self.league_path = data.get("league_path", self.league_path)
                
                self.players = {}
                for name, player_data in data.get("players", {}).items():
                    self.players[name] = PlayerConfig(
                        summoner_id=player_data.get("summoner_id", ""),
                        stream_key=player_data.get("stream_key", ""),
                        channel_name=player_data.get("channel", ""),
                        region=player_data.get("region", "euw1"),
                        priority=player_data.get("priority", 0),
                        enabled=player_data.get("enabled", True),
                        summoner_info=player_data.get("summoner_info")
                    )
                
                return True
            return False
        except Exception as e:
            print(f"Erreur lors du chargement: {e}")
            return False

    def to_dict(self):
        return {
            "obs_path": self.obs_path,
            "obs_host": self.obs_host,
            "obs_port": self.obs_port,
            "obs_password": self.obs_password,
            "riot_api_key": self.riot_api_key,
            "league_path": self.league_path,
            "players": {
                name: player.to_dict() 
                for name, player in self.players.items()
            }
        }

    def verify_obs_settings(self) -> bool:
        return (self.obs_path and self.obs_host and 
                self.obs_port and self.riot_api_key and self.players)

    def get_validation_errors(self) -> list[str]:
        errors = []
        if not self.obs_path:
            errors.append("OBS path not configured")
        if not self.obs_host:
            errors.append("OBS host not configured")
        if not self.obs_port:
            errors.append("OBS port not configured")
        if not self.riot_api_key:
            errors.append("Riot API key not configured")
        if not self.players:
            errors.append("No players configured")
        return errors

    def get_obs_settings_str(self) -> str:
        return (f"OBS Settings: Path={self.obs_path}, "
                f"Host={self.obs_host}, Port={self.obs_port}, "
                f"Password={self.obs_password}, "
                f"API Key={self.riot_api_key}")