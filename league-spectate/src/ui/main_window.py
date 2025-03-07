from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                              QDialog, QLineEdit, QFormLayout, QSpinBox,
                              QMessageBox, QFrame, QApplication, QTextEdit, QSplitter, QComboBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QTextCursor
from typing import Optional
from datetime import datetime
import asyncio
from league import LeagueAPI
from config import PlayerConfig

# Modern UI Components
class ModernButton(QPushButton):
    def __init__(self, text, icon_name=None, is_destructive=False):
        super().__init__(text)
        self.setMinimumHeight(36)
        self.setFont(QFont("Segoe UI", 9))
        
        # Modern flat style with hover effects
        base_color = "#dc2626" if is_destructive else "#2563eb"
        hover_color = "#b91c1c" if is_destructive else "#1d4ed8"
        pressed_color = "#991b1b" if is_destructive else "#1e40af"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:disabled {{
                background-color: #9ca3af;
            }}
        """)
        
        if icon_name:
            self.setIcon(QIcon(f"assets/icons/{icon_name}"))

class ModernTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setMinimumSectionSize(120)  # Minimum column width
        self.setMinimumHeight(200)  # Minimum height
        
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                selection-background-color: #e5e7eb;
                selection-color: black;
                gridline-color: #e5e7eb;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f3f4f6;
            }
            QTableWidget::item:selected {
                background-color: #f3f4f6;
            }
            QHeaderView::section {
                background-color: #f8f9fb;
                padding: 12px 16px;
                border: none;
                border-right: 1px solid #e5e7eb;
                border-bottom: 2px solid #e5e7eb;
                font-weight: 600;
                color: #374151;
                font-size: 13px;
                text-align: center;
            }
            QHeaderView::section:first {
                padding-left: 24px;
            }
            QTableWidget::item:hover {
                background-color: #f9fafb;
            }
        """)

class StatusCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("statusCard")
        self.setStyleSheet("""
            QFrame#statusCard {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("""
            color: #9ca3af;
            font-size: 24px;
        """)
        layout.addWidget(self.status_indicator)
        
        # Status text
        text_layout = QVBoxLayout()
        self.stream_status = QLabel("No active stream")
        self.stream_status.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #111827;
        """)
        
        self.status_detail = QLabel("Service stopped")
        self.status_detail.setStyleSheet("""
            font-size: 13px;
            color: #6b7280;
        """)
        
        text_layout.addWidget(self.stream_status)
        text_layout.addWidget(self.status_detail)
        layout.addLayout(text_layout)

        # Make the control button more prominent
        self.control_button = ModernButton("Start Service", "play")
        self.control_button.setFixedWidth(150)  # Made wider
        self.control_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: white;
            }
        """)
        layout.addWidget(self.control_button)

    def set_stopping(self):
        """Show stopping state"""
        self.status_indicator.setStyleSheet("color: #eab308; font-size: 24px;")  # Yellow
        self.stream_status.setText("Stopping service...")
        self.status_detail.setText("Please wait")
        self.status_detail.setStyleSheet("font-size: 13px; color: #eab308;")
        self.control_button.setEnabled(False)
        self.control_button.setText("Stopping...")

    def set_active(self, is_active: bool, stream_name: str = None):
        self.control_button.setEnabled(True)  # Re-enable button
        if is_active and stream_name:
            self.status_indicator.setStyleSheet("color: #22c55e; font-size: 24px;")
            self.stream_status.setText(f"Streaming: {stream_name}")
            self.status_detail.setText("Live")
            self.status_detail.setStyleSheet("font-size: 13px; color: #22c55e;")
            self.control_button.setText("Stop Service")
            self.control_button.setIcon(QIcon("assets/icons/stop"))
        else:
            self.status_indicator.setStyleSheet("color: #9ca3af; font-size: 24px;")
            self.stream_status.setText("No active stream")
            self.status_detail.setText("Service stopped")
            self.status_detail.setStyleSheet("font-size: 13px; color: #6b7280;")
            self.control_button.setText("Start Service")
            self.control_button.setIcon(QIcon("assets/icons/play"))

class ModernConsole(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("consoleFrame")
        self.setMinimumHeight(300)  # Increased from 150
        
        # Set frame styling
        self.setStyleSheet("""
            QFrame#consoleFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Remove spacing between elements
        
        # Header
        header = QLabel("Console")
        header.setStyleSheet("""
            background-color: #f8f9fb;
            padding: 12px 16px;
            border-bottom: 1px solid #e5e7eb;
            font-weight: 600;
            color: #374151;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        layout.addWidget(header)
        
        # Console output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(100)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: none;
                padding: 8px 12px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f5f9;
                width: 12px;
                border-radius: 6px;
                margin: 12px 4px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.console.setTextInteractionFlags(
            Qt.TextSelectableByMouse | 
            Qt.TextSelectableByKeyboard
        )
        layout.addWidget(self.console)
        
        # Footer with clear button
        footer = QFrame()
        footer.setStyleSheet("""
            background-color: #f8f9fb;
            border-top: 1px solid #e5e7eb;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        
        clear_btn = ModernButton("Clear Console", is_destructive=True)
        clear_btn.clicked.connect(self.clear)
        clear_btn.setFixedWidth(120)
        
        footer_layout.addStretch()
        footer_layout.addWidget(clear_btn)
        layout.addWidget(footer)

    def log(self, message: str, level: str = "INFO"):
        """Add a message to the console with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Define message type colors
        if "API response" in message:
            color = "#0891b2"  # Cyan for API responses
        elif "No active game found" in message:
            color = "#6366f1"  # Indigo for no game found
        elif "Checking for active game" in message:
            color = "#8b5cf6"  # Purple for checking games
        elif "Waiting" in message:
            color = "#a855f7"  # Pink for waiting messages
        elif "No active games found" in message:
            color = "#6366f1"  # Indigo for no games found
        else:
            # Default colors based on level
            color = {
                "INFO": "#374151",    # Gray
                "ERROR": "#dc2626",   # Red
                "WARNING": "#d97706",  # Orange
                "SUCCESS": "#059669"   # Green
            }.get(level, "#374151")
        
        self.console.moveCursor(QTextCursor.End)
        self.console.insertHtml(
            f'<div style="margin: 4px 0; line-height: 1.5;">'
            f'<span style="color: #6b7280; font-family: Consolas, monospace;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-family: Consolas, monospace;">{message}</span>'
            f'</div><br>'
        )
        self.console.moveCursor(QTextCursor.End)
        
        # Ensure the latest message is visible
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )

    def clear(self):
        """Clear the console"""
        self.console.clear()

class AddPlayerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Player")
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)

        # Input fields
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter player name")
        
        self.summoner_input = QLineEdit()
        self.summoner_input.setPlaceholderText("Enter Riot ID (e.g. Name#TAG)")  # Updated placeholder
        
        self.stream_key_input = QLineEdit()
        self.stream_key_input.setPlaceholderText("Enter stream key")
        
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Enter channel name")
        
        self.priority_input = QSpinBox()
        self.priority_input.setRange(0, 100)
        
        # Add region dropdown
        self.region_input = QComboBox()
        self.region_input.addItems([
            "euw1",  # Europe West
            "na1",   # North America
            "kr",    # Korea
            "eun1",  # Europe Nordic & East
            "br1",   # Brazil
            "jp1",   # Japan
            "la1",   # Latin America North
            "la2",   # Latin America South
            "oc1",   # Oceania
            "tr1",   # Turkey
            "ru"     # Russia
        ])

        # Add fields to layout
        layout.addRow("Player Name:", self.name_input)
        layout.addRow("Region:", self.region_input)  # Add region field
        layout.addRow("Summoner ID:", self.summoner_input)
        layout.addRow("Stream Key:", self.stream_key_input)
        layout.addRow("Channel Name:", self.channel_input)
        layout.addRow("Priority (0=highest):", self.priority_input)

        # Buttons
        buttons = QHBoxLayout()
        save_btn = ModernButton("Save")
        cancel_btn = ModernButton("Cancel", is_destructive=True)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_values(self):
        return {
            "name": self.name_input.text(),
            "summoner_id": self.summoner_input.text(),
            "stream_key": self.stream_key_input.text(),
            "channel_name": self.channel_input.text(),
            "priority": self.priority_input.value(),
            "region": self.region_input.currentText()  # Add region to values
        }

    def accept(self):
        if not self.parent().config.riot_api_key:
            QMessageBox.warning(
                self,
                "Error",
                "No API key configured. Please add your Riot API key in Settings first."
            )
            return

        try:
            values = self.get_values()
            
            # Parse Riot ID
            riot_id = values["summoner_id"]
            if "#" not in riot_id:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Please enter a valid Riot ID in the format Name#TAG"
                )
                return
            
            game_name, tag_line = riot_id.split("#")
            
            # Create League instance
            league = LeagueAPI(
                api_key=self.parent().config.riot_api_key,
                region=values["region"]
            )
            
            self.parent().console.log(f"Looking up Riot ID: {game_name}#{tag_line}", "INFO")
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Get account info using Riot ID
                summoner = loop.run_until_complete(league._get_summoner_by_riot_id(game_name, tag_line))
                
                if summoner and "id" in summoner:
                    # Log the raw API response for debugging
                    self.parent().console.log(f"Raw API Response: {summoner}", "INFO")
                    
                    # Get ranked stats
                    summoner_stats = loop.run_until_complete(league._get_summoner_stats(summoner["id"]))
                    loop.close()
                    
                    # Create the complete summoner info object
                    summoner_info = {
                        "accountInfo": summoner,
                        "stats": summoner_stats,
                        "riotId": {
                            "gameName": game_name,
                            "tagLine": tag_line,
                            "region": values["region"]
                        }
                    }
                    
                    # Log the structured data we're about to save
                    self.parent().console.log(f"Storing summoner info: {summoner_info}", "INFO")
                    
                    # Add player to config with summoner info
                    self.parent().config.add_player(
                        name=values["name"],
                        summoner_id=f"{game_name}#{tag_line}",
                        stream_key=values["stream_key"],
                        channel_name=values["channel_name"],
                        region=values["region"],
                        priority=values["priority"],
                        summoner_info=summoner_info  # Pass the summoner info
                    )
                    
                    # Verify the data was stored
                    self.parent().console.log(
                        f"Saved player data: {self.parent().config.players[values['name']].__dict__}", 
                        "INFO"
                    )
                    
                    self.parent().console.log(f"Successfully added player: {values['name']}", "SUCCESS")
                    QDialog.accept(self)
                    return
                    
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Could not find account with that Riot ID. Please check the spelling and region."
                    )
                    
            except Exception as e:
                error_msg = str(e)
                self.parent().console.log(f"Error: {error_msg}", "ERROR")
                QMessageBox.warning(self, "Error", str(e))
                
        except Exception as e:
            self.parent().console.log(f"Unexpected error: {str(e)}", "ERROR")
            QMessageBox.warning(
                self,
                "Error",
                f"An unexpected error occurred: {str(e)}"
            )

class MainWindow(QMainWindow):
    def __init__(self, config, service):
        super().__init__()
        self.config = config
        self.service = service
        self.service.set_log_callback(self.log_message)
        self.is_running = False
        self.setup_ui()
        
        # Update timer for status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)

    def setup_ui(self):
        self.setWindowTitle("League Stream Manager")
        self.setMinimumSize(1200, 700)
        
        # Set application-wide style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f9fafb;
            }
            QSplitter::handle {
                background-color: #e5e7eb;
                margin: 1px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(24)
        layout.setContentsMargins(24, 24, 24, 24)

        # Top section with status and buttons
        top_section = QHBoxLayout()
        
        # Status card
        self.status_card = StatusCard()
        self.status_card.control_button.clicked.connect(self.toggle_service)
        top_section.addWidget(self.status_card, stretch=1)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        add_player_btn = ModernButton("Add Player", "plus")
        add_player_btn.clicked.connect(self.add_player)
        
        settings_btn = ModernButton("Settings", "settings")
        settings_btn.clicked.connect(self.show_obs_settings)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #4b5563;
                border: 1px solid #e5e7eb;
            }
            QPushButton:hover {
                background-color: #f9fafb;
            }
            QPushButton:pressed {
                background-color: #f3f4f6;
            }
        """)
        
        button_layout.addWidget(add_player_btn)
        button_layout.addWidget(settings_btn)
        top_section.addLayout(button_layout)
        
        layout.addLayout(top_section)

        # Create a splitter for table and console
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)  # Prevent complete collapse
        layout.addWidget(splitter)

        # Add table to splitter
        self.players_table = ModernTableWidget()
        self.players_table.setColumnCount(6)
        self.players_table.setHorizontalHeaderLabels([
            "PLAYER NAME", "CHANNEL", "PRIORITY", "STREAMING", "ACTIVE", "ACTIONS"
        ])
        self.players_table.horizontalHeader().setStretchLastSection(True)
        
        # Set column widths
        self.players_table.setColumnWidth(0, 250)  # Name - increased width
        self.players_table.setColumnWidth(1, 250)  # Channel - increased width
        self.players_table.setColumnWidth(2, 120)  # Priority
        self.players_table.setColumnWidth(3, 120)  # Streaming
        self.players_table.setColumnWidth(4, 120)  # Active
        self.players_table.setColumnWidth(5, 250)  # Actions - increased width
        
        splitter.addWidget(self.players_table)
        self.update_players_table()

        # Add console to splitter
        self.console = ModernConsole()
        splitter.addWidget(self.console)

        # Set initial sizes (60% table, 40% console)
        splitter.setSizes([600, 400])  # Changed from [700, 300]

    def create_table_button(self, text, is_destructive=False):
        btn = ModernButton(text, is_destructive=is_destructive)
        btn.setFixedSize(120, 32)  # Increased button width
        return btn

    def update_players_table(self):
        self.players_table.setRowCount(len(self.config.players))
        
        # If there are no players, return early
        if not self.config.players:
            return
        
        for row, (name, player) in enumerate(self.config.players.items()):
            # Set row height at the start of each iteration
            self.players_table.setRowHeight(row, 60)
            
            # Create items with modern styling and left alignment
            for col, value in enumerate([
                name, 
                player.channel_name,
                str(player.priority)
            ]):
                item = QTableWidgetItem(value)
                item.setFont(QFont("Segoe UI", 9))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Left align text
                self.players_table.setItem(row, col, item)
            
            # Status with modern badge style
            status = "Streaming" if self.service.is_player_streaming(name) else "Idle"
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(4, 4, 4, 4)
            
            status_label = QLabel(status)
            status_label.setStyleSheet(f"""
                background-color: {('#dcfce7' if status == 'Streaming' else '#f3f4f6')};
                color: {('#15803d' if status == 'Streaming' else '#4b5563')};
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
            """)
            status_layout.addWidget(status_label)
            status_layout.addStretch()
            self.players_table.setCellWidget(row, 3, status_widget)
            
            # Active toggle button
            active_widget = QWidget()
            active_layout = QHBoxLayout(active_widget)
            active_layout.setContentsMargins(4, 4, 4, 4)
            
            # Create a function that captures the current name and enabled state
            def create_toggle_handler(player_name, enabled):
                return lambda checked: self.toggle_player(player_name, not enabled)
            
            active_btn = self.create_table_button(
                "Active" if player.enabled else "Inactive",
                is_destructive=not player.enabled
            )
            active_btn.clicked.connect(create_toggle_handler(name, player.enabled))
            active_layout.addWidget(active_btn)
            active_layout.addStretch()
            self.players_table.setCellWidget(row, 4, active_widget)
            
            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(8)
            
            # Create functions that capture the current name
            def create_edit_handler(player_name):
                return lambda: self.edit_player(player_name)
            
            def create_delete_handler(player_name):
                return lambda: self.delete_player(player_name)
            
            edit_btn = self.create_table_button("Edit")
            edit_btn.clicked.connect(create_edit_handler(name))
            
            delete_btn = self.create_table_button("Delete", is_destructive=True)
            delete_btn.clicked.connect(create_delete_handler(name))
            
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            action_layout.addStretch()
            
            self.players_table.setCellWidget(row, 5, action_widget)

    def log_message(self, message: str, level: str = "INFO"):
        """Callback for service logging"""
        self.console.log(message, level)

    def toggle_service(self):
        if not self.is_running:
            # Check all requirements before starting
            validation_errors = self.config.get_validation_errors()
            
            # Check if there are any enabled players
            enabled_players = [name for name, player in self.config.players.items() if player.enabled]
            if not enabled_players:
                validation_errors.append("No enabled players found. Please enable at least one player.")
            
            if validation_errors:
                error_message = "Cannot start service:\n\n" + "\n".join(f"• {error}" for error in validation_errors)
                self.console.log("Service start failed: Missing requirements", "ERROR")
                for error in validation_errors:
                    self.console.log(f"- {error}", "ERROR")
                
                QMessageBox.warning(
                    self,
                    "Configuration Error",
                    error_message
                )
                return
            
            try:
                if self.service.start():  # Only proceed if service actually started
                    self.is_running = True
                    self.status_timer.start(5000)
                    self.status_card.status_detail.setText("Searching for active games...")
                    self.status_card.control_button.setText("Stop Service")
                    self.status_card.control_button.setIcon(QIcon("assets/icons/stop"))
            except Exception as e:
                self.console.log(f"Failed to start service: {str(e)}", "ERROR")
                self.is_running = False
        else:
            # Show stopping state
            self.status_card.set_stopping()
            self.console.log("Stopping service...", "INFO")
            
            try:
                # Use QTimer to add a small delay for visual feedback
                QTimer.singleShot(500, self._complete_stop)
            except Exception as e:
                self.console.log(f"Error stopping service: {str(e)}", "ERROR")
                self.status_card.set_active(False)  # Reset to stopped state

    def _complete_stop(self):
        """Complete the service stop operation"""
        try:
            self.service.stop()
            self.is_running = False
            self.status_timer.stop()
            self.status_card.set_active(False)
            self.console.log("Service stopped successfully", "SUCCESS")
        except Exception as e:
            self.console.log(f"Error stopping service: {str(e)}", "ERROR")
            self.status_card.set_active(False)  # Reset to stopped state

    def update_status(self):
        if not self.is_running:
            self.status_card.set_active(False)
            return

        if self.service.active_stream:
            name, channel = self.service.active_stream
            self.status_card.set_active(True, f"{name} on {channel}")
        else:
            self.status_card.status_detail.setText("Searching for active games...")
            self.status_card.status_indicator.setStyleSheet("color: #9ca3af; font-size: 24px;")
            self.status_card.stream_status.setText("No active stream")
        
        self.update_players_table()

    def add_player(self):
        dialog = AddPlayerDialog(self)
        if dialog.exec():
            # The dialog's accept method already handles adding the player with summoner info
            self.update_players_table()

    def edit_player(self, name):
        dialog = AddPlayerDialog(self)
        player = self.config.players[name]
        
        # Pre-fill existing values
        dialog.name_input.setText(name)
        dialog.summoner_input.setText(player.summoner_id)
        dialog.stream_key_input.setText(player.stream_key)
        dialog.channel_input.setText(player.channel_name)
        dialog.priority_input.setValue(player.priority)
        dialog.region_input.setCurrentText(player.region)
        
        if dialog.exec():
            values = dialog.get_values()
            # Remove old entry and add new one if name changed
            if values["name"] != name:
                self.config.remove_player(name)
            # Preserve summoner_info when editing
            self.config.add_player(
                **values,
                summoner_info=player.summoner_info
            )
            self.update_players_table()

    def delete_player(self, name):
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            self.config.remove_player(name)
            self.update_players_table()

    def toggle_player(self, name, state):
        self.config.players[name].enabled = state
        self.config.save()
        self.update_players_table()

    def show_obs_settings(self):
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.console.log("Settings saved successfully", "SUCCESS")
            self.console.log(self.config.get_obs_settings_str(), "INFO")
            
            # Reconnect OBS if service is running
            if self.is_running:
                try:
                    self.service.connect_obs()
                    self.console.log("Reconnected to OBS with new settings", "SUCCESS")
                except Exception as e:
                    self.console.log(f"Failed to reconnect to OBS: {str(e)}", "ERROR")