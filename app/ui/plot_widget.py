# app/ui/plot_widget.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette

class PlotWidget(QWidget):
    """Beautiful dark/light mode compatible sensor display."""
    
    def __init__(self) -> None:
        super().__init__()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        self.title = QLabel("M5StickC Plus - Live Sensor Data")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        
        # Grid for the 6 values
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Create 6 value labels
        self.acc_x = QLabel("AccX: 0")
        self.acc_y = QLabel("AccY: 0") 
        self.acc_z = QLabel("AccZ: 0")
        self.gyr_x = QLabel("GyrX: 0")
        self.gyr_y = QLabel("GyrY: 0")
        self.gyr_z = QLabel("GyrZ: 0")
        
        # Add section headers
        acc_header = QLabel("ACCELEROMETER")
        gyr_header = QLabel("GYROSCOPE")
        
        # Add to grid with headers
        grid.addWidget(acc_header, 0, 0, 1, 3)  # Span 3 columns
        grid.addWidget(self.acc_x, 1, 0)
        grid.addWidget(self.acc_y, 1, 1)
        grid.addWidget(self.acc_z, 1, 2)
        
        grid.addWidget(gyr_header, 2, 0, 1, 3)  # Span 3 columns
        grid.addWidget(self.gyr_x, 3, 0)
        grid.addWidget(self.gyr_y, 3, 1)
        grid.addWidget(self.gyr_z, 3, 2)
        
        layout.addLayout(grid)
        
        # Apply beautiful styling
        self._apply_styling()
    
    def _apply_styling(self) -> None:
        """Apply beautiful dark/light mode compatible styling."""
        
        # Detect if system is in dark mode
        palette = QApplication.instance().palette()
        is_dark_mode = palette.color(QPalette.Window).lightness() < 128
        
        if is_dark_mode:
            # Dark mode colors
            bg_color = "#2b2b2b"
            text_color = "#ffffff"
            accent_color = "#4a9eff"
            secondary_bg = "#3d3d3d"
            border_color = "#555555"
            header_bg = "#1e1e1e"
            acc_color = "#ff6b6b"
            gyr_color = "#4ecdc4"
        else:
            # Light mode colors
            bg_color = "#ffffff"
            text_color = "#2c3e50"
            accent_color = "#3498db"
            secondary_bg = "#f8f9fa"
            border_color = "#dee2e6"
            header_bg = "#ecf0f1"
            acc_color = "#e74c3c"
            gyr_color = "#1abc9c"
        
        # Style the main widget
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }}
        """)
        
        # Style the title
        self.title.setStyleSheet(f"""
            QLabel {{
                font-size: 22px;
                font-weight: bold;
                color: {accent_color};
                padding: 15px;
                background-color: {header_bg};
                border-radius: 10px;
                border: 2px solid {accent_color};
            }}
        """)
        
        # Style sensor value labels
        sensor_labels = [self.acc_x, self.acc_y, self.acc_z, self.gyr_x, self.gyr_y, self.gyr_z]
        for i, label in enumerate(sensor_labels):
            if i < 3:  # Accelerometer labels
                label.setStyleSheet(f"""
                    QLabel {{
                        font-size: 18px;
                        font-weight: bold;
                        font-family: 'Courier New', monospace;
                        padding: 15px;
                        background-color: {secondary_bg};
                        color: {text_color};
                        border: 2px solid {acc_color};
                        border-radius: 8px;
                        min-width: 120px;
                        min-height: 50px;
                    }}
                    QLabel:hover {{
                        background-color: {acc_color};
                        color: white;
                        transform: scale(1.05);
                    }}
                """)
            else:  # Gyroscope labels
                label.setStyleSheet(f"""
                    QLabel {{
                        font-size: 18px;
                        font-weight: bold;
                        font-family: 'Courier New', monospace;
                        padding: 15px;
                        background-color: {secondary_bg};
                        color: {text_color};
                        border: 2px solid {gyr_color};
                        border-radius: 8px;
                        min-width: 120px;
                        min-height: 50px;
                    }}
                    QLabel:hover {{
                        background-color: {gyr_color};
                        color: white;
                        transform: scale(1.05);
                    }}
                """)
            label.setAlignment(Qt.AlignCenter)
        
        # Style section headers
        acc_header = self.findChild(QLabel, "ACCELEROMETER") or QLabel("ACCELEROMETER")
        gyr_header = self.findChild(QLabel, "GYROSCOPE") or QLabel("GYROSCOPE")
        
        # Find headers in the grid layout
        grid_layout = self.layout().itemAt(1).layout()
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QLabel) and widget.text() in ["ACCELEROMETER", "GYROSCOPE"]:
                    if widget.text() == "ACCELEROMETER":
                        widget.setStyleSheet(f"""
                            QLabel {{
                                font-size: 16px;
                                font-weight: bold;
                                color: white;
                                background-color: {acc_color};
                                padding: 10px;
                                border-radius: 6px;
                                margin-bottom: 5px;
                            }}
                        """)
                    else:
                        widget.setStyleSheet(f"""
                            QLabel {{
                                font-size: 16px;
                                font-weight: bold;
                                color: white;
                                background-color: {gyr_color};
                                padding: 10px;
                                border-radius: 6px;
                                margin-bottom: 5px;
                            }}
                        """)
                    widget.setAlignment(Qt.AlignCenter)
    
    def add_sample(self, ax: int, ay: int, az: int, gx: int, gy: int, gz: int) -> None:
        """Update the 6 values with beautiful formatting."""
        self.acc_x.setText(f"X: {ax:6d}")
        self.acc_y.setText(f"Y: {ay:6d}")
        self.acc_z.setText(f"Z: {az:6d}")
        self.gyr_x.setText(f"X: {gx:6d}")
        self.gyr_y.setText(f"Y: {gy:6d}")
        self.gyr_z.setText(f"Z: {gz:6d}")
