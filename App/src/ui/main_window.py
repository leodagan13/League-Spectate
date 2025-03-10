from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                              QDialog, QLineEdit, QFormLayout, QSpinBox,
                              QMessageBox, QFrame, QApplication, QTextEdit, QSplitter, QComboBox, QHeaderView, QToolButton, QMenu,
                              QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QTextCursor, QPainter, QAction, QPixmap
from typing import Optional
from datetime import datetime
import asyncio
from league import LeagueAPI
from config import PlayerConfig
import os
import hashlib

# Modern UI Components
class ModernButton(QPushButton):
    def __init__(self, text, icon_name=None, is_destructive=False):
        super().__init__(text)
        self.setMinimumHeight(32)  # Hauteur réduite pour mieux s'adapter
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        
        # Couleurs plus modernes
        if is_destructive:
            base_color = "#ef4444"  # Rouge vif
            hover_color = "#dc2626"  # Rouge plus foncé
            pressed_color = "#b91c1c"  # Rouge encore plus foncé
        else:
            base_color = "#3b82f6"  # Bleu vif
            hover_color = "#2563eb"  # Bleu plus foncé
            pressed_color = "#1d4ed8"  # Bleu encore plus foncé
            
        # Appliquer un effet d'ombre plus léger
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(6)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)
            
        # Style normalisé avec moins de padding et des bords moins arrondis
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:disabled {{
                background-color: #d1d5db;
                color: #9ca3af;
            }}
        """)
        
        # Ajouter une icône si spécifiée, avec taille réduite
        if icon_name:
            icon_path = os.path.join("App", "assets", "icons", f"{icon_name}.svg")
            if os.path.exists(icon_path):
                self.setIcon(QIcon(icon_path))
                self.setIconSize(QSize(16, 16))
        
    def setSuccess(self):
        """Set button to success state"""
        self.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 120px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
                box-shadow: none;
            }
        """)
        
    def setWarning(self):
        """Set button to warning state"""
        self.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 120px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover {
                background-color: #d97706;
            }
            QPushButton:pressed {
                background-color: #b45309;
                box-shadow: none;
            }
        """)

# Modern Switch Widget (style toggle button)
class ModernSwitch(QWidget):
    toggled = Signal(bool)
    
    def __init__(self, parent=None, is_on=False):
        super().__init__(parent)
        self.is_on = is_on
        self.setFixedSize(36, 20)
        
        # Track animation progress
        self.animation_progress = 1.0 if is_on else 0.0
        self.animation_active = False
        self.animation_direction = 0  # 1 = to ON, -1 = to OFF
        
        # Setup timer for smooth animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        
        # Enable mouse tracking
        self.setCursor(Qt.PointingHandCursor)
        
    def update_animation(self):
        # Update animation progress
        animation_speed = 0.2  # Animation step size
        if self.animation_direction > 0:
            self.animation_progress += animation_speed
            if self.animation_progress >= 1.0:
                self.animation_progress = 1.0
                self.timer.stop()
                self.animation_active = False
        else:
            self.animation_progress -= animation_speed
            if self.animation_progress <= 0.0:
                self.animation_progress = 0.0
                self.timer.stop()
                self.animation_active = False
        
        # Trigger repaint
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        track_color = QColor(47, 133, 90) if self.is_on else QColor(155, 155, 155)
        thumb_color = QColor(255, 255, 255)
        
        # Draw track
        track_opacity = 0.6 if not self.is_on else 0.8  # Lower opacity when off
        painter.setBrush(QColor(track_color.red(), track_color.green(), track_color.blue(), 
                              int(255 * track_opacity)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        
        # Draw thumb based on animation progress
        thumb_size = 16
        thumb_margin = 2
        thumb_x = thumb_margin + (self.width() - thumb_size - 2 * thumb_margin) * self.animation_progress
        
        # Draw drop shadow
        shadow_color = QColor(0, 0, 0, 30)
        for i in range(1, 4):
            painter.setBrush(shadow_color)
            painter.drawEllipse(int(thumb_x) - i, thumb_margin - i + 1, thumb_size + i*2, thumb_size + i*2)
        
        # Draw thumb
        painter.setBrush(thumb_color)
        painter.drawEllipse(int(thumb_x), thumb_margin, thumb_size, thumb_size)
    
    def mousePressEvent(self, event):
        self.toggle()
        
    def toggle(self):
        # Toggle state
        self.is_on = not self.is_on
        
        # Start animation
        self.animation_active = True
        self.animation_direction = 1 if self.is_on else -1
        if not self.timer.isActive():
            self.timer.start(16)  # ~60 FPS
        
        # Emit signal
        self.toggled.emit(self.is_on)
    
    def setChecked(self, checked):
        if self.is_on != checked:
            self.is_on = checked
            self.animation_progress = 1.0 if checked else 0.0
            self.update()

class ModernTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False)
        
        # Appliquer un effet d'ombre
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        
        # Appliquer un style moderne
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0px;
                alternate-background-color: #f9fafb;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e5e7eb;
            }
            QTableWidget::item:selected {
                background-color: #e5e7eb;
                color: black;
            }
            QHeaderView::section {
                background-color: #f3f4f6;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #d1d5db;
                font-weight: bold;
            }
            QScrollBar:vertical {
                border: none;
                background: #f3f4f6;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #d1d5db;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
        """)

class StatusCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("status_card")
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)
        
        # Style avec des bords arrondis sur tous les côtés pour l'effet de puce
        self.setStyleSheet("""
            #status_card {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)
        
        # Info panel - left side
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)  # Réduire l'espacement
        
        # Title with status icon
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(12, 12)  # Réduire la taille de l'icône
        title_layout.addWidget(self.status_icon)
        
        self.title_label = QLabel("League Spectate")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        info_layout.addLayout(title_layout)
        
        # Status message
        self.status_msg = QLabel("Service not running")
        self.status_msg.setStyleSheet("color: #4b5563; font-size: 12px;")
        info_layout.addWidget(self.status_msg)
        
        # Add info to main layout
        layout.addLayout(info_layout)
        
        # Right side with player info when streaming
        self.streaming_info = QWidget()
        streaming_layout = QVBoxLayout(self.streaming_info)
        streaming_layout.setContentsMargins(0, 0, 0, 0)
        streaming_layout.setSpacing(4)  # Réduire l'espacement
        
        self.stream_title = QLabel("Currently streaming:")
        self.stream_title.setStyleSheet("font-size: 12px; color: #4b5563;")
        streaming_layout.addWidget(self.stream_title)
        
        self.stream_player = QLabel("No player")
        self.stream_player.setStyleSheet("font-weight: bold; font-size: 14px;")
        streaming_layout.addWidget(self.stream_player)
        
        # Hide by default
        self.streaming_info.setVisible(False)
        
        layout.addWidget(self.streaming_info)
        layout.addStretch()
        
        # Set inactive by default
        self.set_active(False)

    def _create_status_icon(self, color):
        """Crée une icône circulaire de couleur"""
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
        
        return pixmap

    def set_stopping(self):
        """Show stopping state"""
        self.status_icon.setPixmap(self._create_status_icon("#facc15"))  # Jaune
        self.status_msg.setText("Stopping service...")

    def set_active(self, is_active: bool, stream_name: str = None):
        if is_active:
            self.status_icon.setPixmap(self._create_status_icon("#10b981"))  # Vert
            if stream_name:
                self.stream_player.setText(stream_name)
                self.streaming_info.setVisible(True)
                self.status_msg.setText("Stream active")
            else:
                self.stream_player.setText("Waiting for match")
                self.streaming_info.setVisible(False)
                self.status_msg.setText("Service running")
        else:
            self.status_icon.setPixmap(self._create_status_icon("#9ca3af"))  # Gris
            self.streaming_info.setVisible(False)
            self.status_msg.setText("Service stopped")

class ModernConsole(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("modern_console")
        self.setMinimumHeight(200)
        
        # Créer un effet d'ombre
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        
        # Style de base avec des bords arrondis
        self.setStyleSheet("""
            #modern_console {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header with title and clear button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # Console title
        title_label = QLabel("Console")
        title_label.setStyleSheet("""
            color: #e5e7eb;
            font-size: 14px;
            font-weight: bold;
            padding-bottom: 4px;
        """)
        header_layout.addWidget(title_label)
        
        # Add stretch to push clear button to the right
        header_layout.addStretch()
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #e5e7eb;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:pressed {
                background-color: #6b7280;
            }
        """)
        self.clear_button.clicked.connect(self.clear)
        header_layout.addWidget(self.clear_button)
        
        layout.addLayout(header_layout)
        
        # Text area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #111827;
                color: #f9fafb;
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                line-height: 1.5;
                selection-background-color: #374151;
            }
            QScrollBar:vertical {
                border: none;
                background: #1f2937;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #4b5563;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0;
            }
        """)
        layout.addWidget(self.text_area)

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Définir les styles pour les différents niveaux de logs
        if level.upper() == "ERROR":
            color = "#ef4444"  # Rouge
            prefix = "❌ ERROR"
        elif level.upper() == "WARNING":
            color = "#f59e0b"  # Jaune/Orange
            prefix = "⚠️ WARNING"
        elif level.upper() == "SUCCESS":
            color = "#10b981"  # Vert émeraude
            prefix = "✅ SUCCESS"
        else:
            color = "#60a5fa"  # Bleu clair
            prefix = "ℹ️ INFO"
        
        # Formatter le message avec du HTML
        formatted_message = f'<span style="color:#9ca3af;">[{timestamp}]</span> <span style="color:{color};">{prefix}:</span> {message}<br>'
        
        # Ajouter le message à la console
        self.text_area.moveCursor(QTextCursor.End)
        self.text_area.insertHtml(formatted_message)
        self.text_area.moveCursor(QTextCursor.End)

    def clear(self):
        self.text_area.clear()

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
        
        self.update_players_table()
        # Update timer for status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)

    def setup_ui(self):
        """Set up the main window UI"""
        self.setWindowTitle("League Spectate")
        self.setMinimumSize(1000, 700)
        
        # Style global de l'application
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f9fafb;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                gridline-color: #f3f4f6;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QHeaderView::section {
                background-color: #f3f4f6;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #e5e7eb;
            }
            QSplitter::handle {
                background-color: #e5e7eb;
                margin: 2px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 3, 10, 5)  # Réduire légèrement le padding supérieur (5 -> 3)
        main_layout.setSpacing(2)
        
        # Section avec la StatusCard à gauche et les boutons à droite
        top_section = QWidget()
        top_section.setContentsMargins(0, 0, 0, 0)
        top_section_layout = QHBoxLayout(top_section)
        top_section_layout.setContentsMargins(0, 0, 0, 0)
        top_section_layout.setSpacing(10)
        
        # StatusCard positionnée en haut à gauche comme une puce
        self.status_card = StatusCard()
        # Limiter la largeur pour qu'elle ne prenne pas tout l'espace
        self.status_card.setMaximumWidth(300)
        top_section_layout.addWidget(self.status_card, 0, Qt.AlignLeft | Qt.AlignVCenter)  # Aligner verticalement au centre
        
        # Ajouter un espace extensible pour séparer StatusCard des boutons
        top_section_layout.addStretch(1)
        
        # Créer un conteneur pour les boutons bleus afin de les centrer ensemble
        blue_buttons_container = QWidget()
        blue_buttons_layout = QHBoxLayout(blue_buttons_container)
        blue_buttons_layout.setContentsMargins(0, 0, 0, 0)
        blue_buttons_layout.setSpacing(10)
        blue_buttons_layout.setAlignment(Qt.AlignCenter)  # Centrer les boutons dans le conteneur
        
        # Service toggle button
        self.toggle_button = ModernButton("Start Service", "play")
        self.toggle_button.clicked.connect(self.toggle_service)
        blue_buttons_layout.addWidget(self.toggle_button)
        
        # Bouton de sauvegarde explicite
        self.save_button = ModernButton("Sauvegarder", is_destructive=False)
        self.save_button.setToolTip("Sauvegarder tous les changements")
        self.save_button.clicked.connect(self.save_config)
        blue_buttons_layout.addWidget(self.save_button)
        
        # Add player button
        add_player_button = ModernButton("Ajouter un joueur", "plus")
        add_player_button.clicked.connect(self.add_player)
        blue_buttons_layout.addWidget(add_player_button)
        
        # Ajouter le conteneur des boutons bleus au layout principal
        top_section_layout.addWidget(blue_buttons_container, 4, Qt.AlignCenter | Qt.AlignVCenter)  # Aligner verticalement au centre
        
        # Ajouter un espace extensible après les boutons bleus
        top_section_layout.addStretch(1)
        
        # Petit espacement avant les boutons d'outils
        top_section_layout.addSpacing(5)
        
        # Settings button
        self.settings_button = QToolButton()
        self.settings_button.setIcon(QIcon(os.path.join("App", "assets", "icons", "settings.svg")))
        self.settings_button.setIconSize(QSize(22, 22))
        self.settings_button.setToolTip("OBS Settings")
        self.settings_button.setFixedSize(40, 40)
        self.settings_button.setStyleSheet("""
            QToolButton {
                background-color: #f3f4f6;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QToolButton:hover {
                background-color: #e5e7eb;
            }
        """)
        self.settings_button.clicked.connect(self.show_obs_settings)
        top_section_layout.addWidget(self.settings_button, 0, Qt.AlignVCenter)  # Aligner verticalement au centre
        
        # Test menu button (dropdown) - Modifier pour clarifier qu'il s'agit d'un menu déroulant
        self.test_menu_button = QToolButton()
        # Utiliser une icône différente ou générer une icône personnalisée pour indiquer un menu
        self.test_menu_button.setText("▼")  # Ajouter un triangle vers le bas pour indiquer un menu déroulant
        self.test_menu_button.setIconSize(QSize(16, 16))
        self.test_menu_button.setToolTip("Menu de test (spectate/streaming)")
        self.test_menu_button.setFixedSize(40, 40)
        self.test_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.test_menu_button.setStyleSheet("""
            QToolButton {
                background-color: #f3f4f6;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                color: #4b5563;
            }
            QToolButton:hover {
                background-color: #e5e7eb;
            }
            QToolButton::menu-indicator { 
                image: none;  /* Cacher l'indicateur de menu par défaut */
            }
        """)
        
        # Créer le menu déroulant
        test_menu = QMenu(self)
        test_spectate_action = QAction("Test Spectate", self)
        test_spectate_action.triggered.connect(self.test_spectate)
        test_stream_action = QAction("Test Stream", self)
        test_stream_action.triggered.connect(self.test_stream)
        
        test_menu.addAction(test_spectate_action)
        test_menu.addAction(test_stream_action)
        
        self.test_menu_button.setMenu(test_menu)
        top_section_layout.addWidget(self.test_menu_button, 0, Qt.AlignVCenter)  # Aligner verticalement au centre
        
        # Ajouter la section supérieure au layout principal
        main_layout.addWidget(top_section)
        
        # Ajouter une marge supplémentaire sous la puce League Spectate
        main_layout.addSpacing(10)  # 10 pixels de marge supplémentaire
        
        # Section principale avec la table des joueurs (sans les boutons de contrôle)
        main_section = QWidget()
        main_section_layout = QVBoxLayout(main_section)
        main_section_layout.setContentsMargins(0, 0, 0, 0)
        main_section_layout.setSpacing(4)
        
        # Players table container
        players_container = QWidget()
        players_layout = QVBoxLayout(players_container)
        players_layout.setContentsMargins(0, 0, 0, 0)
        
        # Table des joueurs (moderne)
        self.players_table = ModernTableWidget()
        self.players_table.setColumnCount(6)
        self.players_table.setHorizontalHeaderLabels(["Joueur", "Région", "Chaîne", "Streaming", "Active", "Actions"])
        
        players_layout.addWidget(self.players_table)
        
        main_section_layout.addWidget(players_container)
        
        # Console section
        self.console = ModernConsole()
        
        # Créer un splitter entre les joueurs et la console
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(1)
        splitter.addWidget(main_section)
        splitter.addWidget(self.console)
        splitter.setSizes([600, 200])
        
        # Ajouter le splitter au layout de contenu
        main_layout.addWidget(splitter)
        
        # Set up the service - inject the logger
        self.service.set_log_callback(self.log_message)
        
        # Update the status
        self.update_status()
        
        # Setup timer for periodic updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update each second

    def save_config(self):
        """Sauvegarder explicitement la configuration"""
        try:
            if self.config.save():
                self.console.log("Configuration sauvegardée avec succès", "SUCCESS")
            else:
                self.console.log("Erreur lors de la sauvegarde de la configuration", "ERROR")
        except Exception as e:
            self.console.log(f"Exception lors de la sauvegarde: {str(e)}", "ERROR")

    def update_players_table(self, save=True):
        """Met à jour le tableau des joueurs et sauvegarde si nécessaire"""
        try:
            print(f"Mise à jour de la table des joueurs. Nombre de joueurs: {len(self.config.players)}")
            # Pour chaque joueur, afficher le nom pour déboguer
            for name in self.config.players:
                print(f"Joueur trouvé: {name}")
            
            if save:
                try:
                    self.config.save()
                except Exception as e:
                    self.console.log(f"Erreur lors de la sauvegarde de la configuration: {str(e)}", "ERROR")
        
            # Déconnecter les signaux existants pour éviter les doubles connexions
            # Utiliser une méthode encore plus sécurisée - ne pas déconnecter tous les signaux
            # mais plutôt recréer le widget entièrement
            
            # Clear the table first
            self.players_table.setRowCount(0)
            
            # Configure columns
            self.players_table.setColumnCount(6)
            self.players_table.setHorizontalHeaderLabels([
                "Name", "Region", "Channel", "Streaming", "Active", "Actions"
            ])
            
            # Set column widths
            self.players_table.setColumnWidth(0, 150)  # Name
            self.players_table.setColumnWidth(1, 80)   # Region
            self.players_table.setColumnWidth(2, 150)  # Channel
            self.players_table.setColumnWidth(3, 100)  # Status
            self.players_table.setColumnWidth(4, 80)   # Active/Inactive
            self.players_table.setColumnWidth(5, 120)  # Actions - réduit de moitié
            
            # Set stretch for the last column
            self.players_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
            sorted_players = sorted(list(self.config.players.items()))
            
            for row, (name, player) in enumerate(sorted_players):
                self.players_table.insertRow(row)
                self.players_table.setRowHeight(row, 50)  # Réduire la hauteur de ligne (60 -> 50)
                
                # Player name
                name_item = QTableWidgetItem(name)
                name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.players_table.setItem(row, 0, name_item)
                
                # Region
                region_item = QTableWidgetItem(player.region)
                region_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.players_table.setItem(row, 1, region_item)
                
                # Channel
                channel_item = QTableWidgetItem(player.channel_name)
                channel_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.players_table.setItem(row, 2, channel_item)
                
                # Status indicator
                try:
                    status = "Streaming" if self.service.is_player_streaming(name) else "Idle"
                except:
                    status = "Idle"
                
                status_widget = QWidget()
                status_layout = QHBoxLayout(status_widget)
                status_layout.setContentsMargins(4, 4, 4, 4)
                
                status_label = QLabel(status)
                status_label.setStyleSheet(f"""
                    background-color: {('#dcfce7' if status == 'Streaming' else '#f3f4f6')};
                    color: {('#16a34a' if status == 'Streaming' else '#374151')};
                    padding: 4px 8px;
                    border-radius: 4px;
                """)
                status_layout.addWidget(status_label)
                status_layout.addStretch()
                self.players_table.setCellWidget(row, 3, status_widget)
                
                # Active/Inactive toggle button (column 4)
                active_widget = QWidget()
                active_layout = QHBoxLayout(active_widget)
                active_layout.setContentsMargins(8, 4, 8, 4)
                active_layout.setAlignment(Qt.AlignCenter)
                
                # Utiliser un simple QPushButton avec un style très clair
                text = "✓ Actif" if player.enabled else "✕ Inactif"
                color = "#16a34a" if player.enabled else "#6b7280"  # vert ou gris
                bg_color = "#dcfce7" if player.enabled else "#f3f4f6"  # vert clair ou gris clair
                border_color = "#86efac" if player.enabled else "#d1d5db"  # vert clair ou gris clair
                
                active_btn = QPushButton(text)
                active_btn.setFixedSize(90, 30)  # Taille augmentée
                active_btn.setCursor(Qt.PointingHandCursor)
                active_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_color};
                        color: {color};
                        border: 1px solid {border_color};
                        border-radius: 6px;
                        padding: 2px 6px;
                    }}
                    QPushButton:hover {{
                        background-color: {border_color};
                    }}
                """)
                
                # Fonction simple pour gérer le clic
                def toggle_click_handler(player_name=name, enabled=player.enabled):
                    def handler():
                        # Inverser l'état et appeler toggle_player
                        self.toggle_player(player_name, not enabled)
                    return handler
                
                active_btn.clicked.connect(toggle_click_handler())
                active_layout.addWidget(active_btn)
                
                self.players_table.setCellWidget(row, 4, active_widget)
                
                # Action buttons (column 5)
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 4, 4, 4)
                action_layout.setSpacing(8)
                
                # Create edit and delete buttons directly
                edit_btn = QPushButton("Edit")
                edit_btn.setFixedSize(25, 25)
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #eff6ff;
                        color: #2563eb;
                        border: 1px solid #bfdbfe;
                        border-radius: 6px;
                        padding: 2px 4px;
                    }
                    QPushButton:hover {
                        background-color: #dbeafe;
                    }
                """)
                
                # Fonctions de création de handler plus sûres
                def create_edit_handler(player_name):
                    return lambda checked=False: self.edit_player(player_name)
                
                def create_delete_handler(player_name):
                    return lambda checked=False: self.delete_player(player_name)
                
                edit_btn.clicked.connect(create_edit_handler(name))
                
                delete_btn = QPushButton("Del")
                delete_btn.setFixedSize(25, 25)
                delete_btn.setCursor(Qt.PointingHandCursor)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #fee2e2;
                        color: #dc2626;
                        border: 1px solid #fecaca;
                        border-radius: 6px;
                        padding: 2px 4px;
                    }
                    QPushButton:hover {
                        background-color: #fecaca;
                    }
                """)
                delete_btn.clicked.connect(create_delete_handler(name))
                
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                action_layout.addStretch()
                
                self.players_table.setCellWidget(row, 5, action_widget)
        
        except Exception as e:
            self.console.log(f"Erreur lors de la mise à jour du tableau des joueurs: {str(e)}", "ERROR")

    def log_message(self, message: str, level: str = "INFO"):
        """Callback for service logging"""
        self.console.log(message, level)

    def toggle_service(self):
        """Toggle the service between running and stopped states"""
        try:
            if self.service.running:  # Correction: is_running -> running
                # Stop the service
                try:
                    # Update button
                    self.toggle_button.setText("Starting...")
                    self.toggle_button.setEnabled(False)
                    
                    # Show stopping state in UI
                    self.status_card.set_stopping()
                    
                    # Define error callback
                    def log_error(msg, exc=None):
                        self.console.log(f"Error: {msg}", "ERROR")
                        if exc:
                            self.console.log(f"Exception: {str(exc)}", "ERROR")
                    
                    # Actually stop the service
                    self.service.stop()
                    
                    # Update UI to reflect stopped state
                    self.status_card.set_active(False)
                    self.toggle_button.setText("Start Service")
                    # Remettre le bouton en bleu normal (pas rouge)
                    self.toggle_button.setStyleSheet("""
                        QPushButton {
                            background-color: #3b82f6;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 4px 10px;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #2563eb;
                        }
                        QPushButton:pressed {
                            background-color: #1d4ed8;
                        }
                        QPushButton:disabled {
                            background-color: #d1d5db;
                            color: #9ca3af;
                        }
                    """)
                    self.toggle_button.setEnabled(True)
                    self.console.log("Service stopped", "INFO")
                    
                except Exception as e:
                    self.console.log(f"Failed to stop service: {str(e)}", "ERROR")
                    self.toggle_button.setText("Stop Service")
                    # Garder le bouton rouge car le service est toujours actif
                    self.toggle_button.setStyleSheet("""
                        QPushButton {
                            background-color: #ef4444;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 4px 10px;
                            min-width: 80px;
                        }
                        QPushButton:hover {
                            background-color: #dc2626;
                        }
                        QPushButton:pressed {
                            background-color: #b91c1c;
                        }
                        QPushButton:disabled {
                            background-color: #d1d5db;
                            color: #9ca3af;
                        }
                    """)
                    self.toggle_button.setEnabled(True)
                    self.status_card.set_active(self.service.running)
            else:
                # Trying to start the service
                try:
                    # Update button first
                    self.toggle_button.setText("Starting...")
                    self.toggle_button.setEnabled(False)
                    
                    # Ensure OBS is configured
                    if not self.config.verify_obs_settings():
                        errors = self.config.get_validation_errors()
                        error_msg = "\n• ".join(["Configuration incomplete:"] + errors)
                        self.console.log(error_msg, "ERROR")
                        
                        # Show dialog
                        QMessageBox.warning(
                            self,
                            "Configuration Incomplete",
                            f"{error_msg}\n\nPlease configure OBS settings first."
                        )
                        # Open settings
                        self.show_obs_settings()
                        # Reset button
                        self.toggle_button.setText("Start Service")
                        self.toggle_button.setEnabled(True)
                        return
                except Exception as e:
                    self.console.log(f"Error checking configuration: {str(e)}", "ERROR")
                    self.toggle_button.setText("Start Service")
                    self.toggle_button.setEnabled(True)
                    return
                
                # Already configured, proceed with starting
                success = False
                
                try:
                    # Override the service's emergency_log to use our console
                    def emergency_log(self_svc, message, level="INFO"):
                        if hasattr(self, 'console'):
                            self.console.log(message, level)
                        else:
                            print(f"[{level}] {message}")
                    
                    self.service.log = emergency_log.__get__(self.service, type(self.service))
                    
                    # Start the service
                    success = self.service.start()
                    
                    if success:
                        self.console.log("Service started successfully", "SUCCESS")
                        self.status_card.set_active(True)
                        self.toggle_button.setText("Stop Service")
                        # Mettre le bouton en rouge quand le service est actif
                        self.toggle_button.setStyleSheet("""
                            QPushButton {
                                background-color: #ef4444;
                                color: white;
                                border: none;
                                border-radius: 4px;
                                padding: 4px 10px;
                                min-width: 80px;
                            }
                            QPushButton:hover {
                                background-color: #dc2626;
                            }
                            QPushButton:pressed {
                                background-color: #b91c1c;
                            }
                            QPushButton:disabled {
                                background-color: #d1d5db;
                                color: #9ca3af;
                            }
                        """)
                    else:
                        self.console.log("Failed to start service", "ERROR")
                        self.status_card.set_active(False)
                        self.toggle_button.setText("Start Service")
                    
                except Exception as e:
                    # In case of error starting
                    def emergency_log(self_svc, message, level="INFO"):
                        if hasattr(self, 'console'):
                            self.console.log(message, level)
                        else:
                            print(f"[{level}] {message}")
                        
                    self.service.log = emergency_log.__get__(self.service, type(self.service))
                        
                    self.console.log(f"Error starting service: {str(e)}", "ERROR")
                    self.status_card.set_active(False)
                    self.toggle_button.setText("Start Service")
                
                # Re-enable button in all cases
                self.toggle_button.setEnabled(True)
            
        except Exception as e:
            self.console.log(f"Erreur lors de la bascule du service: {str(e)}", "ERROR")
            self.status_card.set_active(self.service.running)
            self.toggle_button.setText("Start Service")
            self.toggle_button.setEnabled(True)

    def update_status(self):
        """Update the status display based on the current service state"""
        try:
            # Vérifier explicitement les attributs de Service pour le débogage
            is_running = bool(self.service.running)
            is_streaming = bool(self.service.isStreaming)
            active_stream = self.service.active_stream
            
            self.console.log(f"[DEBUG] Status: running={is_running}, streaming={is_streaming}, active_stream={active_stream}", "INFO")
            
            # Check if service is running
            if is_streaming:
                # Check what player is being streamed
                if active_stream:
                    # Format: (player_name, channel_name)
                    player_name, channel_name = active_stream
                    self.status_card.set_active(True, f"{player_name} on {channel_name}")
                    self.console.log(f"[STATUS] Streaming: {player_name} on {channel_name}", "SUCCESS")
                else:
                    # Service is running but no specific player is streaming yet
                    self.status_card.set_active(True)
                    self.console.log("[STATUS] Streaming but no player info", "WARNING")
            else:
                # Service is not streaming
                if is_running:
                    self.status_card.set_active(True)
                    self.console.log("[STATUS] Service running but not streaming", "INFO")
                else:
                    self.status_card.set_active(False)
                    self.console.log("[STATUS] Service stopped", "INFO")
                    
            # Mettre à jour explicitement le tableau des joueurs
            self.update_players_table(save=False)
            
        except Exception as e:
            self.console.log(f"Error updating status: {str(e)}", "ERROR")

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
        """Change l'état d'un joueur sans sauvegarder immédiatement"""
        self.console.log(f"[TOGGLE-001] Attempting to toggle player {name} to {'active' if state else 'inactive'}", "INFO")
        
        try:
            if not name:
                self.console.log("[TOGGLE-002] Empty player name provided", "ERROR")
                return False
                
            if name not in self.config.players:
                self.console.log(f"[TOGGLE-003] Player {name} not found in configuration", "ERROR")
                return False
                
            # Récupérer le statut actuel pour le comparer
            current_state = self.config.players[name].enabled
            self.console.log(f"[TOGGLE-004] Current state for {name}: {current_state}, new state: {state}", "DEBUG")
            
            if current_state == state:
                self.console.log(f"[TOGGLE-005] State is already {state} for {name}, no change needed", "INFO")
                return True
                
            # Mise à jour de l'état du joueur en mémoire seulement
            try:
                self.config.players[name].enabled = bool(state)
                self.console.log(f"[TOGGLE-006] Player {name} is now {'active' if state else 'inactive'}", "SUCCESS")
            except Exception as e:
                self.console.log(f"[TOGGLE-ERR1] Failed to update player state: {str(e)}", "ERROR")
                return False
            
            # Mettre à jour l'interface sans sauvegarder
            try:
                self.update_players_table(save=False)
                self.console.log(f"[TOGGLE-007] Player table updated for {name}", "DEBUG")
                return True
            except Exception as e:
                self.console.log(f"[TOGGLE-ERR2] Failed to update UI: {str(e)}", "ERROR")
                # On continue même si l'UI ne s'est pas mise à jour, l'état mémoire est correct
                return True
                
        except Exception as e:
            self.console.log(f"[TOGGLE-CRIT] Critical error toggling {name}: {str(e)}", "ERROR")
            import traceback
            self.console.log(f"[TOGGLE-TRACE] {traceback.format_exc()}", "ERROR")
            return False

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

    def test_spectate(self):
        """Test the spectate functionality without starting the service"""
        self.console.log("[SPECTATE-001] Starting spectate test", "INFO")
        
        sender = None
        original_text = "Test Spectate"
        
        try:
            # Récupérer le nom du joueur sélectionné ou choisir le premier de la liste
            player_name = None
            active_count = 0
            
            self.console.log("[SPECTATE-002] Searching for active players", "INFO")
            for row in range(self.players_table.rowCount()):
                try:
                    cell_widget = self.players_table.cellWidget(row, 4)
                    if cell_widget:
                        is_active = "Active" in cell_widget.findChild(QPushButton).text()
                        if is_active:
                            active_count += 1
                            if player_name is None:
                                player_name = self.players_table.item(row, 0).text()
                                self.console.log(f"[SPECTATE-003] Found active player: {player_name}", "INFO")
                except Exception as e:
                    self.console.log(f"[SPECTATE-ERR1] Error checking row {row}: {str(e)}", "ERROR")
            
            self.console.log(f"[SPECTATE-004] Found {active_count} active player(s)", "INFO")
            
            if player_name is None:
                self.console.log("[SPECTATE-005] No active players found", "WARNING")
                QMessageBox.warning(self, "No Active Players", "Please activate at least one player to test spectate.")
                return
            
            # Désactiver le bouton pendant le test
            sender = self.sender()
            if sender:
                original_text = sender.text()
                sender.setText("Testing...")
                sender.setEnabled(False)
                self.console.log("[SPECTATE-006] Disabled UI button during test", "DEBUG")
            
            # Effectuer le test de spectate
            try:
                if player_name not in self.config.players:
                    self.console.log(f"[SPECTATE-ERR2] Player {player_name} not found in config", "ERROR")
                    return
                    
                region = self.config.players[player_name].region
                summoner_id = self.config.players[player_name].summoner_id
                
                self.console.log(f"[SPECTATE-007] Using League API for {player_name} (ID: {summoner_id}) on {region}", "INFO")
                
                if not self.config.riot_api_key:
                    self.console.log("[SPECTATE-ERR3] No Riot API key configured", "ERROR")
                    return
                
                api = LeagueAPI(self.config.riot_api_key, region)
                api.set_logger(self.console.log)
                
                # Vérifier si en partie
                self.console.log(f"[SPECTATE-008] Checking if player is in game", "INFO")
                game_id = api.get_active_game_id(summoner_id)
                
                if not game_id:
                    self.console.log(f"[SPECTATE-009] Player {player_name} is not in game", "WARNING")
                    return
                
                self.console.log(f"[SPECTATE-010] Found active game with ID: {game_id}", "SUCCESS")
                
                # Vérifier le chemin de League
                if not self.config.league_path or not os.path.exists(self.config.league_path):
                    self.console.log("[SPECTATE-ERR4] League path is invalid or not configured", "ERROR") 
                    return
                
                # Créer la commande de spectate
                spectate_cmd = api.create_spectate_command(game_id, self.config.league_path)
                self.console.log(f"[SPECTATE-011] Generated spectate command: {spectate_cmd}", "INFO")
                
                # Tenter de lancer la commande
                success = self.service.launch_spectate_client(spectate_cmd) 
                
                if not success:
                    self.console.log("Trying alternative launch method...", "WARNING")
                    success = self.service.launch_spectate_client_alternative(spectate_cmd)
                
                if success:
                    self.console.log("Spectate command successfully executed", "SUCCESS")
                else:
                    self.console.log("All launch methods failed", "ERROR")
                
            except Exception as e:
                self.console.log(f"[SPECTATE-ERR5] Error during spectate test: {str(e)}", "ERROR")
                import traceback
                self.console.log(f"[SPECTATE-TRACE] {traceback.format_exc()}", "ERROR")
            finally:
                # Réactiver le bouton
                if sender:
                    sender.setText(original_text)
                    sender.setEnabled(True)
                    self.console.log("[SPECTATE-014] Re-enabled UI button", "DEBUG")
        
        except Exception as e:
            self.console.log(f"[SPECTATE-CRIT] Critical error in test_spectate: {str(e)}", "ERROR")
            import traceback
            self.console.log(f"[SPECTATE-TRACE2] {traceback.format_exc()}", "ERROR")
            
            # Ensure button is re-enabled
            if sender:
                sender.setText(original_text)
                sender.setEnabled(True)

    def test_stream(self):
        """Test the stream functionality without starting the service"""
        self.console.log("[STREAM-001] Starting stream test", "INFO")
        
        sender = None
        original_text = "Test Stream"
        
        try:
            # Récupérer le nom du joueur sélectionné ou choisir le premier joueur actif de la liste
            player_name = None
            active_count = 0
            
            self.console.log("[STREAM-002] Searching for active players", "INFO")
            for row in range(self.players_table.rowCount()):
                try:
                    cell_widget = self.players_table.cellWidget(row, 4)
                    if cell_widget:
                        is_active = "Actif" in cell_widget.findChild(QPushButton).text()
                        if is_active:
                            active_count += 1
                            if player_name is None:
                                player_name = self.players_table.item(row, 0).text()
                                self.console.log(f"[STREAM-003] Found active player: {player_name}", "INFO")
                except Exception as e:
                    self.console.log(f"[STREAM-ERR1] Error checking row {row}: {str(e)}", "ERROR")
            
            self.console.log(f"[STREAM-004] Found {active_count} active player(s)", "INFO")
            
            if player_name is None:
                self.console.log("[STREAM-005] No active players found", "WARNING")
                QMessageBox.warning(self, "No Active Players", "Please activate at least one player to test stream.")
                return
            
            # Désactiver le bouton pendant le test
            sender = self.sender()
            if sender:
                original_text = sender.text()
                sender.setText("Testing...")
                sender.setEnabled(False)
                self.console.log("[STREAM-006] Disabled UI button during test", "DEBUG")
            
            # Effectuer le test de stream
            try:
                # Vérifier si OBS est configuré
                if not self.config.obs_password or not self.config.obs_address:
                    self.console.log("[STREAM-ERR2] OBS settings are not configured", "ERROR")
                    return
                
                self.console.log(f"[STREAM-007] Connecting to OBS at {self.config.obs_address}", "INFO")
                
                # Vérifier que le joueur est dans la configuration
                if player_name not in self.config.players:
                    self.console.log(f"[STREAM-ERR3] Player {player_name} not found in config", "ERROR")
                    return
                
                # Récupérer la configuration du joueur
                player_config = self.config.players[player_name]
                if not player_config.stream_key or not player_config.channel_name:
                    self.console.log(f"[STREAM-ERR4] Stream key or channel name missing for {player_name}", "ERROR")
                    return
                
                self.console.log(f"[STREAM-008] Player {player_name} has valid streaming config (channel: {player_config.channel_name})", "INFO")
                
                # Tentative d'envoi d'une commande test à OBS
                import json
                import websocket
                import base64
                import hashlib
                from datetime import datetime
                
                # Fonction pour envoyer une commande
                def send_command(ws, request_type, request_data=None):
                    if request_data is None:
                        request_data = {}
                    
                    message = {
                        "request-type": request_type,
                        "message-id": f"test-{datetime.now().timestamp()}",
                        **request_data
                    }
                    
                    self.console.log(f"[STREAM-009] Sending OBS command: {request_type}", "DEBUG")
                    ws.send(json.dumps(message))
                    response = json.loads(ws.recv())
                    return response
                
                # Créer la connexion WebSocket à OBS
                try:
                    self.console.log("[STREAM-010] Creating WebSocket connection to OBS", "INFO")
                    ws = websocket.create_connection(self.config.obs_address)
                except Exception as e:
                    self.console.log(f"[STREAM-ERR5] Failed to connect to OBS: {str(e)}", "ERROR")
                    return
                
                # Authentifier
                try:
                    self.console.log("[STREAM-011] Starting OBS authentication", "INFO")
                    auth_response = send_command(ws, "GetAuthRequired")
                    
                    if auth_response.get("authRequired"):
                        self.console.log("[STREAM-012] Authentication required, generating auth hash", "INFO")
                        
                        try:
                            secret = base64.b64encode(hashlib.sha256(
                                (self.config.obs_password + auth_response["salt"]).encode()
                            ).digest())
                            
                            auth_response = send_command(ws, "Authenticate", {
                                "auth": base64.b64encode(
                                    hashlib.sha256(secret + auth_response["challenge"].encode()).digest()
                                ).decode()
                            })
                        except Exception as e:
                            self.console.log(f"[STREAM-ERR6] Error generating auth hash: {str(e)}", "ERROR")
                            ws.close()
                            return
                        
                        if auth_response.get("status") != "ok":
                            self.console.log(f"[STREAM-ERR7] Authentication failed: {auth_response.get('error')}", "ERROR")
                            ws.close()
                            return
                        
                        self.console.log("[STREAM-013] Authentication successful", "SUCCESS")
                    else:
                        self.console.log("[STREAM-014] No authentication required", "INFO")
                except Exception as e:
                    self.console.log(f"[STREAM-ERR8] Error during authentication: {str(e)}", "ERROR")
                    ws.close()
                    return
                
                # Test de récupération de la liste des scènes
                try:
                    self.console.log("[STREAM-015] Requesting scene list", "INFO")
                    scenes_response = send_command(ws, "GetSceneList")
                    
                    if scenes_response.get("status") == "ok":
                        scene_names = [scene["name"] for scene in scenes_response.get("scenes", [])]
                        self.console.log(f"[STREAM-016] Found {len(scene_names)} scenes in OBS", "SUCCESS")
                        if scene_names:
                            self.console.log(f"[STREAM-017] Sample scenes: {', '.join(scene_names[:3])}", "INFO")
                    else:
                        self.console.log(f"[STREAM-ERR9] Failed to get scene list: {scenes_response.get('error')}", "ERROR")
                except Exception as e:
                    self.console.log(f"[STREAM-ERR10] Error getting scene list: {str(e)}", "ERROR")
                
                # Fermer la connexion
                ws.close()
                self.console.log("[STREAM-018] OBS connection test completed successfully", "SUCCESS")
                
            except Exception as e:
                self.console.log(f"[STREAM-ERR11] Error during stream test: {str(e)}", "ERROR")
                import traceback
                self.console.log(f"[STREAM-TRACE] {traceback.format_exc()}", "ERROR")
            finally:
                # Réactiver le bouton
                if sender:
                    sender.setText(original_text)
                    sender.setEnabled(True)
                    self.console.log("[STREAM-019] Re-enabled UI button", "DEBUG")
                    
        except Exception as e:
            self.console.log(f"[STREAM-CRIT] Critical error in test_stream: {str(e)}", "ERROR")
            import traceback
            self.console.log(f"[STREAM-TRACE2] {traceback.format_exc()}", "ERROR")
            
            # Ensure button is re-enabled
            if sender:
                sender.setText(original_text)
                sender.setEnabled(True)
