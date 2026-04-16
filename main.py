import sys
import csv
import time
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QSlider, QStackedWidget, 
    QFrame, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QColor, QIcon
import pyqtgraph as pg

# --- Sophisticated Dark Theme Constants ---
BG_DEEP = "#0a0a0c"
BG_PANEL = "#141417"
BG_CARD = "#1c1c21"
ACCENT_CYAN = "#00f2ff"
ACCENT_ROSE = "#ff2d55"
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
"""

class ActuatorSimulator:
    def __init__(self):
        self.pos = 0.0
        self.vel = 0.0
        self.integral = 0.0
        self.last_error = 0.0
        self.setpoint = 50.0
        self.p, self.i, self.d = 12.5, 0.85, 2.1
        self.dt = 0.05
        
    def update(self):
        # PID Logic
        error = self.setpoint - self.pos
        self.integral += error * self.dt
        derivative = (error - self.last_error) / self.dt
        output = self.p * error + self.i * self.integral + self.d * derivative
        self.last_error = error
        
        # Physics
        mass = 1.0
        friction = 5.0
        accel = (output - friction * self.vel) / mass
        self.vel += accel * self.dt
        self.pos += self.vel * self.dt
        
        # Bounds
        if self.pos < 0: self.pos, self.vel = 0.0, 0.0
        if self.pos > 100: self.pos, self.vel = 100.0, 0.0
        
        return self.pos, self.setpoint, error

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supervisório Atuador Pneumático")
        self.resize(1280, 700)
        self.setStyleSheet(STYLESHEET)
        
        self.sim = ActuatorSimulator()
        self.history = {"time": [], "pos": [], "setpoint": [], "error": []}
        self.start_time = time.time()
        self.is_running = False
        self.sliding_window_enabled = True
        
        self.init_ui()
        
        # Simulation Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(50) # 20Hz
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210) # Tightened sidebar
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 24, 0, 24)
        
        brand = QLabel("PNEUMATIC CONTROL")
        brand.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: bold; letter-spacing: 2px; padding: 0 20px 32px; font-size: 12px;")
        sidebar_layout.addWidget(brand)
        
        self.nav_btns = []
        # Removed "PID" from navigation
        for i, name in enumerate(["Supervisório", "Configurações"]):
            btn = QPushButton(name)
            btn.setProperty("active", i == 0)
            btn.clicked.connect(lambda checked, idx=i: self.switch_view(idx))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
            
        sidebar_layout.addStretch()
        
        # Start/Stop Button at the bottom of sidebar
        self.start_stop_btn = QPushButton("INICIAR LEITURA")
        self.start_stop_btn.setObjectName("ActionBtn")
        self.start_stop_btn.setFixedWidth(180) # Tightened button
        self.start_stop_btn.setStyleSheet(f"margin: 0 15px; padding: 15px; text-align: center;")
        self.start_stop_btn.clicked.connect(self.toggle_reading)
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
        
        # --- Left Column: Controls ---
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
        
        self.sp_input = QLineEdit("50.0")
        sp_layout.addWidget(self.sp_input)
        
        self.sp_slider = QSlider(Qt.Horizontal)
        self.sp_slider.setRange(0, 100)
        self.sp_slider.setValue(50)
        self.sp_slider.valueChanged.connect(self.on_slider_change)
        sp_layout.addWidget(self.sp_slider)
        
        send_btn = QPushButton("Enviar Setpoint")
        send_btn.setObjectName("ActionBtn")
        send_btn.clicked.connect(self.on_send_setpoint)
        sp_layout.addWidget(send_btn)
        
        ctrl_panel.addWidget(sp_card)
        
        # PID Card (Moved from PID view)
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
        
        # --- Right Column: Visualizer & Graphs ---
        right_panel = QVBoxLayout()
        right_panel.setSpacing(20)
        
        # Visualizer Card
        vis_card = QFrame()
        vis_card.setObjectName("Card")
        vis_layout = QVBoxLayout(vis_card)
        vis_layout.addWidget(QLabel("VISUALIZADOR LINEAR", styleSheet=f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;"))
        
        self.linear_vis = pg.PlotWidget()
        self.linear_vis.setBackground(None)
        self.linear_vis.setXRange(0, 100)
        self.linear_vis.setYRange(-1, 1)
        self.linear_vis.hideAxis('left')
        self.linear_vis.showAxis('bottom')
        self.linear_vis.getAxis('bottom').setLabel("Posição (cm)")
        self.linear_vis.setFixedHeight(70)
        self.linear_vis.setMouseEnabled(x=False, y=False)
        self.linear_vis.setMenuEnabled(False)
        
        self.pos_marker = pg.ScatterPlotItem(size=15, pen=pg.mkPen(None), brush=pg.mkBrush(ACCENT_CYAN))
        self.sp_line = pg.InfiniteLine(pos=50, angle=90, pen=pg.mkPen(ACCENT_ROSE, width=2, style=Qt.DashLine))
        self.linear_vis.addItem(self.pos_marker)
        self.linear_vis.addItem(self.sp_line)
        vis_layout.addWidget(self.linear_vis)
        right_panel.addWidget(vis_card)
        
        # History Graph Card
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
        self.plot_super.setYRange(0, 100)
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
        label = QLabel("Configurações")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 18px;")
        layout.addWidget(label)
        self.stack.addWidget(view)
        
    # --- Slots & Logic ---
    
    def toggle_reading(self):
        if not self.is_running:
            # Start
            self.reset_data()
            self.is_running = True
            self.start_stop_btn.setText("PARAR LEITURA")
            self.start_stop_btn.setStyleSheet(f"margin: 0 15px; padding: 15px; text-align: center; background-color: {ACCENT_ROSE}; color: white;")
        else:
            # Stop
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
            self.sim.setpoint = np.clip(val, 0, 100)
            self.sp_slider.setValue(int(self.sim.setpoint))
            print(f"[ACTION] Setpoint updated to {self.sim.setpoint}")
        except ValueError:
            pass
            
    def on_update_pid(self):
        try:
            self.sim.p = float(self.kp_input.text())
            self.sim.i = float(self.ki_input.text())
            self.sim.d = float(self.kd_input.text())
            print(f"[ACTION] PID Gains updated: P={self.sim.p}, I={self.sim.i}, D={self.sim.d}")
        except ValueError:
            pass
            
    def reset_data(self):
        self.history = {"time": [], "pos": [], "setpoint": [], "error": []}
        self.start_time = time.time()
        # Clear curves
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
        pos, sp, err = self.sim.update()
        
        # Update UI Labels (always update current value)
        self.pos_val_label.setText(f"{pos:.1f}cm")
        
        # Update Visualizer (always update current value)
        self.pos_marker.setData(x=[pos], y=[0])
        self.sp_line.setValue(sp)
        
        if not self.is_running:
            return

        t = time.time() - self.start_time
        
        # Update History
        self.history["time"].append(t)
        self.history["pos"].append(pos)
        self.history["setpoint"].append(sp)
        self.history["error"].append(err)
        
        # Update Graphs
        self.curve_pos.setData(self.history["time"], self.history["pos"])
        self.curve_sp.setData(self.history["time"], self.history["setpoint"])
        
        # Handle Sliding Window
        if self.sliding_window_enabled:
            window_size = 10 # seconds
            if t > window_size:
                self.plot_super.setXRange(t - window_size, t)
            else:
                self.plot_super.setXRange(0, window_size)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
