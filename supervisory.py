import sys
import csv
import time
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QSlider, QStackedWidget, 
    QFrame, QSizePolicy, QFileDialog, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QColor, QIcon
import pyqtgraph as pg
import serial
import serial.tools.list_ports

INITIAL_SETPOINT = 12.5

# --- Sophisticated Dark Theme Constants ---
BG_DEEP = "#0a0a0c"
BG_PANEL = "#141417"
BG_CARD = "#1c1c21"
ACCENT_CYAN = "#00f2ff"
ACCENT_ROSE = "#ff2d55"
ACCENT_GREEN = "#00e676"
ACCENT_AMBER = "#ffab00"
TEXT_PRIMARY = "#f0f0f5"
TEXT_SECONDARY = "#8e8e99"
BORDER = "#2d2d35"

# --- QSS Stylesheet ---
STYLESHEET = f"""
QMainWindow {{
    background-color: {BG_DEEP};
}}

QWidget {{
    color: {TEXT_PRIMARY};
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

QFrame#Sidebar {{
    background-color: {BG_PANEL};
    border-right: 1px solid {BORDER};
}}

QFrame#Card {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QPushButton {{
    background-color: transparent;
    border: none;
    color: {TEXT_SECONDARY};
    padding: 12px 24px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    border-left: 3px solid transparent;
}}

QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.02);
    color: {TEXT_PRIMARY};
}}

QPushButton[active="true"] {{
    background-color: rgba(0, 242, 255, 0.05);
    color: {TEXT_PRIMARY};
    border-left: 3px solid {ACCENT_CYAN};
}}

QPushButton#ActionBtn {{
    background-color: {ACCENT_CYAN};
    color: {BG_DEEP};
    border-radius: 6px;
    font-weight: 600;
    text-align: center;
    padding: 8px;
}}

QPushButton#ActionBtn:hover {{
    background-color: #33f5ff;
}}

QPushButton#ActionBtn:disabled {{
    background-color: #1c1c21;
    color: {TEXT_SECONDARY};
}}

QPushButton#DangerBtn {{
    background-color: {ACCENT_ROSE};
    color: white;
    border-radius: 6px;
    font-weight: 600;
    text-align: center;
    padding: 8px;
}}

QPushButton#DangerBtn:hover {{
    background-color: #ff5577;
}}

QPushButton#DangerBtn:disabled {{
    background-color: #1c1c21;
    color: {TEXT_SECONDARY};
}}

QPushButton#SecondaryBtn {{
    background-color: transparent;
    border: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
    border-radius: 6px;
    text-align: center;
    padding: 8px;
}}

QPushButton#SecondaryBtn:hover {{
    background-color: rgba(255, 255, 255, 0.02);
}}

QPushButton#OutlineBtn {{
    background-color: transparent;
    border: 1px solid {ACCENT_CYAN};
    color: {ACCENT_CYAN};
    border-radius: 6px;
    text-align: center;
    padding: 8px;
}}

QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px;
    color: white;
    font-family: 'JetBrains Mono', monospace;
}}

QSlider::groove:horizontal {{
    border: 1px solid {BORDER};
    height: 4px;
    background: {BG_CARD};
    margin: 2px 0;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT_CYAN};
    border: 1px solid {ACCENT_CYAN};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}

QListWidget {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    outline: none;
}}

QListWidget::item {{
    padding: 10px 14px;
    border-bottom: 1px solid {BORDER};
    border-radius: 0px;
}}

QListWidget::item:selected {{
    background-color: rgba(0, 242, 255, 0.1);
    color: {ACCENT_CYAN};
    border-left: 3px solid {ACCENT_CYAN};
}}

QListWidget::item:hover:!selected {{
    background-color: rgba(255, 255, 255, 0.03);
}}
"""

class ArduinoController:
    def __init__(self, baudrate=9600):
        self.ser = None
        self.baudrate = baudrate
        self.setpoint = INITIAL_SETPOINT
        self.p, self.i, self.d = 12.5, 0.85, 2.1
        self.last_pos = 0.0

    def connect(self, porta):
        try:
            self.ser = serial.Serial(porta, self.baudrate, timeout=0.1)
            line = ""
            timeout_start = time.time()
            while "system ready" not in line.lower():
                if time.time() - timeout_start > 5:
                    # Timeout after 5s — assume connected anyway
                    break
                raw = self.ser.readline()
                if raw:
                    line = raw.decode('utf-8', errors='ignore').strip()
            print(f"Arduino connected on {porta}!")
            return True
        except Exception as e:
            print(f"Error on port {porta}: {e}")
            return False

    def disconnect(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.ser = None
                print("Arduino disconnected.")
                return True
        except Exception as e:
            print(f"Error disconnecting: {e}")
        return False

    @property
    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def send_command(self):
        if self.ser and self.ser.is_open:
            packet = f"SP:{self.setpoint};P:{self.p};I:{self.i};D:{self.d}\n"
            try:
                self.ser.write(packet.encode('utf-8'))
            except Exception as e:
                print(f"Error sending command: {e}")
        else:
            print("Error: serial port not open.")

    def receive_command(self):
        if self.ser and self.ser.is_open:
            while self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        self.last_pos = float(line)
                except Exception:
                    pass
        
        error = self.setpoint - self.last_pos
        return self.last_pos, self.setpoint, error


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supervisório Atuador Pneumático")
        self.resize(1280, 700)
        self.setStyleSheet(STYLESHEET)
        
        self.history = {"time": [], "pos": [], "setpoint": [], "error": []}
        self.start_time = time.time()
        self.is_running = False
        self.sliding_window_enabled = True
        
        self.serialArduino = ArduinoController()
        
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(50)  # 20Hz
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 24, 0, 24)
        
        brand = QLabel("PNEUMATIC CONTROL")
        brand.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: bold; letter-spacing: 2px; padding: 0 20px 32px; font-size: 12px;")
        sidebar_layout.addWidget(brand)
        
        self.nav_btns = []
        for i, name in enumerate(["Supervisório", "Configurações"]):
            btn = QPushButton(name)
            btn.setProperty("active", i == 0)
            btn.clicked.connect(lambda checked, idx=i: self.switch_view(idx))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
            
        sidebar_layout.addStretch()

        # Connection status indicator in sidebar
        self.sidebar_status_label = QLabel("● DESCONECTADO")
        self.sidebar_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 10px; font-weight: bold; padding: 0 20px 12px;")
        sidebar_layout.addWidget(self.sidebar_status_label)
        
        self.start_stop_btn = QPushButton("INICIAR LEITURA")
        self.start_stop_btn.setObjectName("ActionBtn")
        self.start_stop_btn.setFixedWidth(180)
        self.start_stop_btn.setStyleSheet(f"margin: 0 15px; padding: 15px; text-align: center;")
        self.start_stop_btn.clicked.connect(self.toggle_reading)
        self.start_stop_btn.setEnabled(False)  # Disabled until connected
        sidebar_layout.addWidget(self.start_stop_btn)
        
        layout.addWidget(sidebar)
        
        # --- Content Area ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        self.init_supervisorio_view()
        self.init_config_view()
        
    def init_supervisorio_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        header = QLabel("Supervisório e Controle")
        header.setStyleSheet("font-size: 22px; font-weight: 600;")
        header_layout.addWidget(header)
        
        export_btn = QPushButton("Exportar Run (.CSV)")
        export_btn.setObjectName("OutlineBtn")
        export_btn.setFixedWidth(180)
        export_btn.clicked.connect(self.export_csv)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        grid = QHBoxLayout()
        grid.setSpacing(20)
        
        # --- Left Column ---
        ctrl_panel = QVBoxLayout()
        ctrl_panel.setSpacing(20)
        
        # Setpoint Card
        sp_card = QFrame()
        sp_card.setObjectName("Card")
        sp_card.setFixedWidth(300)
        sp_layout = QVBoxLayout(sp_card)
        
        sp_layout.addWidget(QLabel("CONTROLE DE SETPOINT", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;"))
        sp_layout.addSpacing(10)
        
        label = QLabel("Posição Alvo (cm)")
        label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        sp_layout.addWidget(label)
        
        self.sp_input = QLineEdit(str(INITIAL_SETPOINT))
        sp_layout.addWidget(self.sp_input)
        
        self.sp_slider = QSlider(Qt.Horizontal)
        self.sp_slider.setRange(0, 25)
        self.sp_slider.setValue(int(INITIAL_SETPOINT))
        self.sp_slider.valueChanged.connect(self.on_slider_change)
        sp_layout.addWidget(self.sp_slider)
        
        send_btn = QPushButton("Enviar Setpoint")
        send_btn.setObjectName("ActionBtn")
        send_btn.clicked.connect(self.on_send_setpoint)
        sp_layout.addWidget(send_btn)
        
        ctrl_panel.addWidget(sp_card)
        
        # PID Card
        pid_card = QFrame()
        pid_card.setObjectName("Card")
        pid_card.setFixedWidth(300)
        pid_layout = QVBoxLayout(pid_card)
        
        pid_layout.addWidget(QLabel("PARÂMETROS PID", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;"))
        pid_layout.addSpacing(10)
        
        self.kp_input = QLineEdit("12.5")
        self.ki_input = QLineEdit("0.85")
        self.kd_input = QLineEdit("2.1")
        
        for label_text, input_widget in [("Kp", self.kp_input), ("Ki", self.ki_input), ("Kd", self.kd_input)]:
            pid_layout.addWidget(QLabel(label_text, styleSheet=f"color: {TEXT_SECONDARY}; font-size: 11px;"))
            pid_layout.addWidget(input_widget)
            
        update_btn = QPushButton("Atualizar Ganhos")
        update_btn.setObjectName("ActionBtn")
        update_btn.clicked.connect(self.on_update_pid)
        pid_layout.addWidget(update_btn)
        
        ctrl_panel.addWidget(pid_card)
        
        # Current Value Display
        val_card = QFrame()
        val_card.setObjectName("Card")
        val_card.setFixedWidth(300)
        val_layout = QVBoxLayout(val_card)
        self.pos_val_label = QLabel("0.0cm")
        self.pos_val_label.setStyleSheet("font-size: 32px; font-weight: 200; text-align: center;")
        self.pos_val_label.setAlignment(Qt.AlignCenter)
        val_layout.addWidget(self.pos_val_label)
        val_layout.addWidget(QLabel("POSIÇÃO ATUAL", alignment=Qt.AlignCenter, styleSheet=f"color: {TEXT_SECONDARY}; font-size: 10px;"))
        ctrl_panel.addWidget(val_card)
        
        ctrl_panel.addStretch()
        grid.addLayout(ctrl_panel)
        
        # --- Right Column ---
        right_panel = QVBoxLayout()
        right_panel.setSpacing(20)
        
        vis_card = QFrame()
        vis_card.setObjectName("Card")
        vis_layout = QVBoxLayout(vis_card)
        vis_layout.addWidget(QLabel("VISUALIZADOR LINEAR", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;"))
        
        self.linear_vis = pg.PlotWidget()
        self.linear_vis.setBackground(None)
        self.linear_vis.setXRange(0, 25)
        self.linear_vis.setYRange(-1, 1)
        self.linear_vis.hideAxis('left')
        self.linear_vis.showAxis('bottom')
        self.linear_vis.getAxis('bottom').setLabel("Posição (cm)")
        self.linear_vis.setFixedHeight(70)
        self.linear_vis.setMouseEnabled(x=False, y=False)
        self.linear_vis.setMenuEnabled(False)
        
        self.pos_marker = pg.ScatterPlotItem(size=15, pen=pg.mkPen(None), brush=pg.mkBrush(ACCENT_CYAN))
        self.sp_line = pg.InfiniteLine(pos=INITIAL_SETPOINT, angle=90, pen=pg.mkPen(ACCENT_ROSE, width=2, style=Qt.DashLine))
        self.linear_vis.addItem(self.pos_marker)
        self.linear_vis.addItem(self.sp_line)
        vis_layout.addWidget(self.linear_vis)
        right_panel.addWidget(vis_card)
        
        graph_card = QFrame()
        graph_card.setObjectName("Card")
        graph_layout = QVBoxLayout(graph_card)
        
        graph_header = QHBoxLayout()
        graph_header.addWidget(QLabel("HISTÓRICO DE POSIÇÃO", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;"))
        
        self.window_toggle_super = QPushButton("JANELA DESLIZANTE: ON")
        self.window_toggle_super.setStyleSheet(f"color: {ACCENT_CYAN}; font-size: 10px; font-weight: bold; border: 1px solid {BORDER}; padding: 4px;")
        self.window_toggle_super.setFixedWidth(150)
        self.window_toggle_super.clicked.connect(self.toggle_sliding_window)
        graph_header.addWidget(self.window_toggle_super)
        graph_layout.addLayout(graph_header)
        
        self.plot_super = pg.PlotWidget()
        self.plot_super.setBackground(None)
        self.plot_super.showGrid(x=True, y=True, alpha=0.1)
        self.plot_super.setYRange(0, 25)
        self.plot_super.getAxis('left').setLabel("Posição", units="cm")
        self.plot_super.getAxis('bottom').setLabel("Tempo", units="s")
        
        self.curve_pos = self.plot_super.plot(pen=pg.mkPen(ACCENT_CYAN, width=2), name="Posição")
        self.curve_sp = self.plot_super.plot(pen=pg.mkPen(ACCENT_ROSE, width=1, style=Qt.DashLine), name="Setpoint")
        graph_layout.addWidget(self.plot_super)
        right_panel.addWidget(graph_card, 1)
        
        grid.addLayout(right_panel, 1)
        layout.addLayout(grid)
        self.stack.addWidget(view)
        
    def init_config_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("Configurações")
        header.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setAlignment(Qt.AlignTop)

        # --- Serial Connection Card ---
        serial_card = QFrame()
        serial_card.setObjectName("Card")
        serial_card.setFixedWidth(420)
        serial_layout = QVBoxLayout(serial_card)
        serial_layout.setSpacing(14)

        serial_layout.addWidget(QLabel(
            "CONEXÃO SERIAL",
            styleSheet=f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        ))

        # Status badge
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 12px;"))
        self.connection_status_label = QLabel("● Desconectado")
        self.connection_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 12px; font-weight: bold;")
        status_row.addWidget(self.connection_status_label)
        status_row.addStretch()
        serial_layout.addLayout(status_row)

        # Port info (shows connected port name)
        self.connected_port_label = QLabel("")
        self.connected_port_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        serial_layout.addWidget(self.connected_port_label)

        serial_layout.addWidget(QLabel(
            "Portas COM disponíveis:",
            styleSheet=f"color: {TEXT_SECONDARY}; font-size: 11px;"
        ))

        # COM port list
        self.port_list = QListWidget()
        self.port_list.setFixedHeight(180)
        self.port_list.setSelectionMode(QAbstractItemView.SingleSelection)
        serial_layout.addWidget(self.port_list)

        # Refresh + action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        refresh_btn = QPushButton("↻  Atualizar Lista")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self.refresh_ports)
        btn_row.addWidget(refresh_btn)

        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.setObjectName("ActionBtn")
        self.connect_btn.clicked.connect(self.on_connect)
        btn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Desconectar")
        self.disconnect_btn.setObjectName("DangerBtn")
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.disconnect_btn.setEnabled(False)
        btn_row.addWidget(self.disconnect_btn)

        serial_layout.addLayout(btn_row)

        # Baud rate info (read-only)
        baud_row = QHBoxLayout()
        baud_row.addWidget(QLabel("Baud Rate:", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 11px;"))
        baud_label = QLabel("9600")
        baud_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        baud_row.addWidget(baud_label)
        baud_row.addStretch()
        serial_layout.addLayout(baud_row)

        content_layout.addWidget(serial_card)
        content_layout.addStretch()
        layout.addLayout(content_layout)
        layout.addStretch()

        self.stack.addWidget(view)

        # Populate port list on startup
        self.refresh_ports()

    # --- Config Slots ---

    def refresh_ports(self):
        self.port_list.clear()
        ports = serial.tools.list_ports.comports()
        if ports:
            for port in sorted(ports):
                item_text = f"{port.device}   —   {port.description}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, port.device)  # Store raw port name
                self.port_list.addItem(item)
            self.port_list.setCurrentRow(0)
        else:
            placeholder = QListWidgetItem("Nenhuma porta encontrada")
            placeholder.setData(Qt.UserRole, None)
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(QColor(TEXT_SECONDARY))
            self.port_list.addItem(placeholder)

    def on_connect(self):
        selected = self.port_list.currentItem()
        if not selected:
            return
        port_name = selected.data(Qt.UserRole)
        if not port_name:
            return

        success = self.serialArduino.connect(port_name)
        self._update_connection_ui(success, port_name)

    def on_disconnect(self):
        if self.is_running:
            self.toggle_reading()  # Stop reading before disconnecting
        self.serialArduino.disconnect()
        self._update_connection_ui(connected=False)

    def _update_connection_ui(self, connected: bool, port_name: str = ""):
        if connected:
            self.connection_status_label.setText("● Conectado")
            self.connection_status_label.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 12px; font-weight: bold;")
            self.connected_port_label.setText(f"Porta: {port_name}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.start_stop_btn.setEnabled(True)
            self.sidebar_status_label.setText(f"● {port_name}")
            self.sidebar_status_label.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 10px; font-weight: bold; padding: 0 20px 12px;")
        else:
            self.connection_status_label.setText("● Desconectado")
            self.connection_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 12px; font-weight: bold;")
            self.connected_port_label.setText("")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.start_stop_btn.setEnabled(False)
            self.sidebar_status_label.setText("● DESCONECTADO")
            self.sidebar_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 10px; font-weight: bold; padding: 0 20px 12px;")

    # --- General Slots ---

    def toggle_reading(self):
        if not self.is_running:
            self.reset_data()
            self.is_running = True
            self.start_stop_btn.setText("PARAR LEITURA")
            self.start_stop_btn.setStyleSheet(f"margin: 0 15px; padding: 15px; text-align: center; background-color: {ACCENT_ROSE}; color: white;")
        else:
            self.is_running = False
            self.start_stop_btn.setText("INICIAR LEITURA")
            self.start_stop_btn.setStyleSheet(f"margin: 0 15px; padding: 15px; text-align: center; background-color: {ACCENT_CYAN}; color: {BG_DEEP};")

    def toggle_sliding_window(self):
        self.sliding_window_enabled = not self.sliding_window_enabled
        txt = "JANELA DESLIZANTE: ON" if self.sliding_window_enabled else "JANELA DESLIZANTE: OFF"
        self.window_toggle_super.setText(txt)
        if not self.sliding_window_enabled:
            self.plot_super.enableAutoRange(axis='x', enable=True)

    def switch_view(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
    def on_slider_change(self, value):
        self.sp_input.setText(str(float(value)))
        
    def on_send_setpoint(self):
        try:
            val = float(self.sp_input.text())
            self.serialArduino.setpoint = val
            self.sp_slider.setValue(int(self.serialArduino.setpoint))
            self.serialArduino.send_command()
            print(f"[ACTION] Setpoint updated to {self.serialArduino.setpoint}")
        except ValueError:
            pass
            
    def on_update_pid(self):
        try:
            self.serialArduino.p = float(self.kp_input.text().replace(',', '.'))
            self.serialArduino.i = float(self.ki_input.text().replace(',', '.'))
            self.serialArduino.d = float(self.kd_input.text().replace(',', '.'))
            self.serialArduino.send_command()
            print(f"[ACTION] PID Gains: P={self.serialArduino.p}, I={self.serialArduino.i}, D={self.serialArduino.d}")
        except ValueError:
            print("[WARNING] Invalid PID input values.")
            
    def reset_data(self):
        self.history = {"time": [], "pos": [], "setpoint": [], "error": []}
        self.start_time = time.time()
        self.curve_pos.setData([], [])
        self.curve_sp.setData([], [])
        
    def export_csv(self):
        if not self.history["time"]:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Dados", "", "CSV Files (*.csv)")
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["time_s", "position_cm", "setpoint_cm", "error_cm"])
                for i in range(len(self.history["time"])):
                    writer.writerow([
                        self.history["time"][i],
                        self.history["pos"][i],
                        self.history["setpoint"][i],
                        self.history["error"][i]
                    ])
            print(f"[ACTION] Data exported to {path}")

    def update_simulation(self):
        pos, sp, err = self.serialArduino.receive_command()
        
        self.pos_val_label.setText(f"{pos:.1f}cm")
        self.pos_marker.setData(x=[pos], y=[0])
        self.sp_line.setValue(sp)
        
        if not self.is_running:
            return

        t = time.time() - self.start_time
        
        self.history["time"].append(t)
        self.history["pos"].append(pos)
        self.history["setpoint"].append(sp)
        self.history["error"].append(err)
        
        self.curve_pos.setData(self.history["time"], self.history["pos"])
        self.curve_sp.setData(self.history["time"], self.history["setpoint"])
        
        if self.sliding_window_enabled:
            window_size = 10
            if t > window_size:
                self.plot_super.setXRange(t - window_size, t)
            else:
                self.plot_super.setXRange(0, window_size)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())