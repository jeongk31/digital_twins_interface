import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QComboBox, QLineEdit, QFrame, QScrollArea, QSizePolicy,
    QStackedWidget, QToolBar, QStatusBar
)

from PyQt5.QtGui import QPixmap, QFont, QColor, QPalette
from PyQt5.QtCore import Qt
from model_main import GLWidget, read_csv  # Import GLWidget and read_csv function
import csv
from functools import partial
# Add these imports at the top of your existing imports
import qtawesome as qta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QComboBox, QLineEdit, QFrame, QScrollArea
)
# Import Matplotlib for plotting
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from PyQt5.QtCore import pyqtSlot
class ModernWidget(QWidget):
    """Base template for modern-looking widgets"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #2C2C2C;
                border-radius: 8px;
                padding: 8px;
            }
        """)

class SensorDisplayWidget(ModernWidget):
    """Template for sensor display panels"""
    def __init__(self, title, icon_name, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Header with icon and title
        header = QHBoxLayout()
        icon = qta.icon(f"fa5s.{icon_name}", color='white')
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(24, 24))
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()
        
        # Content area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        
        layout.addLayout(header)
        layout.addWidget(self.content_area)

class DataGraphWidget(ModernWidget):
    """Template for data visualization graphs"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        
        # Graph canvas
        self.figure = Figure(facecolor='#2C2C2C')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2C2C2C')
        
        layout.addWidget(title_label)
        layout.addWidget(self.canvas)

class ControlPanel(ModernWidget):
    """Template for control panels"""
    def __init__(self, title, buttons_data, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        
        # Buttons grid
        buttons_layout = QGridLayout()
        row = 0
        col = 0
        max_cols = 4
        
        for btn_text, icon_name, callback in buttons_data:
            button = ModernButton(btn_text, qta.icon(f"fa5s.{icon_name}", color='white'))
            if callback:
                button.clicked.connect(callback)
            buttons_layout.addWidget(button, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        layout.addWidget(title_label)
        layout.addLayout(buttons_layout)
plt.style.use('dark_background')  # Set Matplotlib style to dark
class ModernButton(QPushButton):
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)
        if icon:
            self.setIcon(icon)
        self.setFont(QFont("Segoe UI", 10))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C;
                color: #FFFFFF;
                border: 1px solid #3C3C3C;
                padding: 8px 16px;
                border-radius: 4px;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #3C3C3C;
                border: 1px solid #4C4C4C;
            }
            QPushButton:pressed {
                background-color: #1C1C1C;
            }
        """)

class MainAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = os.path.join(os.getcwd(), "images")
        self.setWindowTitle("Bridge Digital Twin Interface")
        self.setGeometry(100, 100, 1600, 900)
        self.sensors = self.read_sensor_data()
        self.setup_ui()
        self.setup_statusbar()
        self.setup_toolbar()
        
    def setup_statusbar(self):
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border-top: 1px solid #3C3C3C;
            }
        """)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def setup_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2C2C2C;
                border-bottom: 1px solid #3C3C3C;
                spacing: 10px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 6px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3C3C3C;
            }
        """)
        
        # Add toolbar actions with icons
        toolbar_actions = [
            # ("refresh", "Refresh View", self.refresh_view),
            # ("save", "Save", self.save_data),
            # ("cog", "Settings", self.show_settings),
            # ("question-circle", "Help", self.show_help)
        ]
        
        for action_id, tooltip, callback in toolbar_actions:
            icon = qta.icon(f"fa5s.{action_id}", color='white')
            action = toolbar.addAction(icon, "")
            action.setToolTip(tooltip)
            action.triggered.connect(callback)
            
        self.addToolBar(toolbar)

    def setup_ui(self):
        # Create central widget with main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        
        # Left sidebar (Menu)
        left_sidebar = self.create_left_sidebar()
        main_layout.addWidget(left_sidebar)
        
        # Center area (3D Model)
        center_area = self.create_center_area()
        main_layout.addWidget(center_area, stretch=2)
        
        # Right sidebar (Analysis)
        right_sidebar = self.create_right_sidebar()
        main_layout.addWidget(right_sidebar)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Bottom panel
        bottom_panel = self.create_bottom_panel()
        bottom_dock = QDockWidget("Controls")
        bottom_dock.setWidget(bottom_panel)
        bottom_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.BottomDockWidgetArea, bottom_dock)

    def create_left_sidebar(self):
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(8)
        
        # Add menu buttons with icons
        menu_items = [
            ("file-alt", "File"),
            ("cube", "FEM Model"),
            ("eye", "View"),
            ("tools", "Tools"),
            ("question-circle", "Help"),
            ("comment", "Feedback")
        ]
        
        for icon_name, text in menu_items:
            icon = qta.icon(f"fa5s.{icon_name}", color='white')
            btn = ModernButton(text, icon)
            btn.clicked.connect(lambda checked, t=text: self.open_menu(t))
            layout.addWidget(btn)
            
        layout.addStretch()
        sidebar.setMaximumWidth(200)
        return sidebar

    def create_center_area(self):
        # Load data for 3D model
        node_data, element_data, node_weights = read_csv("nodes_animated.csv")
        gl_widget = GLWidget(node_data, element_data, node_weights, self)
        
        # Create frame for 3D view
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setFixedHeight(500)  # Adjust this value as needed

        frame.setStyleSheet("""
            QFrame {
                background-color: #1E1E1E;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)  # Reduce margins
        layout.setSpacing(4)  # Reduce spacing
        layout.addWidget(gl_widget)
        return frame

    def create_right_sidebar(self):
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(16)

        
        analysis_items = [
            ("chart-line", "Deformation Analysis", "Deformation.jpg"),
            ("search", "Damage Detection", "Damage.jpg"),
            ("random", "Uncertainty", "Uncertanity.jpg"),
            ("lightbulb", "Suggested Action", "Suggestions.jpg")
        ]
        
        for icon_name, text, img_file in analysis_items:
            container = QFrame()
            container.setStyleSheet("""
                QFrame {
                    background-color: #2C2C2C;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            
            item_layout = QVBoxLayout(container)
            
            # Image
            img_label = QLabel()
            img_path = os.path.join(self.path, img_file)
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(
                    100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignCenter)
            
            # Button
            icon = qta.icon(f"fa5s.{icon_name}", color='white')
            btn = ModernButton(text, icon)

            if text == "Deformation Analysis":
                btn.clicked.connect(self.open_deformation_analysis)

            if text == "Damage Detection":
                btn.clicked.connect(self.open_damage_detection)
                
            item_layout.addWidget(img_label)
            item_layout.addWidget(btn)
            layout.addWidget(container)
            
        layout.addStretch()
        sidebar.setMaximumHeight(600)  # Adjust this value as needed

        sidebar.setMaximumWidth(220)
        return sidebar

    def read_sensor_data(self):
        sensor_data_str = '''Sensors\tDescriptions\tLocation\tx(m)\ty(m)\tz(m)\tColor (Small Sphere or Cube)
Accelerometer 1\t(PCB 393B04) Uniaxial Lateral\t9-10 (A)\t28,5\t16,155415\t12,4\tRED
Accelerometer 2\t(PCB 393B04) Uniaxial Lateral\t9-10 (C)\t28,5\t16,155415\t0\tRED
Accelerometer 3\t(PCB 393B04) Uniaxial Lateral\t15-16 (A)\t51,7\t20,811278\t12,4\tRED
Accelerometer 4\t(PCB 393B04) Uniaxial Lateral\t15-16 (C)\t51,7\t20,811278\t0\tRED
Accelerometer 5\t(PCB 393B04) Uniaxial Lateral\t21-22 (A)\t74,95\t19,276895\t12,4\tRED
Accelerometer 6\t(PCB 393B04) Uniaxial Lateral\t21-22 (C)\t74,95\t19,276895\t0\tRED
Accelerometer 7\t(PCB 393B04) Uniaxial Lateral\t17 (A)\t57,495\t0\t12,4\tRED
Accelerometer 8\t(PCB 393B04) Uniaxial Lateral\t23 (A)\t80,493\t0\t12,4\tRED
Accelerometer 9\t(PCB 393B04) Uniaxial Vertical\t11 (A)\t34,497\t0\t12,4\tRED
Accelerometer 10\t(PCB 393B04) Uniaxial Vertical\t17 (A)\t57,495\t0\t12,4\tRED
Accelerometer 11\t(PCB 393B04) Uniaxial Vertical\t17 (C)\t57,495\t0\t0\tRED
Accelerometer 12\t(PCB 393B04) Uniaxial Vertical\t23 (A)\t80,493\t0\t12,4\tRED
Strain Gauge 1\t(CEA-06-250UN-350) Uniaxial\t20-21 (A)\t71,972\t9,638447\t12,4\tGreen
Strain Gauge 2\t(CEA-06-250UN-350) Uniaxial\t20-21 (C)\t71,972\t9,638447\t0\tGreen
Strain Gauge 3\t(CEA-06-250UN-350) Uniaxial\t23-24 (A)\t83,4965\t8,077707\t12,4\tGreen
Strain Gauge 4\t(CEA-06-250UN-350) Uniaxial\t23-24 (C)\t83,4965\t8,077707\t0\tGreen
Strain Gauge 5\t(CEA-06-250UN-350) Uniaxial\t10-11 (A)\t32,5805\t0\t12,4\tGreen
Strain Gauge 6\t(CEA-06-250UN-350) Uniaxial\t14-15 (A)\t47,9125\t0\t12,4\tGreen
Strain Gauge 7\t(CEA-06-250UN-350) Uniaxial\t17-18 (A)\t59,4115\t0\t12,4\tGreen
Strain Gauge 8\t(CEA-06-250UN-350) Uniaxial\t17-18 (C)\t59,4115\t0\t0\tGreen
Strain Gauge 9\t(CEA-06-250UN-350) Uniaxial\t23-24 (A)\t82,4095\t0\t12,4\tGreen
Strain Gauge 10\t(CEA-06-250UN-350) Uniaxial\t23-24 (A)\t82,4095\t0\t12\tGreen
Strain Gauge 11\t(CEA-06-250UN-350) Uniaxial\t23-24 (C)\t82,4095\t0\t0\tGreen
Strain Gauge 12\t(CEA-06-250UN-350) Uniaxial\t27-28 (A)\t97,7415\t0\t12,4\tGreen
Camera 1\tPTZ\t1 (B)\t0\t0\t6,2\tOrange
Camera 2\tPTZ\t33 (B)\t115\t0\t6,2\tOrange'''

        sensors_list = []

        lines = sensor_data_str.strip().split('\n')
        headers = lines[0].split('\t')
        for line in lines[1:]:
            fields = line.split('\t')
            data = dict(zip(headers, fields))
            # Replace commas with dots in numerical values and convert to floats
            x = float(data['x(m)'].replace(',', '.'))
            y = float(data['y(m)'].replace(',', '.'))
            z = float(data['z(m)'].replace(',', '.'))

            # Determine image based on sensor name
            if 'Accelerometer' in data['Sensors']:
                image = 'accelerometer_img.jpg'
            elif 'Strain Gauge' in data['Sensors']:
                image = 'strain_gauge_img.jpeg'
            elif 'Camera' in data['Sensors']:
                image = 'Camera.jpg'
            else:
                image = 'default_sensor_img.jpg'

            sensor = {
                'name': data['Sensors'],
                'description': data['Descriptions'],
                'location': data['Location'],
                'x': x,
                'y': y,
                'z': z,
                'color': data['Color (Small Sphere or Cube)'],
                'image': image
            }
            sensor['data_key'] = sensor['name'].replace(' ', '_')
            sensors_list.append(sensor)

        return sensors_list
    def create_bottom_panel(self):
        # Create bottom panel container
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setSpacing(10)
        
        # Create two rows for buttons
        row1_layout = QHBoxLayout()
        row2_layout = QHBoxLayout()
        
        # Define bottom panel buttons with their respective icons and images
        bottom_buttons = [
            ("Real Life Response", "Real_Life_Response.jpg", "chart-line"),
            ("View Sensors Location", "sensor.jpg", "map-marker"),
            ("Accelerometer Feed", "accelerometer.jpg", "wave-square"),
            ("Strain Gauge Feed", "Strain.jpg", "tachometer-alt"),
            ("Camera Feed", "Camera.jpg", "video"),
            ("Traffic Flow", "Traffic.jpg", "car"),
            ("Load Identification", "Load.jpg", "weight"),
            ("Damage Location", "Damage_Loc.jpg", "search-location"),
            ("Damage Extent", "Damage_Ext.jpg", "chart-bar"),
            ("Crack Detection", "Crack_Det.jpg", "search"),
            ("Required Maintenance", "Maintenance.jpg", "tools"),
            ("Estimated Work", "Estimate.jpg", "clock"),
            ("Estimated Cost", "Cost.jpg", "dollar-sign"),
            ("Structural Health Index", "SHI.jpg", "heartbeat")
        ]
        
        for i, (text, img_file, icon_name) in enumerate(bottom_buttons):
            # Create container for each button
            button_container = QFrame()
            button_container.setFixedSize(180, 100)  # Fix container size
            button_container.setStyleSheet("""
                QFrame {
                    background-color: #2C2C2C;
                    border-radius: 8px;
                    padding: 2px;
                }
            """)
            
            # Create layout for button container
            container_layout = QVBoxLayout(button_container)
            container_layout.setSpacing(3)
            
            # Add image
            img_label = QLabel()
            img_path = os.path.join(self.path, img_file)
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(
                    80, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignCenter)
            
            # Create button with icon
            icon = qta.icon(f"fa5s.{icon_name}", color='white')
            button = ModernButton(text, icon)
            button.setFixedWidth(170)
            button.setFixedHeight(30)
            # Connect button signals
            if text == "View Sensors Location":
                button.clicked.connect(self.show_sensors_location)
            elif text == "Strain Gauge Feed":
                button.clicked.connect(self.show_strain_gauge_feed)
            elif text == "Accelerometer Feed":
                button.clicked.connect(self.show_accelerometer_feed)
            
            # Add widgets to container
            container_layout.addWidget(img_label)
            container_layout.addWidget(button)
            
            # Add container to appropriate row
            if i < 7:
                row1_layout.addWidget(button_container)
            else:
                row2_layout.addWidget(button_container)
        
        # Add rows to main layout
        bottom_layout.addLayout(row1_layout)
        bottom_layout.addLayout(row2_layout)
        
        return bottom_panel
    def initUI(self):
        # Left Frame
        left_frame = QDockWidget("Menu", self)
        left_frame.setFixedWidth(250)
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        menu_buttons = ["File", "FEM Model", "View", "Tools", "Help", "Feedback"]
        
        for btn_text in menu_buttons:
            button = QPushButton(btn_text)
            button.setFont(QFont("Segoe UI", 11))
            button.clicked.connect(lambda _, text=btn_text: self.open_menu(text))
            left_layout.addWidget(button)
        
        left_widget.setLayout(left_layout)
        left_frame.setWidget(left_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_frame)
        
        # Right Frame with images and text as buttons
        right_frame = QDockWidget("Analysis", self)
        right_frame.setFixedWidth(200)
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        buttons_texts = [
            ("Deformation Analysis", "Deformation.jpg"),
            ("Damage Detection", "Damage.jpg"),
            ("Uncertainty", "Uncertanity.jpg"),
            ("Suggested Action", "Suggestions.jpg")
        ]
        
        for text, img_file in buttons_texts:
            img_path = os.path.join(self.path, img_file)
            pixmap = QPixmap(img_path).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(pixmap)

            # Vertical layout to stack image and button
            item_layout = QVBoxLayout()
            item_layout.addWidget(img_label, alignment=Qt.AlignCenter)

            text_button = QPushButton(text)
            text_button.setFont(QFont("Segoe UI", 11))

            # Check if it's the "Deformation Analysis" button to set up redirection
            if text == "Deformation Analysis":
                text_button.clicked.connect(self.open_deformation_analysis)

            if text == "Damage Detection":
                text_button.clicked.connect(self.open_damage_detection)
            
            item_layout.addWidget(text_button, alignment=Qt.AlignCenter)
            item_widget = QWidget()
            item_widget.setLayout(item_layout)
            right_layout.addWidget(item_widget)
        
        right_widget.setLayout(right_layout)
        right_frame.setWidget(right_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, right_frame)
        
        # Load node, element, and weight data for the 3D model
        node_data, element_data, node_weights = read_csv("nodes_animated.csv")

        # Set the 3D model as the central widget
        gl_widget = GLWidget(node_data, element_data, node_weights, self)
        self.setCentralWidget(gl_widget)
        
        # Bottom Frame with control buttons
        bottom_frame = QDockWidget("Controls", self)
        bottom_frame.setFixedHeight(250)
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()
        
        bottom_row1 = QHBoxLayout()
        bottom_row2 = QHBoxLayout()
        
        # Add the buttons with images and labels for the bottom frame
        bottom_buttons_texts = [
            ("Real Life Response", "Real_Life_Response.jpg"),
            ("View Sensors Location", "sensor.jpg"),
            ("Accelerometer Feed", "accelerometer.jpg"),
            ("Strain Gauge Feed", "Strain.jpg"),
            ("Camera Feed", "Camera.jpg"),
            ("Traffic Flow", "Traffic.jpg"),
            ("Load Identification", "Load.jpg"),
            ("Damage Location", "Damage_Loc.jpg"),
            ("Damage Extent", "Damage_Ext.jpg"),
            ("Crack Detection", "Crack_Det.jpg"),
            ("Required Maintenance", "Maintenance.jpg"),
            ("Estimated Work", "Estimate.jpg"),
            ("Estimated Cost", "Cost.jpg"),
            ("Structural Health Index", "SHI.jpg")
        ]
        
        for i, (text, img_file) in enumerate(bottom_buttons_texts):
            img_path = os.path.join(self.path, img_file)
            pixmap = QPixmap(img_path).scaled(100, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(pixmap)

            # Vertical layout for each control button with image on top and text button below
            item_layout = QVBoxLayout()
            item_layout.addWidget(img_label, alignment=Qt.AlignCenter)

            # Create a QPushButton for the text and style it
            text_button = QPushButton(text)
            text_button.setFont(QFont("Segoe UI", 11))
            text_button.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    padding: 8px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #005a9e;
                }
            """)

            # Connect the "View Sensors Location" button to the event handler
            if text == "View Sensors Location":
                text_button.clicked.connect(self.show_sensors_location)
            if text == "Strain Gauge Feed":
                text_button.clicked.connect(self.show_strain_gauge_feed)
            # Connect the "Accelerometer Feed" button to the event handler
            if text == "Accelerometer Feed":
                text_button.clicked.connect(self.show_accelerometer_feed)

            item_layout.addWidget(text_button, alignment=Qt.AlignCenter)
            
            item_widget = QWidget()
            item_widget.setLayout(item_layout)
            
            if i < 7:
                bottom_row1.addWidget(item_widget)
            else:
                bottom_row2.addWidget(item_widget)
        
        bottom_layout.addLayout(bottom_row1)
        bottom_layout.addLayout(bottom_row2)
        bottom_widget.setLayout(bottom_layout)
        bottom_frame.setWidget(bottom_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, bottom_frame)

    def open_menu(self, text):
        print(f"{text} menu opened")

    # Method to open model.py when Deformation Analysis button is clicked
    def open_deformation_analysis(self):
        # Get the absolute path to model.py
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_visualization', 'main.py')
        
        # Use sys.executable to ensure the right Python interpreter is used
        subprocess.Popen([sys.executable, model_path])

    def open_damage_detection(self):
        # Path to the main.py file in confusion_matrix directory
        main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'confusion_matrix', 'main.py')
        
        # Use sys.executable to ensure the correct Python interpreter is used
        subprocess.Popen([sys.executable, main_path])

        # Method to show the sensors location in a table
    def show_sensors_location(self):
        # Create a new window or dialog
        self.sensor_window = QWidget()
        self.sensor_window.setWindowTitle("Sensors Location")
        self.sensor_window.setGeometry(100, 100, 1000, 800)
        sensor_layout = QVBoxLayout()

        # Add two images of the bridge map before the table
        images_layout = QHBoxLayout()

        # Load the images
        bridge_image1 = QLabel()
        bridge_img_path1 = os.path.join(self.path, 'bridge_image.png')

        # Ensure the images exist
        if os.path.exists(bridge_img_path1):
            pixmap1 = QPixmap(bridge_img_path1).scaled(1000, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            bridge_image1.setPixmap(pixmap1)
            bridge_image1.setAlignment(Qt.AlignCenter)
        else:
            bridge_image1.setText("Bridge Map Image 1 Not Found")

        images_layout.addWidget(bridge_image1, alignment=Qt.AlignCenter)
        sensor_layout.addLayout(images_layout)

        # Create a table
        table = QTableWidget()
        table.setRowCount(len(self.sensors))
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(['Sensor Name', 'Image', 'Description', 'Location', 'X', 'Y', 'Z', 'Color'])

        # Populate the table
        for row, sensor in enumerate(self.sensors):
            name_button = QPushButton(sensor['name'])
            sensor_key_name = sensor['data_key']
            name_button.clicked.connect(lambda _, sensor_key_name=sensor_key_name: self.plot_sensor_graph(sensor_key_name))
            table.setCellWidget(row, 0, name_button)

            # Image
            img_label = QLabel()
            img_path = os.path.join(self.path, sensor['image'])
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(pixmap)
            else:
                img_label.setText("No Image")
            table.setCellWidget(row, 1, img_label)

            # Description
            table.setItem(row, 2, QTableWidgetItem(sensor['description']))
            # Location
            table.setItem(row, 3, QTableWidgetItem(sensor['location']))
            # X, Y, Z coordinates
            table.setItem(row, 4, QTableWidgetItem(str(sensor['x'])))
            table.setItem(row, 5, QTableWidgetItem(str(sensor['y'])))
            table.setItem(row, 6, QTableWidgetItem(str(sensor['z'])))

            # Color as actual color
            color_label = QLabel()
            color_label.setFixedSize(50, 50)
            color_label.setStyleSheet(f"background-color: {sensor['color'].lower()};")
            color_label.setAlignment(Qt.AlignCenter)
            table.setCellWidget(row, 7, color_label)

        # Adjust column widths
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        sensor_layout.addWidget(table)
        self.sensor_window.setLayout(sensor_layout)
        self.sensor_window.show()

    @pyqtSlot(str)
    def plot_sensor_graph(self, sensor_key_name):
        if "Accelerometer_" in sensor_key_name:
            self.show_accelerometer_feed()
            index = self.acc_dropdown.findText(sensor_key_name)
            if index >= 0:
                self.acc_dropdown.setCurrentIndex(index)
                self.update_accelerometer_plot()
        elif "Strain_Gauge_" in sensor_key_name:
            self.show_strain_gauge_feed()
            index = self.strain_dropdown.findText(sensor_key_name)
            if index >= 0:
                self.strain_dropdown.setCurrentIndex(index)
                self.update_strain_gauge_plot()

    # New method to show accelerometer feed
    def show_accelerometer_feed(self):
        # Read the CSV file
        data_file = "acc_data.csv"
        time_values = []
        accelerometer_data = {}  # Dictionary to hold data for each accelerometer

        try:
            with open(data_file, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                # Initialize accelerometer_data with empty lists
                for field in reader.fieldnames:
                    if field.startswith('Accelerometer_'):
                        accelerometer_data[field] = []
                for row in reader:
                    print(row)
                    # Replace commas with dots and convert to float
                    time = float(row['\ufeffTime'].replace(',', '.'))
                    time_values.append(time)
                    for key in accelerometer_data.keys():
                        value_str = row[key].replace(',', '.')
                        if value_str == '':
                            value = None
                        else:
                            value = float(value_str)
                        accelerometer_data[key].append(value)
        except Exception as e:
            print(f"Error reading accelerometer data: {e}")
            return

        # Create a new window
        self.accelerometer_window = QWidget()
        self.accelerometer_window.setWindowTitle("Accelerometer Feed")
        self.accelerometer_window.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()

        # Create a dropdown
        self.acc_dropdown = QComboBox()
        # Get the list of accelerometer names from the keys
        accelerometer_names = list(accelerometer_data.keys())
        # Sort the accelerometer names to ensure correct order
        accelerometer_names.sort(key=lambda x: int(x.split('_')[1]))
        self.acc_dropdown.addItems(accelerometer_names)
        self.acc_dropdown.currentIndexChanged.connect(self.update_accelerometer_plot)

        # Save the data to instance variables
        self.acc_time_values = time_values
        self.acc_data = accelerometer_data

        # Create the matplotlib Figure and FigureCanvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Add widgets to layout
        layout.addWidget(self.acc_dropdown)
        layout.addWidget(self.canvas)

        self.accelerometer_window.setLayout(layout)
        self.accelerometer_window.show()

        # Initial plot
        self.update_accelerometer_plot()

    def update_accelerometer_plot(self):
        # Clear the figure
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Get selected accelerometer
        selected_accelerometer = self.acc_dropdown.currentText()
        y_values = self.acc_data[selected_accelerometer]
        label = selected_accelerometer

        # Plot the data
        ax.plot(self.acc_time_values, y_values, label=label, marker='', linewidth=0.8)  # Removes markers, keeps only the line
        ax.set_title(f"{label} Data Over Time")
        ax.set_xlabel("Time")
        ax.set_ylabel("Acceleration")
        ax.legend()

        self.canvas.draw()
    def show_strain_gauge_feed(self):
        # Read the CSV file
        data_file = "strain_data.csv"
        time_values = []
        strain_gauge_data = {}  # Dictionary to hold data for each strain gauge

        try:
            with open(data_file, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                # Normalize field names
                reader.fieldnames = [field.strip('\ufeff') for field in reader.fieldnames]
                # Initialize strain_gauge_data with empty lists
                for field in reader.fieldnames:
                    if field.startswith('Strain_Gauge_'):
                        strain_gauge_data[field] = []
                for row in reader:
                    # Replace commas with dots and convert to float
                    time = float(row['Time'].replace(',', '.'))
                    time_values.append(time)
                    for key in strain_gauge_data.keys():
                        value_str = row[key].replace(',', '.')
                        if value_str == '':
                            value = None
                        else:
                            value = float(value_str)
                        strain_gauge_data[key].append(value)
        except Exception as e:
            print(f"Error reading strain gauge data: {e}")
            return

        # Create a new window
        self.strain_gauge_window = QWidget()
        self.strain_gauge_window.setWindowTitle("Strain Gauge Feed")
        self.strain_gauge_window.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()

        # Create a dropdown
        self.strain_dropdown = QComboBox()
        # Get the list of strain gauge names from the keys
        strain_gauge_names = list(strain_gauge_data.keys())
        # Sort the strain gauge names to ensure correct order
        strain_gauge_names.sort(key=lambda x: int(x.split('_')[2]))
        self.strain_dropdown.addItems(strain_gauge_names)
        self.strain_dropdown.currentIndexChanged.connect(self.update_strain_gauge_plot)

        # Save the data to instance variables
        self.strain_time_values = time_values
        self.strain_data = strain_gauge_data

        # Create the matplotlib Figure and FigureCanvas
        self.strain_figure = Figure()
        self.strain_canvas = FigureCanvas(self.strain_figure)

        # Add widgets to layout
        layout.addWidget(self.strain_dropdown)
        layout.addWidget(self.strain_canvas)

        self.strain_gauge_window.setLayout(layout)
        self.strain_gauge_window.show()

        # Initial plot
        self.update_strain_gauge_plot()

    def update_strain_gauge_plot(self):
        # Clear the figure
        self.strain_figure.clear()
        ax = self.strain_figure.add_subplot(111)

        # Get selected strain gauge
        selected_strain_gauge = self.strain_dropdown.currentText()
        y_values = self.strain_data[selected_strain_gauge]
        label = selected_strain_gauge

        # Plot the data
        ax.plot(self.strain_time_values, y_values, label=label, marker='', linewidth=0.8)
        ax.set_title(f"{label} Data Over Time")
        ax.set_xlabel("Time")
        ax.set_ylabel("Strain")
        ax.legend()

        self.strain_canvas.draw()



# Create the application and set the style
app = QApplication(sys.argv)
app.setStyle('Fusion')

# Set the dark palette
palette = QPalette()
palette.setColor(QPalette.Window, QColor(53, 53, 53))
palette.setColor(QPalette.WindowText, Qt.white)
palette.setColor(QPalette.Base, QColor(25, 25, 25))
palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
palette.setColor(QPalette.ToolTipBase, Qt.white)
palette.setColor(QPalette.ToolTipText, Qt.white)
palette.setColor(QPalette.Text, Qt.white)
palette.setColor(QPalette.Button, QColor(53, 53, 53))
palette.setColor(QPalette.ButtonText, Qt.white)
palette.setColor(QPalette.BrightText, Qt.red)
palette.setColor(QPalette.Link, QColor(42, 130, 218))
palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
palette.setColor(QPalette.HighlightedText, Qt.black)
app.setPalette(palette)

window = MainAppWindow()
window.show()
sys.exit(app.exec_())