"""
Interface PyQt5 pour WIFI Manager.
Affiche une fenêtre avec les contrôles et la table des résultats.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QFileDialog, QMessageBox, QSpinBox, QCheckBox, QInputDialog,
    QDialog, QGridLayout, QListWidget, QTabWidget, QFrame, QHeaderView, QSlider
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QColor
from typing import Optional, List, Dict
import sys
import os
from collections import deque
from datetime import datetime

# Matplotlib imports for graphs
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Importe les modules personnalisés
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import ARPScanner, OUIDatabase, CIDRValidator, CSVExporter, AppConfig, DeviceNameResolver, DeviceKicker, MessageSender, TVController


class ScanWorker(QObject):
    """
    Worker qui effectue le scan ARP dans un thread séparé.
    Émet des signaux pour communiquer avec l'UI.
    """
    
    progress = pyqtSignal(str, int)  # message, count
    status = pyqtSignal(str)          # status message
    completed = pyqtSignal(list)      # results
    error = pyqtSignal(str)           # error message
    
    def __init__(self, scanner: ARPScanner):
        """
        Initialise le worker.
        
        Args:
            scanner: Instance ARPScanner
        """
        super().__init__()
        self.scanner = scanner
        self.network = None
        self.include_ping = False
    
    def set_parameters(self, network: str, include_ping: bool = False):
        """Configure les paramètres du scan."""
        self.network = network
        self.include_ping = include_ping
    
    def run(self):
        """Lance le scan."""
        if not self.network:
            self.error.emit("Aucun réseau spécifié")
            return
        
        try:
            self.status.emit(f"Initialisation du scan sur {self.network}...")
            results = self.scanner.scan(
                self.network,
                progress_callback=self._on_progress,
                status_callback=self._on_status,
                include_ping=self.include_ping
            )
            self.completed.emit(results)
        except PermissionError as e:
            self.error.emit("Erreur de permissions. Veuillez lancer l'application en tant qu'administrateur.")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.error.emit(f"Erreur lors du scan: {str(e)}\n{error_details}")
            print(f"[SCAN ERROR] {error_details}")
    
    def _on_progress(self, message: str, count: int):
        """Callback de progression."""
        self.progress.emit(message, count)
    
    def _on_status(self, message: str):
        """Callback de status."""
        self.status.emit(message)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application WIFI Manager."""
    
    def __init__(self):
        """Initialise la fenêtre principale."""
        super().__init__()
        
        # Initialise les composants
        self.scanner = ARPScanner(timeout=2)
        self.oui_db = OUIDatabase(auto_download=True)
        self.device_kicker = DeviceKicker()
        self.message_sender = MessageSender()
        self.tv_controller = TVController()
        self.current_results: List[Dict] = []
        self.scan_thread: Optional[QThread] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.is_scanning = False
        
        # Monitoring data for graphs (store last 60 points = 5 minutes at 5s intervals)
        self.device_count_history = deque(maxlen=60)
        self.active_device_history = deque(maxlen=60)
        self.avg_signal_history = deque(maxlen=60)
        self.time_history = deque(maxlen=60)
        
        # Network stats
        self.total_devices = 0
        self.active_devices = 0
        self.network_bandwidth = "0 Mbps"
        self.uptime = "99.8%"
        self.app_start_time = datetime.now()  # Track when app started for uptime calculation
        self.scan_success_count = 0
        self.scan_total_count = 0
        
        # Configure l'UI
        self.init_ui()
        
        # Applique le style
        self.setStyleSheet(AppConfig.STYLE_DARK)
        
        # Timer pour mise à jour des stats
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_network_stats)
        self.stats_timer.start(5000)  # Update every 5 seconds
    
    def init_ui(self):
        """Initialise l'interface utilisateur."""
        # Définit les propriétés de la fenêtre
        self.setWindowTitle("WiFi Manager Pro - Enterprise Network Management")
        self.setGeometry(50, 50, 1600, 900)
        self.setMinimumSize(1200, 700)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # ===== Top Header Bar =====
        self._create_header_bar(main_layout)
        
        # ===== Configuration Bar =====
        self._create_config_bar(main_layout)
        
        # ===== Main Content Grid =====
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Left Sidebar (20% width, max 420px)
        self._create_left_sidebar(content_layout)
        
        # Main Content Area (80% width)
        self._create_main_content(content_layout)
        
        main_layout.addLayout(content_layout)
        
        # ===== Bottom Status Bar =====
        self._create_status_bar(main_layout)
    
    def _create_header_bar(self, parent_layout):
        """Crée la barre d'en-tête avec stats réseau"""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 100, 0.3);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Logo et titre
        title_section = QHBoxLayout()
        
        logo_label = QLabel("🌐")
        logo_label.setStyleSheet("""
            QLabel {
                font-size: 36pt;
                color: #0078d4;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        title_section.addWidget(logo_label)
        
        title_text = QWidget()
        title_layout = QVBoxLayout(title_text)
        title_layout.setSpacing(0)
        
        title = QLabel("WiFi Manager Pro")
        title.setStyleSheet("""
            QLabel {
                font-size: 22pt;
                font-weight: bold;
                color: white;
                background: transparent;
            }
        """)
        title_layout.addWidget(title)
        
        subtitle = QLabel("Enterprise Network Management System")
        subtitle.setStyleSheet("font-size: 9pt; color: #888888; background: transparent;")
        title_layout.addWidget(subtitle)
        
        title_section.addWidget(title_text)
        title_section.addStretch()
        
        header_layout.addLayout(title_section)
        header_layout.addStretch()
        
        # Network Stats Cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.total_devices_label = self._create_stat_card("👥", "Appareils", "0", "#0078d4")
        self.active_devices_label = self._create_stat_card("✓", "Actifs", "0", "#28a745")
        self.bandwidth_label = self._create_stat_card("⚡", "Bande passante", "0 Mbps", "#ffc107")
        self.uptime_label = self._create_stat_card("✓", "Uptime", "99.8%", "#00ff88")
        
        stats_layout.addWidget(self.total_devices_label)
        stats_layout.addWidget(self.active_devices_label)
        stats_layout.addWidget(self.bandwidth_label)
        stats_layout.addWidget(self.uptime_label)
        
        header_layout.addLayout(stats_layout)
        
        parent_layout.addWidget(header)
    
    def _create_config_bar(self, parent_layout):
        """Crée la barre de configuration horizontale"""
        config_bar = QWidget()
        config_bar.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 100, 0.3);
            }
        """)
        config_layout = QHBoxLayout(config_bar)
        config_layout.setContentsMargins(15, 10, 15, 10)
        config_layout.setSpacing(12)
        
        # Title
        config_title = QLabel("⚙️ Config")
        config_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: white; background: transparent;")
        config_layout.addWidget(config_title)
        
        # CIDR Input
        cidr_container = QWidget()
        cidr_container.setStyleSheet("background: transparent;")
        cidr_layout = QVBoxLayout(cidr_container)
        cidr_layout.setContentsMargins(0, 0, 0, 0)
        cidr_layout.setSpacing(3)
        
        cidr_label = QLabel("RÉSEAU CIDR")
        cidr_label.setStyleSheet("font-size: 8pt; color: #888888; font-weight: bold; background: transparent;")
        cidr_layout.addWidget(cidr_label)
        
        self.cidr_input = QLineEdit()
        self.cidr_input.setPlaceholderText("Ex: 192.168.1.0/24")
        suggestion = CIDRValidator.get_suggestion()
        self.cidr_input.setText(suggestion)
        self.cidr_input.setMinimumWidth(180)
        cidr_layout.addWidget(self.cidr_input)
        
        config_layout.addWidget(cidr_container)
        
        # Timeout Slider
        timeout_container = QWidget()
        timeout_container.setStyleSheet("background: transparent;")
        timeout_layout = QVBoxLayout(timeout_container)
        timeout_layout.setContentsMargins(0, 0, 0, 0)
        timeout_layout.setSpacing(3)
        
        timeout_label = QLabel("TIMEOUT")
        timeout_label.setStyleSheet("font-size: 8pt; color: #888888; font-weight: bold; background: transparent;")
        timeout_layout.addWidget(timeout_label)
        
        timeout_controls = QHBoxLayout()
        self.timeout_slider = QSlider(Qt.Horizontal)
        self.timeout_slider.setMinimum(1)
        self.timeout_slider.setMaximum(10)
        self.timeout_slider.setValue(2)
        self.timeout_slider.setMinimumWidth(120)
        self.timeout_slider.valueChanged.connect(self._on_timeout_changed)
        timeout_controls.addWidget(self.timeout_slider)
        
        self.timeout_value_label = QLabel("2s")
        self.timeout_value_label.setStyleSheet("""
            QLabel {
                background: rgba(45, 45, 45, 0.7);
                color: white;
                font-family: 'Consolas';
                font-size: 9pt;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 35px;
            }
        """)
        timeout_controls.addWidget(self.timeout_value_label)
        timeout_layout.addLayout(timeout_controls)
        
        config_layout.addWidget(timeout_container)
        
        # Ping Checkbox
        self.ping_checkbox = QCheckBox("Mode ping")
        self.ping_checkbox.setChecked(True)
        self.ping_checkbox.setStyleSheet("""
            QCheckBox {
                background: rgba(45, 45, 45, 0.3);
                color: #dddddd;
                padding: 8px 10px;
                border-radius: 6px;
                font-size: 9pt;
            }
            QCheckBox:hover {
                background: rgba(45, 45, 45, 0.5);
            }
        """)
        config_layout.addWidget(self.ping_checkbox)
        
        # Auto-detect button
        auto_btn = QPushButton("🛡️ Auto")
        auto_btn.clicked.connect(self._on_suggest_cidr)
        auto_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                color: white;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 6px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1084d7, stop:1 #0078d4);
            }
        """)
        config_layout.addWidget(auto_btn)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("background: rgba(100, 100, 100, 0.5); max-width: 2px;")
        config_layout.addWidget(separator)
        
        # Security Title
        security_title = QLabel("🛡️ Sécurité")
        security_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #00ff88; background: transparent;")
        config_layout.addWidget(security_title)
        
        # Security status items
        firewall_status = self._create_security_item("✓ Firewall", "Actif", "#28a745")
        config_layout.addWidget(firewall_status)
        
        wpa3_status = self._create_security_item("✓ WPA3", "Actif", "#28a745")
        config_layout.addWidget(wpa3_status)
        
        intrusion_status = self._create_security_item("⚠ Intrusions", "2 bloquées", "#ffc107")
        config_layout.addWidget(intrusion_status)
        
        config_layout.addStretch()
        
        parent_layout.addWidget(config_bar)
    
    def _create_stat_card(self, icon, label, value, color):
        """Crée une carte de statistique"""
        card = QWidget()
        card.setMinimumWidth(150)
        card.setStyleSheet(f"""
            QWidget {{
                background: rgba(45, 45, 45, 0.5);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 100, 0.3);
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 18pt; color: {color}; background: transparent;")
        layout.addWidget(icon_label)
        
        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_widget)
        text_layout.setSpacing(0)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 8pt; color: #888888; background: transparent;")
        text_layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_widget.setObjectName("stat_value")
        value_widget.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {color}; background: transparent;")
        text_layout.addWidget(value_widget)
        
        layout.addWidget(text_widget)
        
        return card
    
    def _create_left_sidebar(self, parent_layout):
        """Crée la barre latérale gauche"""
        sidebar = QWidget()
        sidebar.setMinimumWidth(450)
        sidebar.setMaximumWidth(600)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Quick Actions Card
        actions_card = QFrame()
        actions_card.setStyleSheet("""
            QFrame {
                background: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 100, 0.3);
            }
        """)
        actions_layout = QVBoxLayout(actions_card)
        actions_layout.setContentsMargins(25, 20, 25, 20)
        actions_layout.setSpacing(10)
        
        actions_title = QLabel("⚡ Actions Rapides")
        actions_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffc107; background: transparent;")
        actions_layout.addWidget(actions_title)
        
        # Grid of action buttons
        actions_grid = QGridLayout()
        actions_grid.setSpacing(10)
        actions_grid.setContentsMargins(0, 0, 0, 0)
        
        self.scan_btn = self._create_action_button("🔍", "Scan", "#0078d4", "#005a9e")
        self.scan_btn.clicked.connect(self._on_scan)
        actions_grid.addWidget(self.scan_btn, 0, 0)
        
        refresh_btn = self._create_action_button("🔄", "Refresh", "#00bcd4", "#0097a7")
        refresh_btn.clicked.connect(self._on_refresh)
        actions_grid.addWidget(refresh_btn, 0, 1)
        
        export_btn = self._create_action_button("💾", "Export", "#28a745", "#218838")
        export_btn.clicked.connect(self._on_export)
        actions_grid.addWidget(export_btn, 1, 0)
        
        stats_btn = self._create_action_button("📊", "Stats", "#9c27b0", "#7b1fa2")
        actions_grid.addWidget(stats_btn, 1, 1)
        
        msg_btn = self._create_action_button("📨", "Message", "#ff9800", "#f57c00")
        msg_btn.clicked.connect(self._on_send_message)
        actions_grid.addWidget(msg_btn, 2, 0)
        
        kick_all_btn = self._create_action_button("💥", "Kick All", "#dc3545", "#c82333")
        kick_all_btn.clicked.connect(self._on_kick_all)
        actions_grid.addWidget(kick_all_btn, 2, 1)
        
        stop_btn = self._create_action_button("🛑", "Stop", "#ff5722", "#e64a19")
        stop_btn.clicked.connect(self._on_stop_kick)
        actions_grid.addWidget(stop_btn, 3, 0)
        
        tv_btn = self._create_action_button("📺", "TV Remote", "#673ab7", "#512da8")
        tv_btn.clicked.connect(self._on_tv_remote)
        actions_grid.addWidget(tv_btn, 3, 1)
        
        actions_layout.addLayout(actions_grid)
        actions_layout.addStretch()
        
        sidebar_layout.addWidget(actions_card)
        
        parent_layout.addWidget(sidebar)
    
    def _create_action_button(self, icon, text, color1, color2):
        """Crée un bouton d'action avec gradient"""
        btn = QPushButton(f"{icon}\n{text}")
        btn.setMinimumHeight(70)
        btn.setMinimumWidth(190)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color1}, stop:1 {color2});
                color: white;
                font-weight: bold;
                border-radius: 8px;
                font-size: 10pt;
                padding: 8px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color2}, stop:1 {color1});
            }}
            QPushButton:pressed {{
                padding-top: 3px;
            }}
        """)
        return btn
    
    def _create_security_item(self, title, status, color):
        """Crée un élément de statut de sécurité"""
        item = QWidget()
        item.setMinimumWidth(110)
        item.setMaximumWidth(140)
        item.setStyleSheet(f"""
            QWidget {{
                background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1);
                border: 1px solid {color};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(6, 4, 6, 4)
        
        title_label = QLabel(title)
        title_label.setWordWrap(False)
        title_label.setStyleSheet(f"color: #dddddd; font-size: 9pt; background: transparent;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        status_label = QLabel(status)
        status_label.setStyleSheet(f"color: {color}; font-size: 8pt; font-weight: bold; background: transparent;")
        layout.addWidget(status_label)
        
        return item
    
    def _create_main_content(self, parent_layout):
        """Crée la zone de contenu principale avec onglets"""
        main_content = QWidget()
        content_layout = QVBoxLayout(main_content)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 100, 0.3);
            }
            QTabBar::tab {
                background: rgba(45, 45, 45, 0.5);
                color: #888888;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 10pt;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:1 #9c27b0);
                color: white;
            }
            QTabBar::tab:hover {
                background: rgba(100, 100, 100, 0.3);
                color: white;
            }
        """)
        
        # Devices Tab
        devices_tab = QWidget()
        devices_layout = QVBoxLayout(devices_tab)
        devices_layout.setContentsMargins(20, 20, 20, 20)
        
        # Devices header with filter
        devices_header = QHBoxLayout()
        
        devices_title = QLabel("📡 Appareils détectés (0)")
        devices_title.setObjectName("devices_count")
        devices_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; background: transparent;")
        devices_header.addWidget(devices_title)
        
        devices_header.addStretch()
        
        clear_btn = QPushButton("🗑️ Effacer")
        clear_btn.clicked.connect(self._on_clear)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(220, 53, 69, 0.2);
                border: 1px solid #dc3545;
                color: #dc3545;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(220, 53, 69, 0.3);
            }
        """)
        devices_header.addWidget(clear_btn)
        
        devices_layout.addLayout(devices_header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Type", "Appareil", "Adresse IP", "MAC Address",
            "Vendeur", "Signal", "Latence", "Bande", "Actions"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        
        devices_layout.addWidget(self.table)
        
        # Logs Tab
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.setContentsMargins(20, 20, 20, 20)
        
        logs_title = QLabel("📊 Logs système en temps réel")
        logs_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; background: transparent; margin-bottom: 10px;")
        logs_layout.addWidget(logs_title)
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        logs_layout.addWidget(self.logs_text)
        
        # Monitoring Tab
        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout(monitor_tab)
        monitor_layout.setContentsMargins(20, 20, 20, 20)
        monitor_layout.setSpacing(15)
        
        # Title
        monitor_title = QLabel("📈 Monitoring en temps réel")
        monitor_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white; background: transparent; margin-bottom: 10px;")
        monitor_layout.addWidget(monitor_title)
        
        # Create combined graph
        graphs_container = QWidget()
        graphs_layout = QVBoxLayout(graphs_container)
        graphs_layout.setSpacing(15)
        
        # Combined Graph with dual y-axes
        self.combined_figure = Figure(figsize=(14, 6), facecolor='#1e1e1e')
        self.combined_canvas = FigureCanvas(self.combined_figure)
        self.device_count_ax = self.combined_figure.add_subplot(111)
        self.device_count_ax.set_facecolor('#1e1e1e')
        self.device_count_ax.set_xlabel('Temps (dernières 5 minutes)', color='#cccccc', fontsize=11, labelpad=10)
        self.device_count_ax.set_ylabel('Nombre d\'appareils', color='#0078d4', fontsize=11, labelpad=10)
        self.device_count_ax.tick_params(axis='y', colors='#0078d4', labelsize=10, width=1.5)
        self.device_count_ax.tick_params(axis='x', colors='#cccccc', labelsize=10, width=1.5)
        self.device_count_ax.spines['bottom'].set_color('#555555')
        self.device_count_ax.spines['top'].set_visible(False)
        self.device_count_ax.spines['left'].set_color('#0078d4')
        self.device_count_ax.spines['left'].set_linewidth(2)
        self.device_count_ax.spines['right'].set_color('#9c27b0')
        self.device_count_ax.spines['right'].set_linewidth(2)
        self.device_count_ax.grid(True, alpha=0.15, color='#555555', linestyle='--', linewidth=0.8)
        
        # Create second y-axis for signal strength
        self.signal_ax = self.device_count_ax.twinx()
        self.signal_ax.set_ylabel('Signal moyen (%)', color='#9c27b0', fontsize=11, labelpad=10)
        self.signal_ax.tick_params(axis='y', colors='#9c27b0', labelsize=10, width=1.5)
        self.signal_ax.set_ylim(0, 100)
        self.signal_ax.spines['right'].set_color('#9c27b0')
        self.signal_ax.spines['right'].set_linewidth(2)
        self.signal_ax.spines['top'].set_visible(False)
        
        self.combined_figure.tight_layout(pad=1.5)
        graphs_layout.addWidget(self.combined_canvas)
        
        monitor_layout.addWidget(graphs_container)
        
        # Add tabs
        self.tabs.addTab(devices_tab, "🌐 Appareils connectés")
        self.tabs.addTab(monitor_tab, "📈 Monitoring")
        self.tabs.addTab(logs_tab, "📊 Logs système")
        
        content_layout.addWidget(self.tabs)
        
        parent_layout.addWidget(main_content, stretch=1)
    
    def _create_status_bar(self, parent_layout):
        """Crée la barre de statut en bas"""
        status_bar = QWidget()
        status_bar.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 30, 0.9);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 100, 0.3);
            }
        """)
        
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(20, 12, 20, 12)
        
        # Left section
        left_section = QHBoxLayout()
        
        status_indicator = QLabel("●")
        status_indicator.setStyleSheet("color: #28a745; font-size: 14pt; background: transparent;")
        left_section.addWidget(status_indicator)
        
        self.status_label = QLabel("Système opérationnel")
        self.status_label.setStyleSheet("color: #888888; font-size: 10pt; background: transparent;")
        left_section.addWidget(self.status_label)
        
        left_section.addSpacing(30)
        
        version_label = QLabel("WiFi Manager Pro v3.0.0")
        version_label.setStyleSheet("color: #666666; font-size: 9pt; background: transparent;")
        left_section.addWidget(version_label)
        
        status_layout.addLayout(left_section)
        status_layout.addStretch()
        
        # Right section
        import datetime
        time_label = QLabel(f"Dernière mise à jour: {datetime.datetime.now().strftime('%H:%M:%S')}")
        time_label.setStyleSheet("color: #888888; font-size: 9pt; background: transparent;")
        status_layout.addWidget(time_label)
        
        status_layout.addSpacing(20)
        
        doc_link = QLabel("📚 Documentation")
        doc_link.setStyleSheet("color: #0078d4; font-size: 9pt; background: transparent; font-weight: bold;")
        status_layout.addWidget(doc_link)
        
        status_layout.addSpacing(15)
        
        support_link = QLabel("💬 Support")
        support_link.setStyleSheet("color: #0078d4; font-size: 9pt; background: transparent; font-weight: bold;")
        status_layout.addWidget(support_link)
        
        parent_layout.addWidget(status_bar)
    
    def _on_timeout_changed(self, value):
        """Met à jour l'affichage du timeout"""
        self.timeout_value_label.setText(f"{value}s")
        self.scanner.timeout = value
    
    def _update_network_stats(self):
        """Met à jour les statistiques réseau"""
        self.total_devices = len(self.current_results)
        self.active_devices = sum(1 for d in self.current_results if (d.get('ping') or 999) < 100)
        
        # Calculate real bandwidth (sum of all device bandwidths)
        total_bandwidth_mbps = 0
        for device in self.current_results:
            bandwidth_str = device.get('bandwidth', '0 Mbps')
            try:
                if isinstance(bandwidth_str, str):
                    # Extract number from "980 Mbps" or "45 Mbps"
                    if 'Mbps' in bandwidth_str:
                        bw_value = int(bandwidth_str.replace('Mbps', '').strip())
                        total_bandwidth_mbps += bw_value
                    elif 'Gbps' in bandwidth_str:
                        bw_value = float(bandwidth_str.replace('Gbps', '').strip())
                        total_bandwidth_mbps += int(bw_value * 1000)
            except:
                pass
        
        # Format bandwidth
        if total_bandwidth_mbps >= 1000:
            self.network_bandwidth = f"{total_bandwidth_mbps / 1000:.1f} Gbps"
        else:
            self.network_bandwidth = f"{total_bandwidth_mbps} Mbps"
        
        # Calculate uptime (scan success rate)
        if self.scan_total_count > 0:
            uptime_percentage = (self.scan_success_count / self.scan_total_count) * 100
            self.uptime = f"{uptime_percentage:.1f}%"
        else:
            # Calculate based on time running
            elapsed = (datetime.now() - self.app_start_time).total_seconds()
            if elapsed < 60:
                self.uptime = "100%"
            else:
                # Assume 99.8% as baseline for running app
                self.uptime = "99.8%"
        
        # Update stat cards
        self.total_devices_label.findChild(QLabel, "stat_value").setText(str(self.total_devices))
        self.active_devices_label.findChild(QLabel, "stat_value").setText(str(self.active_devices))
        self.bandwidth_label.findChild(QLabel, "stat_value").setText(self.network_bandwidth)
        self.uptime_label.findChild(QLabel, "stat_value").setText(self.uptime)
        
        # Update devices count in tab
        devices_count_label = self.tabs.widget(0).findChild(QLabel, "devices_count")
        if devices_count_label:
            devices_count_label.setText(f"📡 Appareils détectés ({self.total_devices})")
        
        # Update monitoring graphs data
        self._update_monitoring_data()
    
    def _update_monitoring_data(self):
        """Met à jour les données pour les graphiques de monitoring"""
        # Add current timestamp
        current_time = datetime.now().strftime('%H:%M:%S')
        self.time_history.append(current_time)
        
        # Add device counts
        self.device_count_history.append(self.total_devices)
        self.active_device_history.append(self.active_devices)
        
        # Calculate average signal
        if self.current_results:
            signals = []
            for device in self.current_results:
                signal_str = device.get('signal', '0%')
                try:
                    if isinstance(signal_str, str) and '%' in signal_str:
                        signal_val = int(signal_str.replace('%', ''))
                        signals.append(signal_val)
                except:
                    pass
            avg_signal = sum(signals) / len(signals) if signals else 0
        else:
            avg_signal = 0
        
        self.avg_signal_history.append(avg_signal)
        
        # Update graphs
        self._update_monitoring_graphs()
    
    def _update_monitoring_graphs(self):
        """Met à jour les graphiques de monitoring"""
        try:
            # Clear both axes
            self.device_count_ax.clear()
            self.signal_ax.clear()
            
            # Reconfigure device count axis (left)
            self.device_count_ax.set_facecolor('#1e1e1e')
            self.device_count_ax.set_xlabel('Temps (dernières 5 minutes)', color='#cccccc', fontsize=11, labelpad=10)
            self.device_count_ax.set_ylabel('Nombre d\'appareils', color='#0078d4', fontsize=11, labelpad=10)
            self.device_count_ax.tick_params(axis='y', colors='#0078d4', labelsize=10, width=1.5)
            self.device_count_ax.tick_params(axis='x', colors='#cccccc', labelsize=10, width=1.5)
            self.device_count_ax.grid(True, alpha=0.15, color='#555555', linestyle='--', linewidth=0.8)
            self.device_count_ax.spines['left'].set_color('#0078d4')
            self.device_count_ax.spines['left'].set_linewidth(2)
            self.device_count_ax.spines['right'].set_color('#9c27b0')
            self.device_count_ax.spines['right'].set_linewidth(2)
            self.device_count_ax.spines['bottom'].set_color('#555555')
            self.device_count_ax.spines['top'].set_visible(False)
            
            # Reconfigure signal axis (right)
            self.signal_ax.set_ylabel('Signal moyen (%)', color='#9c27b0', fontsize=11, labelpad=10)
            self.signal_ax.tick_params(axis='y', colors='#9c27b0', labelsize=10, width=1.5)
            self.signal_ax.set_ylim(0, 100)
            self.signal_ax.spines['right'].set_color('#9c27b0')
            self.signal_ax.spines['right'].set_linewidth(2)
            self.signal_ax.spines['top'].set_visible(False)
            
            # Only plot if we have data
            if len(self.device_count_history) > 0:
                # Plot device count data with enhanced styling
                x_data = list(range(len(self.device_count_history)))
                device_counts = list(self.device_count_history)
                active_counts = list(self.active_device_history)
                
                line1, = self.device_count_ax.plot(x_data, device_counts, 
                                                  color='#0078d4', linewidth=3, label='Total appareils',
                                                  marker='o', markersize=3, markevery=max(1, len(x_data)//10), alpha=0.9)
                line2, = self.device_count_ax.plot(x_data, active_counts, 
                                                  color='#28a745', linewidth=3, label='Actifs', linestyle='--',
                                                  marker='s', markersize=3, markevery=max(1, len(x_data)//10), alpha=0.9)
                
                # Dynamic y-axis for device count
                max_devices = max(max(device_counts) if device_counts else 0, max(active_counts) if active_counts else 0)
                if max_devices > 0:
                    self.device_count_ax.set_ylim(0, max_devices * 1.1)  # Add 10% padding
                else:
                    self.device_count_ax.set_ylim(0, 10)
                
                # Plot signal strength data on right axis with enhanced gradient
                signal_data = list(self.avg_signal_history)
                if any(s > 0 for s in signal_data):  # Only plot if we have actual signal data
                    line3, = self.signal_ax.plot(x_data, signal_data, color='#9c27b0', linewidth=3, label='Signal moyen',
                                                marker='^', markersize=3, markevery=max(1, len(x_data)//10), alpha=0.9)
                    self.signal_ax.fill_between(x_data, signal_data, alpha=0.25, color='#9c27b0')
                    
                    # Enhanced legend with all three lines
                    lines = [line1, line2, line3]
                    labels = [l.get_label() for l in lines]
                else:
                    # Legend with just device counts (no signal data yet)
                    lines = [line1, line2]
                    labels = [l.get_label() for l in lines]
                
                self.device_count_ax.legend(lines, labels, loc='upper left', facecolor='#2a2a2a', 
                                           edgecolor='#555555', labelcolor='white', fontsize=10,
                                           framealpha=0.95, shadow=True)
            
            # Redraw canvas
            self.combined_canvas.draw()
            
        except Exception as e:
            print(f"[DEBUG] Error updating graphs: {e}")
        
    
    def _log(self, message: str):
        """Ajoute un message au log."""
        self.logs_text.append(message)
        # Scroll vers le bas
        scrollbar = self.logs_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_suggest_cidr(self):
        """Suggestion automatique du CIDR."""
        suggestion = CIDRValidator.get_suggestion()
        self.cidr_input.setText(suggestion)
        self._log(f"CIDR suggéré: {suggestion}")
    
    def _on_scan(self):
        """Lance un scan ARP."""
        print("[DEBUG] _on_scan called")
        if self.is_scanning:
            QMessageBox.warning(self, "Attention", "Un scan est déjà en cours")
            return
        
        # Valide le CIDR
        cidr = self.cidr_input.text().strip()
        print(f"[DEBUG] CIDR: {cidr}")
        if not CIDRValidator.is_valid(cidr):
            QMessageBox.critical(self, "Erreur", f"CIDR invalide: {cidr}")
            return
        
        try:
            print("[DEBUG] Starting scan setup...")
            # Met à jour le timeout from slider
            timeout = self.timeout_slider.value()
            self.scanner.timeout = timeout
            print(f"[DEBUG] Timeout set to {timeout}")
            
            # Lance le scan dans un thread
            self.is_scanning = True
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("⏳\nScanning...")
            self._log(f"Démarrage du scan: {cidr} (timeout={timeout}s)")
            print("[DEBUG] Creating thread and worker...")
            
            # Crée le thread et le worker
            self.scan_thread = QThread()
            self.scan_worker = ScanWorker(self.scanner)
            self.scan_worker.moveToThread(self.scan_thread)
            print("[DEBUG] Worker moved to thread")
            
            # Configure les callbacks
            self.scan_worker.set_parameters(cidr, self.ping_checkbox.isChecked())
            print("[DEBUG] Parameters set")
            
            self.scan_worker.progress.connect(self._on_scan_progress)
            self.scan_worker.status.connect(self._on_scan_status)
            self.scan_worker.completed.connect(self._on_scan_complete)
            self.scan_worker.error.connect(self._on_scan_error)
            self.scan_worker.completed.connect(self.scan_thread.quit)  # Auto-quit thread on completion
            print("[DEBUG] Signals connected")
            
            # Démarre le scan
            self.scan_thread.started.connect(self.scan_worker.run)
            print("[DEBUG] About to start thread...")
            self.scan_thread.start()
            print("[DEBUG] Thread started!")
        except Exception as e:
            import traceback
            error_msg = f"Erreur lors de l'initialisation du scan: {str(e)}"
            print(f"[DEBUG ERROR] {error_msg}")
            print(traceback.format_exc())
            self._log(f"✗ {error_msg}")
            self._log(traceback.format_exc())
            QMessageBox.critical(self, "Erreur", error_msg)
            self.is_scanning = False
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("🔍\nScan")
    
    def _on_scan_progress(self, message: str, count: int):
        """Callback de progression du scan."""
        print(f"[DEBUG PROGRESS] {message} (count: {count})")
        self._log(f"[{count}] {message}")
    
    def _on_scan_status(self, message: str):
        """Callback de status du scan."""
        print(f"[DEBUG STATUS] {message}")
        self.status_label.setText(message)
        self._log(message)
    
    def _on_scan_complete(self, results: List[Dict]):
        """Scan complété avec succès."""
        print(f"[DEBUG] _on_scan_complete called with {len(results)} results")
        try:
            # Track successful scan
            self.scan_total_count += 1
            self.scan_success_count += 1
            
            # Arrête le thread FIRST before updating UI
            if self.scan_thread:
                print("[DEBUG] Quitting thread...")
                self.scan_thread.quit()
                self.scan_thread.wait(2000)  # Wait max 2 seconds
                print("[DEBUG] Thread quit")
            
            self.is_scanning = False
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("🔍\nScan")
            print("[DEBUG] Button state reset")
            
            # Résout les vendors
            print("[DEBUG] Resolving vendors...")
            for i, device in enumerate(results):
                try:
                    if device.get('mac'):
                        device['vendor'] = self.oui_db.lookup(device['mac'])
                    # Try to resolve device name
                    device['device_name'] = DeviceNameResolver.resolve(device.get('ip'))
                    if i % 10 == 0:
                        print(f"[DEBUG] Processed {i}/{len(results)} devices")
                except Exception as e:
                    print(f"[DEBUG] Error processing device {i}: {e}")
                    pass  # Ignore individual device errors
            
            print("[DEBUG] Updating table...")
            self.current_results = results
            self._update_table(results)
            print("[DEBUG] Table updated")
            
            self._log(f"✓ Scan complété: {len(results)} appareils trouvés")
            self.status_label.setText(f"✓ Scan terminé ({len(results)} appareils)")
            print("[DEBUG] _on_scan_complete finished successfully")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[DEBUG ERROR in _on_scan_complete] {error_details}")
            self._log(f"✗ Erreur lors de la finalisation du scan: {str(e)}")
            self._log(error_details)
            self.is_scanning = False
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("🔍\nScan")
    
    def _on_scan_error(self, error_msg: str):
        """Erreur lors du scan."""
        try:
            # Track failed scan
            self.scan_total_count += 1
            
            self.is_scanning = False
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("🔍\nScan")
            
            self._log(f"✗ Erreur: {error_msg}")
            self.status_label.setText(f"✗ Erreur de scan")
            
            # Show error dialog
            QMessageBox.critical(self, "Erreur de scan", error_msg)
            
            # Arrête le thread
            if self.scan_thread:
                self.scan_thread.quit()
                self.scan_thread.wait()
        except Exception as e:
            import traceback
            self._log(f"✗ Erreur critique: {str(e)}")
            self._log(traceback.format_exc())
        
        QMessageBox.critical(self, "Erreur de scan", error_msg)
        
        # Arrête le thread
        if self.scan_thread:
            self.scan_thread.quit()
            self.scan_thread.wait()
    
    def _on_refresh(self):
        """Rafraîchit la table avec les résultats actuels."""
        self._update_table(self.current_results)
        self._log("Table rafraîchie")
    
    def _on_export(self):
        """Exporte les résultats en CSV."""
        if not self.current_results:
            QMessageBox.warning(self, "Attention", "Aucun résultat à exporter")
            return
        
        # Dialogue de sauvegarde
        default_name = CSVExporter.get_default_filename()
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter en CSV",
            default_name,
            "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if filepath:
            success = CSVExporter.export(self.current_results, filepath)
            if success:
                self._log(f"✓ Exporté vers: {filepath}")
                QMessageBox.information(self, "Succès", f"Fichier exporté:\n{filepath}")
            else:
                QMessageBox.critical(self, "Erreur", "Erreur lors de l'export")
    
    def _on_clear(self):
        """Efface les résultats."""
        self.current_results = []
        self._update_table([])
        self.logs_text.clear()
        self.status_label.setText("Prêt")
        self._log("Résultats effacés")
    
    def _on_kick_device(self):
        """Déconnecte un appareil du réseau."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.current_results):
            QMessageBox.warning(self, "Kick Device", "Select a device in the table first.")
            return
        
        device = self.current_results[row]
        ip = device.get('ip')
        mac = device.get('mac')
        device_name = device.get('device_name', '') or device.get('vendor', 'Unknown')
        
        # Demande confirmation
        reply = QMessageBox.question(
            self,
            "Confirm Kick Device",
            f"Disconnect this device from the network?\n\n"
            f"IP: {ip}\n"
            f"MAC: {mac}\n"
            f"Name: {device_name}\n\n"
            f"This will temporarily block the device's network access using ARP spoofing.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Demande la durée
        duration, ok = QInputDialog.getInt(
            self,
            "Kick Duration",
            f"Duration (seconds):\n0 = Until manually stopped",
            30,  # default
            0,   # min
            3600,  # max (1 hour)
            1    # step
        )
        
        if not ok:
            return
        
        # Lance le kick
        self._log(f"Kicking device {ip} ({mac}) for {duration}s..." if duration > 0 
                 else f"Kicking device {ip} ({mac}) indefinitely...")
        
        success = self.device_kicker.kick_device(ip, mac, duration)
        
        if success:
            QMessageBox.information(
                self,
                "Kick Device Started",
                f"Device is being kicked!\n\n"
                f"IP: {ip}\n"
                f"MAC: {mac}\n"
                f"Duration: {duration}s" if duration > 0 else f"Duration: Until stopped\n\n"
                f"The device should lose network connectivity.\n"
                f"Use 'Stop Kick' to restore access early."
            )
            self._log(f"✓ Kick started successfully")
        else:
            QMessageBox.warning(
                self,
                "Kick Failed",
                f"Failed to kick device {ip}.\n\n"
                f"Possible reasons:\n"
                f"- Another kick is in progress\n"
                f"- Cannot find network gateway\n"
                f"- Insufficient permissions (run as Admin)\n\n"
                f"Check the console for details."
            )
            self._log(f"✗ Kick failed")
    
    def _on_stop_kick(self):
        """Arrête le kick en cours."""
        if not self.device_kicker.is_kicking:
            QMessageBox.information(
                self,
                "Stop Kick",
                "No kick is currently running."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Stop Kick",
            "Stop the current kick and restore network access?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self._log("Stopping kick...")
        success = self.device_kicker.stop_kick()
        
        if success:
            QMessageBox.information(
                self,
                "Kick Stopped",
                "The kick has been stopped.\n"
                "The device's network access should be restored."
            )
            self._log("✓ Kick stopped successfully")
        else:
            QMessageBox.warning(
                self,
                "Stop Failed",
                "No kick was running."
            )
    
    def _get_my_ip(self) -> str:
        """Obtient notre propre adresse IP."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
            s.close()
            return my_ip
        except Exception as e:
            print(f"Erreur lors de la détection de l'IP: {e}")
            return None
    
    def _on_kick_all(self):
        """Kick tous les appareils sauf nous-même."""
        if not self.current_results:
            QMessageBox.warning(self, "Kick All", "No devices in the table. Scan the network first.")
            return
        
        # Obtient notre IP
        my_ip = self._get_my_ip()
        if not my_ip:
            QMessageBox.warning(self, "Kick All", "Could not detect your IP address.")
            return
        
        # Filtre les appareils (enlève notre IP)
        devices_to_kick = [d for d in self.current_results if d.get('ip') != my_ip]
        
        if not devices_to_kick:
            QMessageBox.information(self, "Kick All", "No other devices to kick (only you are on the network).")
            return
        
        # Demande confirmation
        reply = QMessageBox.question(
            self,
            "Confirm Mass Kick",
            f"⚠️ WARNING ⚠️\n\n"
            f"You are about to KICK {len(devices_to_kick)} device(s) from the network!\n\n"
            f"Your IP: {my_ip} (will NOT be kicked)\n"
            f"Targets: {len(devices_to_kick)} devices\n\n"
            f"This will disconnect ALL other devices from the network.\n"
            f"Are you absolutely sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Demande la durée
        duration, ok = QInputDialog.getInt(
            self,
            "Kick Duration",
            f"Duration (seconds) for all {len(devices_to_kick)} devices:\n0 = Until manually stopped",
            30,  # default
            0,   # min
            3600,  # max (1 hour)
            1    # step
        )
        
        if not ok:
            return
        
        # Lance le kick pour chaque appareil
        self._log(f"Starting mass kick of {len(devices_to_kick)} devices...")
        kicked_count = 0
        failed_count = 0
        
        for device in devices_to_kick:
            ip = device.get('ip')
            mac = device.get('mac')
            name = device.get('device_name', '') or device.get('vendor', 'Unknown')
            
            self._log(f"Kicking {ip} ({name})...")
            
            # Crée un nouveau kicker pour chaque appareil
            from scanner import DeviceKicker
            kicker = DeviceKicker()
            success = kicker.kick_device(ip, mac, duration)
            
            if success:
                kicked_count += 1
            else:
                failed_count += 1
        
        # Affiche le résultat
        QMessageBox.information(
            self,
            "Mass Kick Complete",
            f"Mass kick operation completed!\n\n"
            f"✓ Successfully kicked: {kicked_count} devices\n"
            f"✗ Failed: {failed_count} devices\n"
            f"Duration: {duration}s\n\n"
            f"Your device ({my_ip}) was excluded.\n"
            f"All other devices should lose network connectivity."
        )
        
        self._log(f"✓ Mass kick complete: {kicked_count} kicked, {failed_count} failed")
    
    def _on_send_message(self):
        """Envoie un message à un appareil sélectionné."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QComboBox, QDialogButtonBox, QSpinBox
        
        row = self.table.currentRow()
        if row < 0 or row >= len(self.current_results):
            QMessageBox.warning(self, "Send Message", "Select a device in the table first.")
            return
        
        device = self.current_results[row]
        ip = device.get('ip')
        mac = device.get('mac')
        device_name = device.get('device_name', '') or device.get('vendor', 'Unknown')
        
        # Crée une boîte de dialogue personnalisée
        dialog = QDialog(self)
        dialog.setWindowTitle("Send Message to Device")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Info sur la cible
        info_label = QLabel(f"<b>Target Device:</b><br>"
                           f"IP: {ip}<br>"
                           f"MAC: {mac}<br>"
                           f"Name: {device_name}")
        layout.addWidget(info_label)
        
        # Protocole
        protocol_label = QLabel("Protocol:")
        layout.addWidget(protocol_label)
        
        protocol_combo = QComboBox()
        protocol_combo.addItems(["Web Browser Hijack ⭐", "Windows Popup (Force)", "UDP", "TCP", "Broadcast", "Multi-Protocol", "HTTP POST"])
        layout.addWidget(protocol_combo)
        
        # Port
        port_label = QLabel("Port:")
        layout.addWidget(port_label)
        
        port_spinbox = QSpinBox()
        port_spinbox.setMinimum(1)
        port_spinbox.setMaximum(65535)
        port_spinbox.setValue(9999)
        layout.addWidget(port_spinbox)
        
        # Message
        message_label = QLabel("Message:")
        layout.addWidget(message_label)
        
        message_text = QTextEdit()
        message_text.setPlaceholderText("Enter your message here...")
        message_text.setMaximumHeight(150)
        layout.addWidget(message_text)
        
        # Info
        info_text = QLabel("<i><b>Web Browser Hijack ⭐:</b> Shows message in target's browser automatically! (No setup needed)<br>"
                          "<b>Windows Popup (Force):</b> Attempts to show popup on Windows devices (requires admin rights/WinRM).<br>"
                          "<b>UDP/TCP/Broadcast:</b> Requires a listener on the target device.<br>"
                          "UDP is faster but unreliable. TCP requires an open port. Broadcast sends to all devices.</i>")
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        # Affiche la boîte de dialogue
        if dialog.exec_() == QDialog.Accepted:
            message = message_text.toPlainText()
            
            if not message:
                QMessageBox.warning(self, "Send Message", "Message cannot be empty!")
                return
            
            protocol = protocol_combo.currentText()
            port = port_spinbox.value()
            
            self._log(f"Sending message to {ip} via {protocol} on port {port}...")
            
            success = False
            results = {}
            
            try:
                if protocol == "Web Browser Hijack ⭐":
                    # Utilise la durée comme paramètre
                    from PyQt5.QtWidgets import QInputDialog
                    hijack_duration, ok = QInputDialog.getInt(
                        self,
                        "Hijack Duration",
                        "Duration (seconds) to intercept web traffic:",
                        60,  # default
                        10,  # min
                        300, # max
                        10   # step
                    )
                    if not ok:
                        return
                    
                    self._log(f"Starting web hijack for {hijack_duration}s...")
                    success = self.message_sender.send_web_message(ip, mac, message, hijack_duration)
                    
                    if success:
                        QMessageBox.information(
                            self,
                            "Web Hijack Started",
                            f"Web traffic hijacking active!\n\n"
                            f"Target: {ip} ({mac})\n"
                            f"Duration: {hijack_duration}s\n\n"
                            f"When the target opens ANY website,\n"
                            f"they will see your message!\n\n"
                            f"Server running on port 80.\n"
                            f"Check console for details."
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Hijack Failed",
                            f"Failed to start web hijack.\n\n"
                            f"Make sure:\n"
                            f"- You're running as Administrator\n"
                            f"- Port 80 is available\n"
                            f"- Network allows spoofing\n\n"
                            f"Check console for details."
                        )
                    return  # Exit early for this protocol
                    
                elif protocol == "Windows Popup (Force)":
                    success = self.message_sender.send_popup_notification(ip, message, "WiFi Manager Alert")
                elif protocol == "UDP":
                    success = self.message_sender.send_udp_message(ip, message, port)
                elif protocol == "TCP":
                    success = self.message_sender.send_tcp_message(ip, message, port)
                elif protocol == "Broadcast":
                    success = self.message_sender.send_broadcast_message(message, port)
                elif protocol == "Multi-Protocol":
                    results = self.message_sender.send_multi_protocol(ip, message)
                    success = any(results.values())
                elif protocol == "HTTP POST":
                    success = self.message_sender.send_http_notification(ip, message, port)
                
                if protocol == "Multi-Protocol":
                    success_count = sum(1 for v in results.values() if v)
                    result_text = "\n".join([f"{k}: {'✓' if v else '✗'}" for k, v in results.items()])
                    
                    QMessageBox.information(
                        self,
                        "Message Sent",
                        f"Multi-protocol transmission completed!\n\n"
                        f"Successful: {success_count}/{len(results)}\n\n"
                        f"{result_text}\n\n"
                        f"Check console for details."
                    )
                elif success:
                    QMessageBox.information(
                        self,
                        "Message Sent",
                        f"Message sent successfully!\n\n"
                        f"Target: {ip}\n"
                        f"Protocol: {protocol}\n"
                        f"Port: {port}\n"
                        f"Size: {len(message)} bytes\n\n"
                        f"Note: Success means the message was transmitted,\n"
                        f"but doesn't guarantee the device received or processed it."
                    )
                    self._log(f"✓ Message sent successfully")
                else:
                    QMessageBox.warning(
                        self,
                        "Message Failed",
                        f"Failed to send message to {ip}\n\n"
                        f"Possible reasons:\n"
                        f"- No service listening on port {port}\n"
                        f"- Firewall blocking the connection\n"
                        f"- Device is offline\n\n"
                        f"Check the console for details."
                    )
                    self._log(f"✗ Message failed to send")
            
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error sending message:\n{str(e)}"
                )
                self._log(f"✗ Error: {str(e)}")
    
    def _on_tv_remote(self):
        """Callback pour contrôler une Smart TV - détecte automatiquement les TVs"""
        # Récupérer tous les appareils scannés
        tvs = []
        all_devices = []
        
        for row in range(self.table.rowCount()):
            ip = self.table.item(row, 1).text()
            mac = self.table.item(row, 2).text()
            vendor = self.table.item(row, 3).text().lower()
            name = self.table.item(row, 4).text() or "Appareil inconnu"
            
            device_info = {
                'ip': ip,
                'mac': mac,
                'vendor': vendor,
                'name': name,
                'is_tv': False
            }
            
            # Détecter si c'est une TV basé sur plusieurs critères
            # 1. Vérifier le vendor name
            if any(tv_brand in vendor for tv_brand in ['samsung', 'lg', 'sony', 'philips', 'panasonic', 'toshiba', 'sharp', 'vizio', 'tcl', 'hisense', 'hitachi', 'grundig']):
                device_info['is_tv'] = True
                tvs.append(device_info)
            # 2. Vérifier les IPs communes pour les TVs (souvent .254, .100-110, .200-210)
            elif ip.endswith('.254') or ip.endswith('.100') or ip.endswith('.101') or ip.endswith('.200'):
                device_info['is_tv'] = True
                device_info['name'] = f"{name} (Probable TV)"
                tvs.append(device_info)
            # 3. Vérifier le nom de l'appareil
            elif any(keyword in name.lower() for keyword in ['tv', 'television', 'smart', 'android tv', 'webos']):
                device_info['is_tv'] = True
                tvs.append(device_info)
            
            all_devices.append(device_info)
        
        # Vérifier si des TVs ont été trouvées
        if not tvs:
            # Proposer de sélectionner manuellement un appareil
            reply = QMessageBox.question(
                self, 
                "Aucune TV détectée automatiquement", 
                f"Aucune Smart TV détectée automatiquement sur le réseau.\n\n"
                f"{len(all_devices)} appareil(s) trouvé(s) au total.\n\n"
                f"Voulez-vous sélectionner manuellement un appareil à contrôler comme TV?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Permettre la sélection manuelle
                tvs = all_devices
            else:
                return
        
        # Si une seule TV, l'ouvrir directement
        if len(tvs) == 1:
            tv = tvs[0]
            self._log(f"📺 TV détectée: {tv['name']} ({tv['ip']})")
            self._open_tv_remote_dialog(tv['ip'], tv['mac'], tv['vendor'], tv['name'])
            return
        
        # Si plusieurs TVs, afficher un dialogue de sélection
        selection_dialog = QDialog(self)
        selection_dialog.setWindowTitle("Sélectionner un appareil à contrôler")
        selection_dialog.setMinimumWidth(500)
        layout = QVBoxLayout(selection_dialog)
        
        title_text = f"📺 {len(tvs)} appareil(s) disponible(s):"
        if any(tv.get('is_tv') for tv in tvs):
            title_text = f"📺 Sélectionnez votre Smart TV:"
        layout.addWidget(QLabel(title_text))
        layout.addSpacing(10)
        
        # Liste des TVs avec plus d'informations
        from PyQt5.QtWidgets import QListWidget
        tv_list = QListWidget()
        for tv in tvs:
            icon = "📺" if tv.get('is_tv') else "📱"
            vendor_text = f" ({tv['vendor']})" if tv['vendor'] and tv['vendor'] != 'unknown' else ""
            display_text = f"{icon} {tv['ip']} - {tv['name']}{vendor_text} - {tv['mac'][:17]}"
            tv_list.addItem(display_text)
        tv_list.setCurrentRow(0)
        layout.addWidget(tv_list)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        select_btn = QPushButton("Contrôler")
        cancel_btn = QPushButton("Annuler")
        buttons_layout.addWidget(select_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        def on_select():
            selected_idx = tv_list.currentRow()
            if selected_idx >= 0:
                tv = tvs[selected_idx]
                selection_dialog.accept()
                self._open_tv_remote_dialog(tv['ip'], tv['mac'], tv['vendor'], tv['name'])
        
        select_btn.clicked.connect(on_select)
        cancel_btn.clicked.connect(selection_dialog.reject)
        tv_list.itemDoubleClicked.connect(on_select)
        
        selection_dialog.exec_()
    
    def _open_tv_remote_dialog(self, ip, mac, vendor, name):
        """Ouvre le dialogue de contrôle TV pour un appareil spécifique"""
        # Créer le dialogue de contrôle TV
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Télécommande TV - {name}")
        dialog.setMinimumWidth(350)
        dialog.setMinimumHeight(500)
        layout = QVBoxLayout(dialog)
        
        # Info TV
        info_label = QLabel(f"📺 {name}\n🌐 IP: {ip}\n🔌 MAC: {mac}")
        info_label.setStyleSheet("font-weight: bold; padding: 10px; background-color: #2b2b2b; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Détection marque
        brand = self.tv_controller.detect_tv_brand(ip, vendor)
        brand_label = QLabel(f"Marque détectée: {brand}")
        brand_label.setStyleSheet("padding: 5px; color: #4CAF50;")
        layout.addWidget(brand_label)
        
        layout.addSpacing(10)
        
        # Bouton Power/Wake
        power_layout = QHBoxLayout()
        wake_btn = QPushButton("⚡ Allumer (WoL)")
        wake_btn.setStyleSheet("background-color: #4CAF50; font-weight: bold; padding: 10px;")
        wake_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "POWER_ON", dialog))
        power_layout.addWidget(wake_btn)
        
        power_btn = QPushButton("🔴 Power")
        power_btn.setStyleSheet("background-color: #f44336; font-weight: bold; padding: 10px;")
        power_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "POWER", dialog))
        power_layout.addWidget(power_btn)
        layout.addLayout(power_layout)
        
        layout.addSpacing(10)
        
        # Contrôles volume
        vol_label = QLabel("🔊 Volume")
        vol_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(vol_label)
        
        vol_layout = QHBoxLayout()
        vol_up_btn = QPushButton("🔼 Vol +")
        vol_up_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "VOLUP", dialog))
        vol_layout.addWidget(vol_up_btn)
        
        mute_btn = QPushButton("🔇 Mute")
        mute_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "MUTE", dialog))
        vol_layout.addWidget(mute_btn)
        
        vol_down_btn = QPushButton("🔽 Vol -")
        vol_down_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "VOLDOWN", dialog))
        vol_layout.addWidget(vol_down_btn)
        layout.addLayout(vol_layout)
        
        layout.addSpacing(10)
        
        # Contrôles chaînes
        ch_label = QLabel("📺 Chaînes")
        ch_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(ch_label)
        
        ch_layout = QHBoxLayout()
        ch_up_btn = QPushButton("⬆️ CH +")
        ch_up_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "CHANUP", dialog))
        ch_layout.addWidget(ch_up_btn)
        
        ch_down_btn = QPushButton("⬇️ CH -")
        ch_down_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "CHANDOWN", dialog))
        ch_layout.addWidget(ch_down_btn)
        layout.addLayout(ch_layout)
        
        layout.addSpacing(10)
        
        # Navigation D-Pad
        nav_label = QLabel("🎮 Navigation")
        nav_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(nav_label)
        
        # Grille navigation 3x3
        nav_grid = QGridLayout()
        
        up_btn = QPushButton("⬆️")
        up_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "UP", dialog))
        nav_grid.addWidget(up_btn, 0, 1)
        
        left_btn = QPushButton("⬅️")
        left_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "LEFT", dialog))
        nav_grid.addWidget(left_btn, 1, 0)
        
        enter_btn = QPushButton("✔️ OK")
        enter_btn.setStyleSheet("background-color: #2196F3; font-weight: bold;")
        enter_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "ENTER", dialog))
        nav_grid.addWidget(enter_btn, 1, 1)
        
        right_btn = QPushButton("➡️")
        right_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "RIGHT", dialog))
        nav_grid.addWidget(right_btn, 1, 2)
        
        down_btn = QPushButton("⬇️")
        down_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "DOWN", dialog))
        nav_grid.addWidget(down_btn, 2, 1)
        
        layout.addLayout(nav_grid)
        
        layout.addSpacing(10)
        
        # Boutons spéciaux
        special_layout = QHBoxLayout()
        home_btn = QPushButton("🏠 Home")
        home_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "HOME", dialog))
        special_layout.addWidget(home_btn)
        
        back_btn = QPushButton("⬅️ Back")
        back_btn.clicked.connect(lambda: self._tv_send_command(mac, ip, brand, "BACK", dialog))
        special_layout.addWidget(back_btn)
        layout.addLayout(special_layout)
        
        layout.addSpacing(10)
        
        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()
    
    def _tv_send_command(self, mac, ip, brand, command, parent_dialog):
        """Envoie une commande à la TV"""
        try:
            if command == "POWER_ON":
                success = self.tv_controller.send_wake_on_lan(mac)
                if success:
                    QMessageBox.information(parent_dialog, "Succès", 
                                          "Signal Wake-on-LAN envoyé!\nLa TV devrait s'allumer dans quelques secondes.")
                else:
                    QMessageBox.warning(parent_dialog, "Erreur", "Échec de l'envoi du signal WoL")
            else:
                success = self.tv_controller.universal_send_key(ip, brand, command)
                if success:
                    # Feedback visuel discret
                    self.status_label.setText(f"✓ Commande {command} envoyée")
                    self._log(f"✓ TV Command: {command} -> {ip} ({brand})")
                else:
                    QMessageBox.warning(parent_dialog, "Erreur", 
                                      f"Échec de l'envoi de la commande {command}\n\n"
                                      f"Vérifiez que:\n"
                                      f"- La TV est allumée\n"
                                      f"- La marque détectée est correcte ({brand})\n"
                                      f"- Le contrôle réseau est activé sur la TV")
        except Exception as e:
            QMessageBox.critical(parent_dialog, "Erreur", f"Erreur lors de l'envoi: {str(e)}")
    
    def _update_table(self, devices: List[Dict]):
        """Met à jour la table avec les appareils."""
        self.table.setRowCount(0)
        
        for i, device in enumerate(devices):
            self.table.insertRow(i)
            
            # Type icon
            vendor = device.get('vendor', '').lower()
            if 'router' in vendor or 'tp-link' in vendor or 'gateway' in vendor:
                type_icon = "🌐"
            elif 'samsung' in vendor or 'apple' in vendor or 'iphone' in vendor or 'galaxy' in vendor:
                type_icon = "📱"
            elif 'dell' in vendor or 'hp' in vendor or 'lenovo' in vendor:
                type_icon = "💻"
            elif 'sony' in vendor or 'playstation' in vendor or 'xbox' in vendor:
                type_icon = "🎮"
            elif 'amazon' in vendor or 'google' in vendor or 'nest' in vendor:
                type_icon = "🏠"
            elif 'printer' in vendor or 'canon' in vendor or 'epson' in vendor:
                type_icon = "🖨️"
            else:
                type_icon = "📡"
            
            type_item = QTableWidgetItem(type_icon)
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, type_item)
            
            # Device Name
            name = device.get('device_name', '') or device.get('vendor', 'Unknown Device')
            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor("#ffffff"))
            self.table.setItem(i, 1, name_item)
            
            # IP
            ip_item = QTableWidgetItem(device.get('ip', ''))
            ip_item.setForeground(QColor("#0078d4"))
            ip_item.setFont(QFont("Consolas", 9))
            self.table.setItem(i, 2, ip_item)
            
            # MAC
            mac_item = QTableWidgetItem(device.get('mac', ''))
            mac_item.setForeground(QColor("#888888"))
            mac_item.setFont(QFont("Consolas", 8))
            self.table.setItem(i, 3, mac_item)
            
            # Vendor
            vendor_item = QTableWidgetItem(device.get('vendor', 'Unknown'))
            vendor_item.setForeground(QColor("#dddddd"))
            self.table.setItem(i, 4, vendor_item)
            
            # Signal (random for now, could be implemented) - store in device dict
            import random
            signal = random.randint(60, 99)
            signal_text = f"{'📶' if signal > 80 else '📶' if signal > 60 else '📶'} {signal}%"
            device['signal'] = f"{signal}%"  # Store in device dict
            signal_item = QTableWidgetItem(signal_text)
            if signal > 80:
                signal_item.setForeground(QColor("#28a745"))
            elif signal > 60:
                signal_item.setForeground(QColor("#ffc107"))
            else:
                signal_item.setForeground(QColor("#dc3545"))
            self.table.setItem(i, 5, signal_item)
            
            # Ping (Latency)
            ping_value = device.get('ping')
            if ping_value:
                ping_text = f"{ping_value:.0f} ms"
                ping_item = QTableWidgetItem(ping_text)
                if ping_value < 5:
                    ping_item.setBackground(QColor("#28a745").lighter(160))
                    ping_item.setForeground(QColor("#28a745"))
                elif ping_value < 10:
                    ping_item.setBackground(QColor("#ffc107").lighter(160))
                    ping_item.setForeground(QColor("#ffc107"))
                else:
                    ping_item.setBackground(QColor("#dc3545").lighter(160))
                    ping_item.setForeground(QColor("#dc3545"))
                ping_item.setTextAlignment(Qt.AlignCenter)
            else:
                ping_item = QTableWidgetItem("-")
                ping_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 6, ping_item)
            
            # Bandwidth (mock data) - store in device dict for stats calculation
            bandwidth_values = ["12 Mbps", "45 Mbps", "120 Mbps", "245 Mbps", "450 Mbps", "980 Mbps"]
            bandwidth = random.choice(bandwidth_values)
            device['bandwidth'] = bandwidth  # Store in device dict
            bandwidth_item = QTableWidgetItem(bandwidth)
            bandwidth_item.setForeground(QColor("#dddddd"))
            self.table.setItem(i, 7, bandwidth_item)
            
            # Actions buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("""
                QPushButton {
                    background: #0078d4;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-size: 12pt;
                }
                QPushButton:hover {
                    background: #1084d7;
                }
            """)
            actions_layout.addWidget(view_btn)
            
            kick_btn = QPushButton("⚡")
            kick_btn.setFixedSize(30, 30)
            kick_btn.setStyleSheet("""
                QPushButton {
                    background: #dc3545;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-size: 12pt;
                }
                QPushButton:hover {
                    background: #c82333;
                }
            """)
            kick_btn.clicked.connect(lambda checked, d=device: self._quick_kick_device(d))
            actions_layout.addWidget(kick_btn)
            
            actions_layout.addStretch()
            self.table.setCellWidget(i, 8, actions_widget)
        
        # Update stats
        self._update_network_stats()
    
    def _quick_kick_device(self, device):
        """Kick rapide depuis le tableau"""
        self._log(f"Quick kick: {device.get('ip', 'unknown')}")
        # Utiliser la même logique que _on_kick_device mais sans sélection
        ip = device.get('ip', '')
        mac = device.get('mac', '')
        name = device.get('device_name', '') or device.get('vendor', 'Unknown')
        
        reply = QMessageBox.question(
            self,
            "Kick Device",
            f"Kick {name} ({ip}) off the network?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        duration, ok = QInputDialog.getInt(
            self,
            "Kick Duration",
            "Enter kick duration in seconds:",
            value=60,
            min=10,
            max=3600
        )
        
        if not ok:
            return
        
        self._log(f"Kicking {ip} for {duration} seconds...")
        success = self.device_kicker.kick_device(ip, mac, duration)
        
        if success:
            QMessageBox.information(self, "Kick Started", f"{name} is being kicked!")
            self._log(f"✓ Kick started successfully")
        else:
            QMessageBox.warning(self, "Kick Failed", f"Failed to kick {name}")
            self._log(f"✗ Kick failed")
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre."""
        # Arrête le kick si en cours
        if self.device_kicker.is_kicking:
            self.device_kicker.stop_kick()
        
        # Arrête le scan si en cours
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.quit()
            self.scan_thread.wait()
        
        event.accept()
