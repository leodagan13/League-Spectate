# league.py
from pantheon import pantheon
import asyncio
from typing import Optional, Dict, Any

class LeagueAPI:
    def __init__(self, api_key: str, region: str = "euw1"):
        self.region = region
        self.panth = pantheon.Pantheon(
            server=region,
            api_key=api_key,
            auto_retry=True
        )
        self.loop = asyncio.get_event_loop()
        self.log = print  # Default logger

    def set_logger(self, logger):
        """Set a custom logger function"""
        self.log = logger

    async def _get_active_game(self, summoner_id: str) -> Dict[str, Any]:
        """Get active game data for a summoner"""
        try:
            # First get the PUUID from summoner ID
            summoner_url = f"https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
            summoner_data = await self.panth.fetch(summoner_url)
            summoner = await summoner_data.json()
            
            if "puuid" not in summoner:
                self.log(f"Could not get PUUID for summoner ID: {summoner_id}", "ERROR")
                return {}
            
            puuid = summoner["puuid"]
            
            # Now get active game using PUUID
            data = await self.panth.fetch(
                (self.panth.BASE_URL_LOL + "spectator/v5/active-games/by-summoner/{puuid}")
                .format(server=self.region, puuid=puuid)
            )
            match = await data.json()
            
            if "status" in match and "message" in match["status"]:
                # This means there's no active game
                self.log(f"No active game found: {match['status']['message']}", "INFO")
                return {}
                
            if "gameId" not in match:
                self.log("Invalid game data received - no gameId found", "ERROR")
                return {}
                
            self.log(f"Found active game: Game ID={match['gameId']}", "INFO")
            return match
            
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                # This is normal - means no active game
                self.log("No active game found", "INFO")
                return {}
            self.log(f"Error getting active game: {error_msg}", "ERROR")
            return {}

    async def _get_summoner_stats(self, summoner_id: str) -> Dict[str, Any]:
        """Get ranked stats for a summoner"""
        try:
            data = await self.panth.get_league_position(summoner_id)
            for queue in data:
                if queue["queueType"] == "RANKED_SOLO_5x5":
                    return {
                        "rank": f"{queue['tier']} {queue['rank']}",
                        "lp": queue["leaguePoints"],
                        "wins": queue["wins"],
                        "losses": queue["losses"]
                    }
            return None
        except Exception as e:
            print(f"[DEBUG] Error getting summoner stats: {e}")
            return None

    def get_active_game(self, summoner_id: str) -> Dict[str, Any]:
        """Synchronous wrapper for getting active game"""
        return self.loop.run_until_complete(self._get_active_game(summoner_id))

    def get_summoner_stats(self, summoner_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for getting summoner stats"""
        return self.loop.run_until_complete(self._get_summoner_stats(summoner_id))

    def verify_api_key(self) -> bool:
        """Test if the API key is valid"""
        try:
            # Try to get the free champion rotation - this endpoint is lightweight
            url = f"https://{self.region}.api.riotgames.com/lol/platform/v3/champion-rotations"
            future = self.panth.fetch(url)
            
            try:
                response = self.loop.run_until_complete(future)
                data = self.loop.run_until_complete(response.json())
                return "freeChampionIds" in data
                
            except Exception as e:
                error_msg = str(e)
                if "403" in error_msg:
                    raise Exception("API Key is invalid or expired")
                elif "401" in error_msg:
                    raise Exception("Unauthorized API key")
                else:
                    raise Exception(f"API Error: {error_msg}")
                
        except Exception as e:
            print(f"[DEBUG] API Key verification error: {str(e)}")
            raise e  # Propagate the error instead of returning False

    async def _get_summoner_by_name(self, summoner_name: str) -> Dict[str, Any]:
        """Get summoner info by summoner name"""
        try:
            # Construct the API URL
            api_url = f"https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
            
            # Log the API call
            print(f"[DEBUG] Making API call to: {api_url}")
            
            data = await self.panth.fetch(api_url)
            summoner = await data.json()
            return summoner
        except Exception as e:
            print(f"[DEBUG] Error getting summoner by name: {e}")
            return None

    def get_summoner_by_name(self, summoner_name: str) -> Dict[str, Any]:
        """Synchronous wrapper for getting summoner by name"""
        try:
            result = self.loop.run_until_complete(self._get_summoner_by_name(summoner_name))
            if not result:
                raise Exception("Failed to get summoner data")
            return result
        except Exception as e:
            print(f"[DEBUG] Error in get_summoner_by_name: {str(e)}")
            raise e

    async def _get_summoner_by_riot_id(self, game_name: str, tag_line: str) -> Dict[str, Any]:
        """Get account info by Riot ID (name#tag format)"""
        try:
            # Map region to routing value
            routing = {
                'euw1': 'europe',
                'eun1': 'europe',
                'tr1': 'europe',
                'ru': 'europe',
                'na1': 'americas',
                'br1': 'americas',
                'la1': 'americas',
                'la2': 'americas',
                'kr': 'asia',
                'jp1': 'asia',
                'oc1': 'asia'
            }.get(self.region, 'europe')
            
            # Construct the API URL for Account-V1
            api_url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
            print(f"[DEBUG] Making Account-V1 API call to: {api_url}")
            
            # Get account info
            data = await self.panth.fetch(api_url)
            account = await data.json()
            
            if account and "puuid" in account:
                # Now get summoner by PUUID
                summoner_url = f"https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{account['puuid']}"
                print(f"[DEBUG] Making Summoner-V4 API call to: {summoner_url}")
                
                summoner_data = await self.panth.fetch(summoner_url)
                summoner = await summoner_data.json()
                
                # Combine the data
                summoner['riotId'] = {
                    'gameName': game_name,
                    'tagLine': tag_line,
                    'puuid': account['puuid']
                }
                return summoner
                
            return None
        except Exception as e:
            print(f"[DEBUG] Error getting account/summoner by Riot ID: {e}")
            return None

    def get_active_game_by_summoner(self, summoner_id: str) -> Dict[str, Any]:
        """Synchronous wrapper for getting active game"""
        try:
            # Parse Riot ID
            if "#" in summoner_id:
                game_name, tag_line = summoner_id.split("#")
                # Get account info using Riot ID
                summoner = self.loop.run_until_complete(self._get_summoner_by_riot_id(game_name, tag_line))
                if not summoner or "id" not in summoner:
                    self.log(f"Could not find summoner with Riot ID: {summoner_id}", "ERROR")
                    return {}
                summoner_id = summoner["id"]  # Use the encrypted summoner ID

            # Get active game using encrypted summoner ID
            game_info = self.loop.run_until_complete(self._get_active_game(summoner_id))
            
            if game_info:
                self.log(f"Found active game: Game ID={game_info.get('gameId')}", "INFO")
            
            return game_info
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg:
                raise Exception("API Key expired or invalid. Please update in settings.")
            self.log(f"Error getting active game: {error_msg}", "ERROR")
            return {}