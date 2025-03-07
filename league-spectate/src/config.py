# config.py
import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any

@dataclass
class PlayerConfig:
    summoner_id: str
    stream_key: str
    channel_name: str
    region: str = "euw1"  # Add region with default
    priority: int = 0
    enabled: bool = True
    summoner_info: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        summoner_id: str,
        stream_key: str,
        channel_name: str,
        region: str,
        priority: int = 0,
        enabled: bool = True,
        summoner_info: Optional[Dict[str, Any]] = None
    ):
        self.summoner_id = summoner_id
        self.stream_key = stream_key
        self.channel_name = channel_name
        self.region = region
        self.priority = priority
        self.enabled = enabled
        self.summoner_info = summoner_info  # Store summoner info

    def to_dict(self):
        return {
            "summoner_id": self.summoner_id,
            "stream_key": self.stream_key,
            "channel_name": self.channel_name,
            "region": self.region,
            "priority": self.priority,
            "enabled": self.enabled,
            "summoner_info": self.summoner_info
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            summoner_id=data.get("summoner_id"),
            stream_key=data.get("stream_key"),
            channel_name=data.get("channel_name"),
            region=data.get("region"),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            summoner_info=data.get("summoner_info")
        )

class Config:
    def __init__(self):
        self.file_path = "settings.json"
        self.obs_path = ""
        self.obs_host = "localhost"
        self.obs_port = 4455
        self.obs_password = ""
        self.riot_api_key = ""
        self.league_path = "C:\\Riot Games\\League of Legends\\Game"  # Add default path
        self.players: Dict[str, PlayerConfig] = {}
        self.load()

    def add_player(self, name: str, summoner_id: str, stream_key: str, 
                   channel_name: str, region: str = "euw1", priority: int = 0,
                   summoner_info: Optional[Dict[str, Any]] = None):
        try:
            # Validate inputs
            if not name or not summoner_id or not stream_key or not channel_name:
                raise ValueError("All fields are required")
            
            # Create new player config
            self.players[name] = PlayerConfig(
                summoner_id=summoner_id,
                stream_key=stream_key,
                channel_name=channel_name,
                region=region,
                priority=priority,
                enabled=True,  # New players are enabled by default
                summoner_info=summoner_info  # Include summoner info
            )
            
            # Save changes
            self.save()
            return True
        
        except Exception as e:
            print(f"Error adding player: {str(e)}")
            raise e

    def remove_player(self, name: str):
        if name in self.players:
            del self.players[name]
            self.save()

    def get_player_by_summoner_id(self, summoner_id: str) -> Optional[tuple[str, PlayerConfig]]:
        for name, config in self.players.items():
            if config.summoner_id == summoner_id and config.enabled:
                return (name, config)
        return None

    def save(self):
        data = {
            "obs_path": self.obs_path,
            "obs_host": self.obs_host,
            "obs_port": self.obs_port,
            "obs_password": self.obs_password,
            "riot_api_key": self.riot_api_key,
            "league_path": self.league_path,  # Add to save
            "players": {
                name: {
                    "summoner_id": player.summoner_id,
                    "stream_key": player.stream_key,
                    "channel_name": player.channel_name,
                    "region": player.region,
                    "priority": player.priority,
                    "enabled": player.enabled,
                    "summoner_info": player.summoner_info
                }
                for name, player in self.players.items()
            }
        }
        
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    def load(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, "r") as f:
            data = json.load(f)
            
        self.obs_path = data.get("obs_path", "")
        self.obs_host = data.get("obs_host", "localhost")
        self.obs_port = data.get("obs_port", 4455)
        self.obs_password = data.get("obs_password", "")
        self.riot_api_key = data.get("riot_api_key", "")
        self.league_path = data.get("league_path", "C:\\Riot Games\\League of Legends\\Game")  # Load from settings
        
        self.players = {
            name: PlayerConfig(
                summoner_id=pdata["summoner_id"],
                stream_key=pdata["stream_key"],
                channel_name=pdata["channel_name"],
                region=pdata.get("region", "euw1"),
                priority=pdata.get("priority", 0),
                enabled=pdata.get("enabled", True),
                summoner_info=pdata.get("summoner_info")  # Load summoner info
            )
            for name, pdata in data.get("players", {}).items()
        }

    def to_dict(self):
        return {
            "obs_path": self.obs_path,
            "obs_host": self.obs_host,
            "obs_port": self.obs_port,
            "obs_password": self.obs_password,
            "players": {
                name: player.to_dict() 
                for name, player in self.players.items()
            }
        }

    def verify_obs_settings(self) -> bool:
        """Verify that all required settings are properly configured"""
        if not self.obs_path:
            return False
        if not self.obs_host:
            return False
        if not self.obs_port:
            return False
        if not self.riot_api_key:
            return False
        if not self.players:
            return False
        return True

    def get_validation_errors(self) -> list[str]:
        """Get a list of validation errors"""
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
        """Get a string representation of current OBS settings"""
        return (f"OBS Settings: Path={self.obs_path}, "
                f"Host={self.obs_host}, Port={self.obs_port}, "
                f"Password={self.obs_password}, "
                f"API Key={self.riot_api_key}")