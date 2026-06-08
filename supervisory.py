import sys
import csv
import time
import struct
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QSlider, QStackedWidget, 
    QFrame, QSizePolicy, QFileDialog, QListWidget, QListWidgetItem,
    QAbstractItemView, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QColor, QIcon
import pyqtgraph as pg
import serial
import serial.tools.list_ports

INITIAL_SETPOINT = 12.5

_KP = 6.0
_KI = 1.5
_KD = 0

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
    font-size: 15px; /* Fonte Maior */
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
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    padding: 10px;
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
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    padding: 10px;
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
    font-size: 14px;
    text-align: center;
    padding: 10px;
}}

QPushButton#SecondaryBtn:hover {{
    background-color: rgba(255, 255, 255, 0.02);
}}

QPushButton#OutlineBtn {{
    background-color: transparent;
    border: 1px solid {ACCENT_CYAN};
    color: {ACCENT_CYAN};
    border-radius: 6px;
    font-size: 14px;
    text-align: center;
    padding: 10px;
}}

QPushButton#BigActionBtn {{
    background-color: {BG_PANEL};
    border: 2px solid {BORDER};
    border-radius: 10px;
    color: {TEXT_PRIMARY};
    font-size: 18px; /* Botões de operação maiores */
    font-weight: bold;
    padding: 24px;
    text-align: center;
}}
QPushButton#BigActionBtn:hover {{
    background-color: rgba(255, 255, 255, 0.02);
    border: 2px solid {ACCENT_CYAN};
}}
QPushButton#BigActionBtn:disabled {{
    background-color: {BG_DEEP};
    color: {TEXT_SECONDARY};
    border: 2px dashed {BORDER};
}}

QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px;
    color: {TEXT_PRIMARY}; /* Corrigido para acompanhar o tema! */
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px; /* Fonte maior */
}}

QSlider::groove:horizontal {{
    border: 1px solid {BORDER};
    height: 6px;
    background: {BG_CARD};
    margin: 2px 0;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT_CYAN};
    border: 1px solid {ACCENT_CYAN};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QListWidget {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    outline: none;
}}

QListWidget::item {{
    padding: 12px 14px;
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

QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {BG_CARD};
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_AMBER};
    border-radius: 3px;
}}
"""

# --- Mapping para Alternância de Temas ---
THEME_COLORS = {
    "dark": {
        "BG_DEEP": "#0a0a0c",
        "BG_PANEL": "#141417",
        "BG_CARD": "#1c1c21",
        "ACCENT_CYAN": "#00f2ff",
        "ACCENT_ROSE": "#ff2d55",
        "ACCENT_GREEN": "#00e676",
        "ACCENT_AMBER": "#ffab00",
        "TEXT_PRIMARY": "#f0f0f5",
        "TEXT_SECONDARY": "#8e8e99",
        "BORDER": "#2d2d35",
        "RGBA_CYAN_05": "rgba(0, 242, 255, 0.05)",
        "RGBA_CYAN_10": "rgba(0, 242, 255, 0.1)",
        "RGBA_WHITE_02": "rgba(255, 255, 255, 0.02)",
        "RGBA_WHITE_03": "rgba(255, 255, 255, 0.03)"
    },
    "light": {
        "BG_DEEP": "#f0f0f5",
        "BG_PANEL": "#fdfdfd",
        "BG_CARD": "#ffffff",
        "ACCENT_CYAN": "#007aff",
        "ACCENT_ROSE": "#ff3b30",
        "ACCENT_GREEN": "#34c759",
        "ACCENT_AMBER": "#ff9500",
        "TEXT_PRIMARY": "#1c1c21",
        "TEXT_SECONDARY": "#6e6e73",
        "BORDER": "#d2d2d7",
        "RGBA_CYAN_05": "rgba(0, 122, 255, 0.08)",
        "RGBA_CYAN_10": "rgba(0, 122, 255, 0.15)",
        "RGBA_WHITE_02": "rgba(0, 0, 0, 0.04)",
        "RGBA_WHITE_03": "rgba(0, 0, 0, 0.06)"
    }
}

class ArduinoController:
    def __init__(self, baudrate=500000):
        self.ser = None
        self.baudrate = baudrate
        self.setpoint = INITIAL_SETPOINT
        self.p, self.i, self.d = _KP, _KI, _KD 
        self.last_pos = 0.0
        self.last_control = 0.0
        self.sync_marker = b'\xaa\xaa'

    def connect(self, porta):
        try:
            self.ser = serial.Serial(porta, self.baudrate, timeout=0.1)
            line = ""
            timeout_start = time.time()
            
            while "system ready" not in line.lower():
                if time.time() - timeout_start > 5:
                    break
                raw = self.ser.readline()
                if raw:
                    line = raw.decode('utf-8', errors='ignore').strip()
            
            print(f"Arduino connected on {porta}!")
            self.send_command()
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
        times, positions, controls = [], [], []
        
        if self.ser and self.ser.is_open:
            while self.ser.in_waiting >= 2:
                marker = self.ser.read(2)
                
                if marker == self.sync_marker:
                    head_data = self.ser.read(2)
                    if len(head_data) < 2:
                        break
                        
                    buffer_head = struct.unpack('<H', head_data)[0]
                    
                    if buffer_head == 0 or buffer_head > 100:
                        continue

                    expected_bytes = buffer_head * 12
                    
                    timeout = time.time()
                    while self.ser.in_waiting < expected_bytes:
                        if time.time() - timeout > 0.1:
                            break
                            
                    if self.ser.in_waiting >= expected_bytes:
                        payload = self.ser.read(expected_bytes)
                        
                        time_format = f'<{buffer_head}L'
                        times_batch = struct.unpack_from(time_format, payload, 0)
                        
                        pos_offset = buffer_head * 4
                        pos_format = f'<{buffer_head}f'
                        pos_batch = struct.unpack_from(pos_format, payload, pos_offset)
                        
                        ctrl_offset = pos_offset + (buffer_head * 4)
                        ctrl_format = f'<{buffer_head}f'
                        ctrl_batch = struct.unpack_from(ctrl_format, payload, ctrl_offset)
                        
                        times.extend(times_batch)
                        positions.extend(pos_batch)
                        controls.extend(ctrl_batch)
                        
                        if len(positions) > 0:
                            self.last_pos = positions[-1]
                            self.last_control = controls[-1]
                else:
                    self.ser.read(1)
                    
        return times, positions, controls
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supervisório Atuador Pneumático")
        self.resize(1280, 780)
        self.setStyleSheet(STYLESHEET)
        
        self.history = {"time": [], "pos": [], "setpoint": [], "error": [], "control": []}
        self.start_time_offset = None
        self.is_running = False
        self.sliding_window_enabled = True
        
        self.serialArduino = ArduinoController()
        
        self.cycle_timer = QTimer()
        self.cycle_timer.timeout.connect(self.cycle_tick)
        self.cycle_elapsed = 0
        
        # Configuração de estilo de fontes para os gráficos (Usado nas abas)
        self.axis_label_style = {'font-size': '15px', 'font-weight': 'bold'}
        self.tick_font = QFont()
        self.tick_font.setPixelSize(13)

        self.init_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(15) 
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 24, 0, 24)
        
        brand = QLabel("PNEUMATIC CONTROL")
        brand.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: bold; letter-spacing: 2px; padding: 0 20px 32px; font-size: 14px;")
        sidebar_layout.addWidget(brand)
        
        self.nav_btns = []
        for i, name in enumerate(["OPERAÇÃO", "Supervisório", "Configurações"]):
            btn = QPushButton(name)
            btn.setProperty("active", i == 0)
            btn.clicked.connect(lambda checked, idx=i: self.switch_view(idx))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
            
        sidebar_layout.addStretch()

        self.theme_btn = QPushButton("☀ Tema Claro")
        self.theme_btn.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: bold; padding: 0 20px 12px; text-align: left;")
        self.theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)

        self.sidebar_status_label = QLabel("● DESCONECTADO")
        self.sidebar_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 12px; font-weight: bold; padding: 0 20px 12px;")
        sidebar_layout.addWidget(self.sidebar_status_label)
        
        self.start_stop_btn = QPushButton("INICIAR LEITURA")
        self.start_stop_btn.setObjectName("ActionBtn")
        self.start_stop_btn.setFixedWidth(190)
        self.start_stop_btn.setStyleSheet(f"margin: 0 15px; padding: 15px; text-align: center;")
        self.start_stop_btn.clicked.connect(self.toggle_reading)
        self.start_stop_btn.setEnabled(False)
        sidebar_layout.addWidget(self.start_stop_btn)
        
        layout.addWidget(sidebar)
        
        # --- Content Area ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        self.init_operacao_view()
        self.init_supervisorio_view()
        self.init_config_view()
        
    def init_supervisorio_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        header = QLabel("Supervisório e Controle")
        header.setStyleSheet("font-size: 26px; font-weight: 600;")
        header_layout.addWidget(header)
        
        export_btn = QPushButton("Exportar Run (.CSV)")
        export_btn.setObjectName("OutlineBtn")
        export_btn.setFixedWidth(180)
        export_btn.clicked.connect(self.export_csv)
        header_layout.addWidget(export_btn)
        layout.addLayout(header_layout)
        
        grid = QHBoxLayout()
        grid.setSpacing(20)
        
        # --- Left column ---
        ctrl_panel = QVBoxLayout()
        ctrl_panel.setSpacing(20)
        
        sp_card = QFrame()
        sp_card.setObjectName("Card")
        sp_card.setFixedWidth(310)
        sp_layout = QVBoxLayout(sp_card)
        sp_layout.addWidget(QLabel("CONTROLE DE SETPOINT", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: bold;"))
        sp_layout.addSpacing(10)
        sp_layout.addWidget(QLabel("Posição Alvo (cm)", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px;"))
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
        
        pid_card = QFrame()
        pid_card.setObjectName("Card")
        pid_card.setFixedWidth(310)
        pid_layout = QVBoxLayout(pid_card)
        pid_layout.addWidget(QLabel("PARÂMETROS PID", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: bold;"))
        pid_layout.addSpacing(10)
        self.kp_input = QLineEdit(str(self.serialArduino.p))
        self.ki_input = QLineEdit(str(self.serialArduino.i))
        self.kd_input = QLineEdit(str(self.serialArduino.d))
        for label_text, input_widget in [("Kp", self.kp_input), ("Ki", self.ki_input), ("Kd", self.kd_input)]:
            pid_layout.addWidget(QLabel(label_text, styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px;"))
            pid_layout.addWidget(input_widget)
        update_btn = QPushButton("Atualizar Ganhos")
        update_btn.setObjectName("ActionBtn")
        update_btn.clicked.connect(self.on_update_pid)
        pid_layout.addWidget(update_btn)
        ctrl_panel.addWidget(pid_card)
        
        val_card = QFrame()
        val_card.setObjectName("Card")
        val_card.setFixedWidth(310)
        val_layout = QVBoxLayout(val_card)
        self.pos_val_label = QLabel("0.0 cm")
        self.pos_val_label.setStyleSheet("font-size: 34px; font-weight: 200;")
        self.pos_val_label.setAlignment(Qt.AlignCenter)
        val_layout.addWidget(self.pos_val_label)
        val_layout.addWidget(QLabel("POSIÇÃO ATUAL", alignment=Qt.AlignCenter, styleSheet=f"color: {TEXT_SECONDARY}; font-size: 12px;"))
        val_layout.addSpacing(8)
        self.ctrl_val_label = QLabel("0.00 V")
        self.ctrl_val_label.setStyleSheet(f"font-size: 34px; font-weight: 200; color: {ACCENT_AMBER};")
        self.ctrl_val_label.setAlignment(Qt.AlignCenter)
        val_layout.addWidget(self.ctrl_val_label)
        val_layout.addWidget(QLabel("SINAL DE CONTROLE", alignment=Qt.AlignCenter, styleSheet=f"color: {TEXT_SECONDARY}; font-size: 12px;"))
        ctrl_panel.addWidget(val_card)
        ctrl_panel.addStretch()
        grid.addLayout(ctrl_panel)
        
        # --- Right column ---
        right_panel = QVBoxLayout()
        right_panel.setSpacing(20)
        
        vis_card = QFrame()
        vis_card.setObjectName("Card")
        vis_layout = QVBoxLayout(vis_card)
        vis_layout.addWidget(QLabel("VISUALIZADOR LINEAR", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: bold;"))
        self.linear_vis = pg.PlotWidget()
        self.linear_vis.setBackground(BG_CARD)
        self.linear_vis.setXRange(0, 25)
        self.linear_vis.setYRange(-1, 1)
        self.linear_vis.hideAxis('left')
        self.linear_vis.showAxis('bottom')
        self.linear_vis.getAxis('bottom').setLabel("Posição (cm)", **self.axis_label_style)
        self.linear_vis.getAxis('bottom').setTickFont(self.tick_font)
        self.linear_vis.setFixedHeight(80)
        self.linear_vis.setMouseEnabled(x=False, y=False)
        self.linear_vis.setMenuEnabled(False)
        self.pos_marker = pg.ScatterPlotItem(size=18, pen=pg.mkPen(None), brush=pg.mkBrush(ACCENT_CYAN))
        self.sp_line = pg.InfiniteLine(pos=INITIAL_SETPOINT, angle=90, pen=pg.mkPen(ACCENT_ROSE, width=2, style=Qt.DashLine))
        self.linear_vis.addItem(self.pos_marker)
        self.linear_vis.addItem(self.sp_line)
        vis_layout.addWidget(self.linear_vis)
        right_panel.addWidget(vis_card)
        
        graph_card = QFrame()
        graph_card.setObjectName("Card")
        graph_layout = QVBoxLayout(graph_card)
        graph_header = QHBoxLayout()
        graph_header.addWidget(QLabel("HISTÓRICO DE POSIÇÃO", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: bold;"))
        self.window_toggle_super = QPushButton("JANELA DESLIZANTE: ON")
        self.window_toggle_super.setStyleSheet(f"color: {ACCENT_CYAN}; font-size: 12px; font-weight: bold; border: 1px solid {BORDER}; padding: 6px;")
        self.window_toggle_super.setFixedWidth(170)
        self.window_toggle_super.clicked.connect(self.toggle_sliding_window)
        graph_header.addWidget(self.window_toggle_super)
        graph_layout.addLayout(graph_header)
        
        self.plot_super = pg.PlotWidget()
        self.plot_super.setBackground(BG_CARD)
        self.plot_super.showGrid(x=True, y=True, alpha=0.1)
        self.plot_super.setYRange(0, 25)
        self.plot_super.getAxis('left').setLabel("Posição", units="cm", **self.axis_label_style)
        self.plot_super.getAxis('bottom').setLabel("Tempo", units="s", **self.axis_label_style)
        self.plot_super.getAxis('left').setTickFont(self.tick_font)
        self.plot_super.getAxis('bottom').setTickFont(self.tick_font)
        self.curve_pos = self.plot_super.plot(pen=pg.mkPen(ACCENT_CYAN, width=2), name="Posição")
        self.curve_sp  = self.plot_super.plot(pen=pg.mkPen(ACCENT_ROSE, width=1, style=Qt.DashLine), name="Setpoint")
        graph_layout.addWidget(self.plot_super)
        right_panel.addWidget(graph_card, 1)

        ctrl_graph_card = QFrame()
        ctrl_graph_card.setObjectName("Card")
        ctrl_graph_layout = QVBoxLayout(ctrl_graph_card)
        ctrl_graph_layout.addWidget(QLabel("SINAL DE CONTROLE (U)", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: bold;"))
        self.plot_ctrl = pg.PlotWidget()
        self.plot_ctrl.setBackground(BG_CARD)
        self.plot_ctrl.showGrid(x=True, y=True, alpha=0.1)
        self.plot_ctrl.setYRange(0, 10)
        self.plot_ctrl.getAxis('left').setLabel("Tensão", units="V", **self.axis_label_style)
        self.plot_ctrl.getAxis('bottom').setLabel("Tempo", units="s", **self.axis_label_style)
        self.plot_ctrl.getAxis('left').setTickFont(self.tick_font)
        self.plot_ctrl.getAxis('bottom').setTickFont(self.tick_font)
        
        self.line_ctrl_0 = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(BORDER, width=1))
        self.line_ctrl_5 = pg.InfiniteLine(pos=5, angle=0, pen=pg.mkPen(BORDER, width=1))
        self.plot_ctrl.addItem(self.line_ctrl_0)
        self.plot_ctrl.addItem(self.line_ctrl_5)
        
        self.curve_ctrl = self.plot_ctrl.plot(pen=pg.mkPen(ACCENT_AMBER, width=2), name="U (V)")
        ctrl_graph_layout.addWidget(self.plot_ctrl)
        right_panel.addWidget(ctrl_graph_card, 1)

        grid.addLayout(right_panel, 1)
        layout.addLayout(grid)
        self.stack.addWidget(view)

    def init_operacao_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        header = QLabel("Operação da Planta")
        header.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(header)

        # --- Ações Superiores ---
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)

        self.btn_pegar = QPushButton("⬇ PEGAR PEÇA")
        self.btn_pegar.setObjectName("BigActionBtn")
        self.btn_pegar.clicked.connect(self.action_pegar)
        actions_layout.addWidget(self.btn_pegar, 1)

        self.btn_largar = QPushButton("⬆ LARGAR PEÇA")
        self.btn_largar.setObjectName("BigActionBtn")
        self.btn_largar.setEnabled(False) # Inativo no início
        self.btn_largar.clicked.connect(self.action_largar)
        actions_layout.addWidget(self.btn_largar, 1)

        cycle_layout = QVBoxLayout()
        cycle_layout.setSpacing(5)
        
        self.btn_ciclo = QPushButton("⟳ CICLO COMPLETO")
        self.btn_ciclo.setObjectName("BigActionBtn")
        self.btn_ciclo.clicked.connect(self.action_ciclo)
        cycle_layout.addWidget(self.btn_ciclo)

        self.progress_ciclo = QProgressBar()
        self.progress_ciclo.setFixedHeight(10)
        self.progress_ciclo.setRange(0, 6000)
        self.progress_ciclo.setValue(0)
        self.progress_ciclo.setTextVisible(False)
        cycle_layout.addWidget(self.progress_ciclo)

        actions_layout.addLayout(cycle_layout, 1)
        layout.addLayout(actions_layout)

        # --- Gráficos Inferiores ---
        graph_header = QHBoxLayout()
        # DESTAQUE AQUI para a solicitação:
        graph_header.addWidget(QLabel("MONITORAMENTO DE DADOS", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 15px; font-weight: bold; letter-spacing: 1px;"))
        self.window_toggle_op = QPushButton("JANELA DESLIZANTE: ON")
        self.window_toggle_op.setStyleSheet(f"color: {ACCENT_CYAN}; font-size: 12px; font-weight: bold; border: 1px solid {BORDER}; padding: 6px;")
        self.window_toggle_op.setFixedWidth(170)
        self.window_toggle_op.clicked.connect(self.toggle_sliding_window)
        graph_header.addWidget(self.window_toggle_op)
        layout.addLayout(graph_header)

        graphs_layout = QHBoxLayout()
        graphs_layout.setSpacing(20)

        # Gráfico de Posição x Setpoint
        self.plot_op_pos_widget = pg.PlotWidget()
        self.plot_op_pos_widget.setBackground(BG_CARD)
        self.plot_op_pos_widget.showGrid(x=True, y=True, alpha=0.1)
        self.plot_op_pos_widget.setYRange(0, 25)
        self.plot_op_pos_widget.getAxis('left').setLabel("Posição", units="cm", **self.axis_label_style)
        self.plot_op_pos_widget.getAxis('bottom').setLabel("Tempo", units="s", **self.axis_label_style)
        self.plot_op_pos_widget.getAxis('left').setTickFont(self.tick_font)
        self.plot_op_pos_widget.getAxis('bottom').setTickFont(self.tick_font)
        self.curve_op_pos = self.plot_op_pos_widget.plot(pen=pg.mkPen(ACCENT_CYAN, width=2), name="Posição")
        self.curve_op_sp = self.plot_op_pos_widget.plot(pen=pg.mkPen(ACCENT_ROSE, width=1, style=Qt.DashLine), name="Setpoint")
        graphs_layout.addWidget(self.plot_op_pos_widget, 1)

        # Gráfico de Erro
        self.plot_op_err_widget = pg.PlotWidget()
        self.plot_op_err_widget.setBackground(BG_CARD)
        self.plot_op_err_widget.showGrid(x=True, y=True, alpha=0.1)
        self.plot_op_err_widget.setYRange(-25, 25)
        self.plot_op_err_widget.getAxis('left').setLabel("Erro", units="cm", **self.axis_label_style)
        self.plot_op_err_widget.getAxis('bottom').setLabel("Tempo", units="s", **self.axis_label_style)
        self.plot_op_err_widget.getAxis('left').setTickFont(self.tick_font)
        self.plot_op_err_widget.getAxis('bottom').setTickFont(self.tick_font)
        self.line_err_0 = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(BORDER, width=1))
        self.plot_op_err_widget.addItem(self.line_err_0)
        self.curve_op_err = self.plot_op_err_widget.plot(pen=pg.mkPen(ACCENT_AMBER, width=2), name="Erro")
        graphs_layout.addWidget(self.plot_op_err_widget, 1)

        layout.addLayout(graphs_layout, 1)
        self.stack.addWidget(view)
        
    def init_config_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        header = QLabel("Configurações")
        header.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setAlignment(Qt.AlignTop)

        serial_card = QFrame()
        serial_card.setObjectName("Card")
        serial_card.setFixedWidth(440)
        serial_layout = QVBoxLayout(serial_card)
        serial_layout.setSpacing(16)

        serial_layout.addWidget(QLabel("CONEXÃO SERIAL", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: bold; letter-spacing: 1px;"))

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 14px;"))
        self.connection_status_label = QLabel("● Desconectado")
        self.connection_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 14px; font-weight: bold;")
        status_row.addWidget(self.connection_status_label)
        status_row.addStretch()
        serial_layout.addLayout(status_row)

        self.connected_port_label = QLabel("")
        self.connected_port_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-family: 'JetBrains Mono', monospace;")
        serial_layout.addWidget(self.connected_port_label)

        serial_layout.addWidget(QLabel("Portas COM disponíveis:", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px;"))

        self.port_list = QListWidget()
        self.port_list.setFixedHeight(200)
        self.port_list.setSelectionMode(QAbstractItemView.SingleSelection)
        serial_layout.addWidget(self.port_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        refresh_btn = QPushButton("↻ Atualizar")
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

        baud_row = QHBoxLayout()
        baud_row.addWidget(QLabel("Baud Rate:", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 13px;"))
        baud_label = QLabel("500000")
        baud_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-family: 'JetBrains Mono', monospace;")
        baud_row.addWidget(baud_label)
        baud_row.addStretch()
        serial_layout.addLayout(baud_row)

        content_layout.addWidget(serial_card)
        content_layout.addStretch()
        layout.addLayout(content_layout)
        layout.addStretch()

        self.stack.addWidget(view)
        self.refresh_ports()

    # --- Lógica do Menu Operação ---
    def update_setpoint_globally(self, val):
        self.serialArduino.setpoint = float(val)
        self.sp_input.setText(str(float(val)))
        self.sp_slider.setValue(int(val))
        self.serialArduino.send_command()

    def action_pegar(self):
        self.update_setpoint_globally(20.0)
        self.btn_pegar.setEnabled(False)
        self.btn_ciclo.setEnabled(False)
        self.btn_largar.setEnabled(True)

    def action_largar(self):
        self.update_setpoint_globally(0.0)
        self.btn_pegar.setEnabled(True)
        self.btn_ciclo.setEnabled(True)
        self.btn_largar.setEnabled(False)

    def action_ciclo(self):
        self.update_setpoint_globally(20.0)
        self.btn_pegar.setEnabled(False)
        self.btn_largar.setEnabled(False)
        self.btn_ciclo.setEnabled(False)
        
        self.cycle_elapsed = 0
        self.progress_ciclo.setValue(0)
        self.cycle_timer.start(50) 

    def cycle_tick(self):
        self.cycle_elapsed += 50
        self.progress_ciclo.setValue(self.cycle_elapsed)
        if self.cycle_elapsed >= 6000:
            self.cycle_timer.stop()
            self.update_setpoint_globally(0.0)
            self.progress_ciclo.setValue(0)
            
            self.btn_pegar.setEnabled(True)
            self.btn_ciclo.setEnabled(True)
            self.btn_largar.setEnabled(False)
            
    # --- Continuação Funções do Sistema ---
    def toggle_theme(self):
        global BG_DEEP, BG_PANEL, BG_CARD, ACCENT_CYAN, ACCENT_ROSE, ACCENT_GREEN, ACCENT_AMBER, TEXT_PRIMARY, TEXT_SECONDARY, BORDER
        
        self.is_light_theme = getattr(self, "is_light_theme", False)
        self.is_light_theme = not self.is_light_theme
        
        old_key = "light" if not self.is_light_theme else "dark"
        new_key = "light" if self.is_light_theme else "dark"
        
        old_theme = THEME_COLORS[old_key]
        new_theme = THEME_COLORS[new_key]
        
        self.theme_btn.setText("🌙 Tema Escuro" if self.is_light_theme else "☀ Tema Claro")
            
        current_qss = self.styleSheet()
        for k in old_theme:
            current_qss = current_qss.replace(old_theme[k], f"__TOKEN_{k}__")
        for k in new_theme:
            current_qss = current_qss.replace(f"__TOKEN_{k}__", new_theme[k])
        self.setStyleSheet(current_qss)
        
        for widget in self.findChildren(QWidget):
            ss = widget.styleSheet()
            if ss:
                new_ss = ss
                for k in old_theme:
                    new_ss = new_ss.replace(old_theme[k], f"__TOKEN_{k}__")
                for k in new_theme:
                    new_ss = new_ss.replace(f"__TOKEN_{k}__", new_theme[k])
                if new_ss != ss:
                    widget.setStyleSheet(new_ss)

        for i in range(self.port_list.count()):
            item = self.port_list.item(i)
            if item.data(Qt.UserRole) is None:
                item.setForeground(QColor(new_theme["TEXT_SECONDARY"]))
                    
        all_plots = [self.linear_vis, self.plot_super, self.plot_ctrl, self.plot_op_pos_widget, self.plot_op_err_widget]
        for plot in all_plots:
            plot.setBackground(new_theme["BG_CARD"])
            plot.getAxis('bottom').setPen(new_theme["TEXT_SECONDARY"])
            plot.getAxis('bottom').setTextPen(new_theme["TEXT_PRIMARY"])
            if plot != self.linear_vis:
                plot.getAxis('left').setPen(new_theme["TEXT_SECONDARY"])
                plot.getAxis('left').setTextPen(new_theme["TEXT_PRIMARY"])
                
        self.pos_marker.setBrush(pg.mkBrush(new_theme["ACCENT_CYAN"]))
        
        self.sp_line.setPen(pg.mkPen(new_theme["ACCENT_ROSE"], width=2, style=Qt.DashLine))
        self.curve_pos.setPen(pg.mkPen(new_theme["ACCENT_CYAN"], width=2))
        self.curve_sp.setPen(pg.mkPen(new_theme["ACCENT_ROSE"], width=1, style=Qt.DashLine))
        self.curve_ctrl.setPen(pg.mkPen(new_theme["ACCENT_AMBER"], width=2))
        
        self.curve_op_pos.setPen(pg.mkPen(new_theme["ACCENT_CYAN"], width=2))
        self.curve_op_sp.setPen(pg.mkPen(new_theme["ACCENT_ROSE"], width=1, style=Qt.DashLine))
        self.curve_op_err.setPen(pg.mkPen(new_theme["ACCENT_AMBER"], width=2))
        
        self.line_ctrl_0.setPen(pg.mkPen(new_theme["BORDER"], width=1))
        self.line_ctrl_5.setPen(pg.mkPen(new_theme["BORDER"], width=1))
        self.line_err_0.setPen(pg.mkPen(new_theme["BORDER"], width=1))
        
        BG_DEEP = new_theme["BG_DEEP"]
        BG_PANEL = new_theme["BG_PANEL"]
        BG_CARD = new_theme["BG_CARD"]
        ACCENT_CYAN = new_theme["ACCENT_CYAN"]
        ACCENT_ROSE = new_theme["ACCENT_ROSE"]
        ACCENT_GREEN = new_theme["ACCENT_GREEN"]
        ACCENT_AMBER = new_theme["ACCENT_AMBER"]
        TEXT_PRIMARY = new_theme["TEXT_PRIMARY"]
        TEXT_SECONDARY = new_theme["TEXT_SECONDARY"]
        BORDER = new_theme["BORDER"]

    def refresh_ports(self):
        self.port_list.clear()
        ports = serial.tools.list_ports.comports()
        if ports:
            for port in sorted(ports):
                item_text = f"{port.device}   —   {port.description}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, port.device)
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
            self.toggle_reading()
        self.serialArduino.disconnect()
        self._update_connection_ui(connected=False)

    def _update_connection_ui(self, connected: bool, port_name: str = ""):
        if connected:
            self.connection_status_label.setText("● Conectado")
            self.connection_status_label.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 14px; font-weight: bold;")
            self.connected_port_label.setText(f"Porta: {port_name}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.start_stop_btn.setEnabled(True)
            self.sidebar_status_label.setText(f"● {port_name}")
            self.sidebar_status_label.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 12px; font-weight: bold; padding: 0 20px 12px;")
        else:
            self.connection_status_label.setText("● Desconectado")
            self.connection_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 14px; font-weight: bold;")
            self.connected_port_label.setText("")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.start_stop_btn.setEnabled(False)
            self.sidebar_status_label.setText("● DESCONECTADO")
            self.sidebar_status_label.setStyleSheet(f"color: {ACCENT_ROSE}; font-size: 12px; font-weight: bold; padding: 0 20px 12px;")

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
        self.window_toggle_op.setText(txt)
        if not self.sliding_window_enabled:
            self.plot_super.enableAutoRange(axis='x', enable=True)
            self.plot_ctrl.enableAutoRange(axis='x', enable=True)
            self.plot_op_pos_widget.enableAutoRange(axis='x', enable=True)
            self.plot_op_err_widget.enableAutoRange(axis='x', enable=True)

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
        self.history = {"time": [], "pos": [], "setpoint": [], "error": [], "control": []}
        self.start_time_offset = None
        self.curve_pos.setData([], [])
        self.curve_sp.setData([], [])
        self.curve_ctrl.setData([], [])
        self.curve_op_pos.setData([], [])
        self.curve_op_sp.setData([], [])
        self.curve_op_err.setData([], [])
        
    def export_csv(self):
        if not self.history["time"]:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Dados", "", "CSV Files (*.csv)")
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["time_s", "position_cm", "setpoint_cm", "error_cm", "control_signal_v"])
                for i in range(len(self.history["time"])):
                    writer.writerow([
                        self.history["time"][i],
                        self.history["pos"][i],
                        self.history["setpoint"][i],
                        self.history["error"][i],
                        self.history["control"][i],
                    ])
            print(f"[ACTION] Data exported to {path}")

    def update_simulation(self):
        times, positions, controls = self.serialArduino.receive_command()
        
        if not times:
            return

        latest_pos = positions[-1]
        latest_ctrl = controls[-1]
        latest_sp = self.serialArduino.setpoint
        
        self.pos_val_label.setText(f"{latest_pos:.1f} cm")
        self.ctrl_val_label.setText(f"{latest_ctrl:.2f} V")
        self.pos_marker.setData(x=[latest_pos], y=[0])
        self.sp_line.setValue(latest_sp)
        
        if not self.is_running:
            return

        for i in range(len(times)):
            t_ms = times[i]
            
            if self.start_time_offset is None:
                self.start_time_offset = t_ms
                
            t_sec = (t_ms - self.start_time_offset) / 1000.0
            error = latest_sp - positions[i]
            
            self.history["time"].append(t_sec)
            self.history["pos"].append(positions[i])
            self.history["setpoint"].append(latest_sp)
            self.history["error"].append(error)
            self.history["control"].append(controls[i])
        
        self.curve_pos.setData(self.history["time"], self.history["pos"])
        self.curve_sp.setData(self.history["time"], self.history["setpoint"])
        self.curve_ctrl.setData(self.history["time"], self.history["control"])
        
        self.curve_op_pos.setData(self.history["time"], self.history["pos"])
        self.curve_op_sp.setData(self.history["time"], self.history["setpoint"])
        self.curve_op_err.setData(self.history["time"], self.history["error"])
        
        if self.sliding_window_enabled and len(self.history["time"]) > 0:
            window_size = 10
            current_t = self.history["time"][-1]
            x_min = max(0, current_t - window_size)
            x_max = x_min + window_size
            
            self.plot_super.setXRange(x_min, x_max)
            self.plot_ctrl.setXRange(x_min, x_max)
            self.plot_op_pos_widget.setXRange(x_min, x_max)
            self.plot_op_err_widget.setXRange(x_min, x_max)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())