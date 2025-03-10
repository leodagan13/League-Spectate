# ui/settings_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QFormLayout, QMessageBox, QFileDialog, QComboBox, QSpinBox)
from PySide6.QtCore import Qt
import asyncio
from pantheon import pantheon
from league import LeagueAPI as League
import os

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OBS Settings")
        self.config = config
        
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        # OBS Path
        self.obs_path_input = QLineEdit(self.config.obs_path)
        browse_obs_btn = QPushButton("Browse")
        browse_obs_btn.clicked.connect(self.browse_obs_path)
        
        obs_path_layout = QHBoxLayout()
        obs_path_layout.addWidget(self.obs_path_input)
        obs_path_layout.addWidget(browse_obs_btn)
        
        # League Path
        self.league_path_input = QLineEdit(self.config.league_path)
        browse_league_btn = QPushButton("Browse")
        browse_league_btn.clicked.connect(self.browse_league_path)
        
        league_path_layout = QHBoxLayout()
        league_path_layout.addWidget(self.league_path_input)
        league_path_layout.addWidget(browse_league_btn)
        
        # Other settings
        self.obs_host_input = QLineEdit(self.config.obs_host)
        self.obs_port_input = QSpinBox()
        self.obs_port_input.setRange(1, 65535)
        self.obs_port_input.setValue(self.config.obs_port)
        self.obs_password_input = QLineEdit(self.config.obs_password)
        self.riot_api_key_input = QLineEdit(self.config.riot_api_key)
        
        # Add to layout
        layout.addRow("OBS Path:", obs_path_layout)
        layout.addRow("League Path:", league_path_layout)
        layout.addRow("OBS Host:", self.obs_host_input)
        layout.addRow("OBS Port:", self.obs_port_input)
        layout.addRow("OBS Password:", self.obs_password_input)
        layout.addRow("Riot API Key:", self.riot_api_key_input)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
        
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def browse_obs_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OBS Executable",
            "",
            "Executables (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.obs_path_input.setText(file_path)

    def browse_league_path(self):
        """Browse for League of Legends Game directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select League of Legends Game Directory\n\n"
            "Please select the 'Game' folder containing 'League of Legends.exe'\n"
            "Typically located at: C:\\Riot Games\\League of Legends\\Game",
            os.path.dirname(self.league_path_input.text()) or "C:\\Riot Games\\League of Legends\\Game"
        )
        if path:
            # Verify the directory contains League of Legends.exe
            if os.path.exists(os.path.join(path, "League of Legends.exe")):
                self.league_path_input.setText(path)
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Directory",
                    "The selected directory does not contain 'League of Legends.exe'.\n\n"
                    "Please select the 'Game' folder inside your League of Legends installation directory."
                )

    def get_values(self):
        return {
            "obs_path": self.obs_path_input.text(),
            "obs_host": self.obs_host_input.text(),
            "obs_port": int(self.obs_port_input.text()),
            "obs_password": self.obs_password_input.text()
        }

    def test_connection(self):
        from obswebsocket import obsws
        try:
            ws = obsws(
                self.obs_host_input.text(),
                int(self.obs_port_input.text()),
                self.obs_password_input.text()
            )
            ws.connect()
            ws.disconnect()
            QMessageBox.information(self, "Success", "Successfully connected to OBS!")
        except Exception as e:
            QMessageBox.warning(self, "Connection Failed", f"Could not connect to OBS: {str(e)}")

    def test_api_key(self):
        """Test if the Riot API key is valid"""
        try:
            # Create a League instance with the new API key
            league = League(
                api_key=self.riot_api_key_input.text(),
                region="euw1"  # Use a default region for testing
            )
            
            # Try to fetch a test summoner - this will validate the API key
            response = league.verify_api_key()
            
            if response:
                QMessageBox.information(self, "Success", "API key is valid!")
                return True
            else:
                QMessageBox.warning(self, "Error", "Invalid API key")
                return False
            
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg:
                QMessageBox.warning(self, "Error", "Invalid API key (403 Forbidden)")
            elif "401" in error_msg:
                QMessageBox.warning(self, "Error", "Unauthorized API key (401)")
            else:
                QMessageBox.warning(self, "Error", f"Failed to validate API key: {error_msg}")
            return False

    def accept(self):
        """Save settings and close dialog"""
        self.config.obs_path = self.obs_path_input.text()
        self.config.obs_host = self.obs_host_input.text()
        self.config.obs_port = self.obs_port_input.value()
        self.config.obs_password = self.obs_password_input.text()
        self.config.riot_api_key = self.riot_api_key_input.text()
        self.config.league_path = self.league_path_input.text()
        
        self.config.save()
        QDialog.accept(self)