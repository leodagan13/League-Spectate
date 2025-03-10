import os
import subprocess
import psutil
import time
from obswebsocket import obsws, requests
from typing import Callable

class OBSManager:
    def __init__(self, obs_path: str, obs_host: str, obs_port: int, obs_password: str, log_callback: Callable = print):
        self.obs_path = obs_path
        self.obs_host = obs_host
        self.obs_port = obs_port
        self.obs_password = obs_password
        self.obs = None
        self.log = log_callback

    def is_obs_running(self) -> bool:
        """Check if OBS is running"""
        try:
            return "obs64.exe" in (p.name() for p in psutil.process_iter())
        except:
            return False

    def launch_obs(self):
        """Launch OBS"""
        if not os.path.exists(self.obs_path):
            raise Exception("OBS path not found")
            
        try:
            # Get OBS directory from the executable path
            obs_dir = os.path.dirname(self.obs_path)
            
            # Store current directory
            current_dir = os.getcwd()
            
            try:
                # Change to OBS directory before launching
                os.chdir(obs_dir)
                subprocess.Popen([self.obs_path])
                self.log("Launching OBS...", "INFO")
            finally:
                # Change back to original directory
                os.chdir(current_dir)
            
            # Wait for OBS to start
            for _ in range(10):  # Wait up to 10 seconds
                if self.is_obs_running():
                    self.log("OBS launched successfully", "SUCCESS")
                    time.sleep(2)  # Give OBS a moment to fully initialize
                    return
                time.sleep(1)
                
            raise Exception("OBS failed to start within timeout")
        except Exception as e:
            raise Exception(f"Failed to launch OBS: {str(e)}")

    def connect(self):
        """Connect to OBS websocket"""
        try:
            # Create OBS websocket connection
            self.obs = obsws(
                host=self.obs_host,
                port=self.obs_port,
                password=self.obs_password,
                timeout=3
            )
            self.obs.connect()
            self.log("Connected to OBS successfully", "SUCCESS")
        except Exception as e:
            raise Exception(f"Failed to connect to OBS: {str(e)}")

    def disconnect(self):
        """Disconnect from OBS websocket"""
        try:
            if self.obs:
                self.obs.disconnect()
                self.obs = None
                self.log("Disconnected from OBS", "INFO")
        except Exception as e:
            self.log(f"Error disconnecting from OBS: {str(e)}", "ERROR") 