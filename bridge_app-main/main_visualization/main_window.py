import vtk
import time
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QComboBox, 
    QFrame,
    QLabel,
    QMessageBox
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from data_handler import DataHandler
from sensor_manager import SensorManager
from visualization import Visualization
from interaction_style import ClickInteractorStyle


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowTitle("Bridge Visualization")

        self.accel_data = None
        self.strain_data = None

        # Initialize sensor storage
        self.sensor_actors = []
        self.sensor_info = []
        
        # Create the main widget and layout
        self.frame = QFrame()
        self.vl = QHBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor()
        
        # Create control panel
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout()
        self.control_panel.setFixedWidth(200)
        
        # Create Label dropdown
        label_title = QLabel("Labels:")
        self.control_layout.addWidget(label_title)
        self.label_combo = QComboBox()
        self.label_combo.addItems(['Show All Labels', 'Hide All Labels', 'Show Random 50 Labels'])
        self.label_combo.currentTextChanged.connect(self.update_labels)
        self.control_layout.addWidget(self.label_combo)
        
        # Create Variable dropdown
        self.variable_label = QLabel("Variable:")
        self.control_layout.addWidget(self.variable_label)
        self.variable_combo = QComboBox()
        self.variable_combo.addItems(['U1', 'U2', 'U3', 'R1', 'R2', 'R3'])
        self.variable_combo.setCurrentText('U1')
        self.variable_combo.currentTextChanged.connect(self.on_variable_changed)
        self.control_layout.addWidget(self.variable_combo)
        
        # Create Sensor Information dropdown
        self.sensor_label = QLabel("Sensor Information:")
        self.control_layout.addWidget(self.sensor_label)
        self.sensor_combo = QComboBox()
        self.sensor_combo.addItems(['Accelerometers', 'Strain Gauge', 'Cameras', 'Displacement'])
        self.control_layout.addWidget(self.sensor_combo)

        # Load data and setup controls
        self.load_sensor_data()
        
        # Add stretch at the end
        self.control_layout.addStretch()
        
        # Set up layouts
        self.control_panel.setLayout(self.control_layout)
        self.vl.addWidget(self.vtkWidget)
        self.vl.addWidget(self.control_panel)
        
        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

        # Set up VTK pipeline
        self.render_window = self.vtkWidget.GetRenderWindow()
        self.renderer = vtk.vtkRenderer()
        self.render_window.AddRenderer(self.renderer)
        self.interactor = self.render_window.GetInteractor()
        
        # Set the interaction style
        style = ClickInteractorStyle(self)
        style.SetDefaultRenderer(self.renderer)
        self.interactor.SetInteractorStyle(style)
        
        # Setup timer variables
        self.timer_count = 0
        self.last_update = time.time()
        self.interactor.AddObserver('TimerEvent', self.update_time_step)
        self.interactor.CreateRepeatingTimer(1000)

        # Initialize visualization
        self.setup_visualization()

    def load_sensor_data(self):
        """Load sensor data using DataHandler"""
        self.accel_data, self.strain_data = DataHandler.load_sensor_data()


    def setup_visualization(self):
        # Create visualization manager
        self.visualization = Visualization(self.renderer)
        
        # Initialize visualization with default variable
        self.current_variable = 'U1'
        results = self.visualization.setup_visualization(self.current_variable)
        if results is not None:
            self.node_to_index, self.node_weights, self.edges, self.planes = results
        
        # Create sensor manager and add sensors
        self.sensor_manager = SensorManager(self.renderer)
        self.sensor_manager.add_sensors()
        self.sensor_actors = self.sensor_manager.sensor_actors
        self.sensor_info = self.sensor_manager.sensor_info
        
        # Initialize with first time step
        self.update_geometry(0)

    def update_labels(self, selection):
        self.visualization.update_labels(selection)
        self.render_window.Render()

    def on_variable_changed(self, variable):
        """Handle variable selection change"""
        # Store current variable
        self.current_variable = variable
        
        # Get columns for the selected variable
        cols = DataHandler.get_columns_for_variable(variable)
        
        # Read data with new columns
        df_weights = pd.read_excel('../data/Data_.xlsx', 
                                 sheet_name='Variables for 5 Timesteps', 
                                 header=None, 
                                 skiprows=1,
                                 usecols=[0] + [ord(col) - ord('A') for col in cols],
                                 nrows=1882)
        
        # Rename columns
        df_weights.columns = ['number'] + [f'weight_t{i+1}' for i in range(5)]
        
        # Update weights
        self.node_weights = {}
        for index, row in df_weights.iterrows():
            node_num = int(row['number'])
            self.node_weights[node_num] = [
                float(row[f'weight_t{i+1}']) for i in range(5)
            ]
        
        # Update geometry with current timestep
        self.update_geometry(self.timer_count % 5)
        self.render_window.Render()

    def update_time_step(self, obj, event):
        current_time = time.time()
        # Only update if 1 second has passed
        if current_time - self.last_update >= 1.0:
            time_step = self.timer_count % 5
            self.update_geometry(time_step)
            self.visualization.update_scalar_bar_title(time_step)
            self.timer_count += 1
            self.render_window.Render()
            self.last_update = current_time

    def update_geometry(self, time_step):
        self.visualization.update_geometry(
            time_step, 
            self.node_weights,
            self.node_to_index,
            self.edges,
            self.planes
        )