import vtk
import pandas as pd
import numpy as np
import time
import random
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QComboBox, 
    QFrame,
    QLabel,
    QMessageBox,
    QDialog,
    QPushButton
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class AccelerometerGraph(QDialog):
    def __init__(self, x_data, y_data, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(300, 300, 800, 400)
        
        # Create the layout
        layout = QVBoxLayout()
        
        # Create the figure and canvas with a smaller size
        fig = Figure(figsize=(6, 3))  # Smaller figure
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        
        # Convert data
        x_data = x_data.astype(float).to_numpy()
        y_data = y_data.astype(float).to_numpy()
        
        # Create the plot
        ax = fig.add_subplot(111)
        ax.plot(x_data, y_data, 'b-', linewidth=0.5)  # Thin blue line
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.set_ylabel('Acceleration', fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.tick_params(labelsize=8)
        
        # Adjust layout
        fig.tight_layout()
        
        # Set the layout
        self.setLayout(layout)


class ClickInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)
        self.parent = parent
        
    def leftButtonPressEvent(self, obj, event):
        clickPos = self.GetInteractor().GetEventPosition()
        
        # Create picker
        picker = vtk.vtkPropPicker()
        picker.Pick(clickPos[0], clickPos[1], 0, self.GetDefaultRenderer())
        
        # Get the picked actor
        actor = picker.GetActor()
        
        if actor in self.parent.sensor_actors:
            # Get sensor info
            sensor_index = self.parent.sensor_actors.index(actor)
            sensor_info = self.parent.sensor_info[sensor_index]
            
            # Create detailed message with all available information
            msg = QMessageBox()
            msg.setWindowTitle("Sensor Information")
            msg.setText(f"Type: {sensor_info['type']}\n"
                       f"Description: {sensor_info['description']}\n"
                       f"Location: {sensor_info['location']}\n"
                       f"Coordinates: ({sensor_info['x']:.2f}, {sensor_info['y']:.2f}, {sensor_info['z']:.2f})")
            msg.exec_()
            
            # Reset the interaction state
            self.GetInteractor().GetRenderWindow().Render()
            self.OnLeftButtonUp()  # Add this line to reset the button state
        else:
            # Only trigger camera movement if we didn't click on a sensor
            self.OnLeftButtonDown()


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

        self.load_sensor_data()  # Load data first
        self.setup_sensor_graph_controls()  # Then setup controls
        
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

        # Set up the visualization
        self.setup_visualization()

    def get_columns_for_variable(self, variable):
        """Return the correct columns based on variable selection"""
        # Map variables to their column positions within each timestep block
        variable_positions = {
            'U1': 0,  # First variable in each timestep block
            'U2': 1,
            'U3': 2,
            'R1': 3,
            'R2': 4,
            'R3': 5
        }
        
        # Calculate the column letters for the selected variable across all timesteps
        base_cols = ['B', 'C', 'D', 'E', 'F', 'G']  # First timestep columns
        var_pos = variable_positions[variable]
        
        # Get columns for all 5 timesteps
        cols = []
        for t in range(5):  # 5 timesteps
            col_index = var_pos + (t * 6)  # 6 variables per timestep
            col_letter = chr(ord('B') + col_index)  # Convert to column letter
            cols.append(col_letter)
        
        return cols

    def on_variable_changed(self, variable):
        """Handle variable selection change"""
        # Store current variable
        self.current_variable = variable
        
        # Get columns for the selected variable
        cols = self.get_columns_for_variable(variable)
        
        # Read data with new columns
        df_weights = pd.read_excel('Data_.xlsx', 
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

    def add_sensors(self):
        try:
            print("\n=== Starting Sensor Data Loading ===")
            
            # Read sensor data from Excel
            print("Attempting to read Excel file...")
            df_sensors = pd.read_excel('Data_.xlsx', 
                                     sheet_name='Sensor Location',
                                     skiprows=1)  # Skip the header row
            
            print("\nDataFrame Head:")
            print(df_sensors.head())
            
            print("\nDataFrame Columns:")
            print(df_sensors.columns.tolist())
            
            # Rename columns to match expected structure
            df_sensors.columns = ['Sensors', 'Descriptions', 'Location', 'x(m)', 'y(m)', 'z(m)', 'Color']
            
            print("\nAfter renaming columns:")
            print(df_sensors.columns.tolist())
            
            # Clear existing sensor data
            self.sensor_actors = []
            self.sensor_info = []
            
            # Define color mapping for sensor types
            sensor_colors = {
                'Accelerometer': (1.0, 0.0, 0.0),    # Red
                'Strain Gauge': (0.0, 1.0, 0.0),     # Green
                'Camera': (1.0, 0.65, 0.0)           # Orange
            }
            
            print("\nProcessing individual sensors:")
            # Process each sensor
            for index, row in df_sensors.iterrows():
                print(f"\n--- Sensor {index + 1} ---")
                sensor_name = str(row['Sensors'])  # Convert to string in case it's not
                print(f"Sensor Name: {sensor_name}")
                
                # Determine sensor type and color
                sensor_type = None
                for type_name in sensor_colors.keys():
                    if type_name.lower() in sensor_name.lower():
                        sensor_type = type_name
                        break
                
                print(f"Detected Type: {sensor_type}")
                
                if sensor_type is None:
                    print("Warning: Sensor type not recognized - skipping")
                    continue
                
                # Get coordinates
                try:
                    x = float(row['x(m)'])
                    y = float(row['y(m)'])
                    z = float(row['z(m)'])
                    print(f"Coordinates: x={x}, y={y}, z={z}")
                except Exception as e:
                    print(f"Error converting coordinates: {e}")
                    print(f"Raw coordinate values: x={row['x(m)']}, y={row['y(m)']}, z={row['z(m)']}")
                    continue
                
                # Create sphere for sensor
                print("Creating sphere...")
                sphere = vtk.vtkSphereSource()
                sphere.SetCenter(x, y, z)
                sphere.SetRadius(0.5)
                
                # Create mapper
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(sphere.GetOutputPort())
                
                # Create actor
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.GetProperty().SetColor(sensor_colors[sensor_type])
                actor.GetProperty().SetOpacity(0.7)
                
                # Store sensor information
                self.sensor_info.append({
                    'type': sensor_type,
                    'description': row['Descriptions'],
                    'location': row['Location'],
                    'x': x,
                    'y': y,
                    'z': z
                })
                
                # Store actor reference
                self.sensor_actors.append(actor)
                
                # Add to renderer
                self.renderer.AddActor(actor)
                print(f"Sensor actor added to renderer: {sensor_type} at ({x}, {y}, {z})")
                
            print(f"\nTotal sensors processed: {len(self.sensor_actors)}")
            print("=== Sensor Loading Complete ===\n")
                
        except Exception as e:
            print(f"\nCRITICAL ERROR loading sensor data:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Stack trace:")
            import traceback
            traceback.print_exc()

    def setup_sensor_graph_controls(self):
        
        # Create Accelerometer dropdown
        self.accel_label = QLabel("Accelerometer Graphs:")
        self.control_layout.addWidget(self.accel_label)
        
        self.accel_combo = QComboBox()
        self.accel_combo.addItems([f'Accelerometer {i}' for i in range(1, 13)])
        self.accel_combo.currentTextChanged.connect(self.show_accelerometer_graph)
        self.control_layout.addWidget(self.accel_combo)
        
        # Create Strain Gauge dropdown
        self.strain_label = QLabel("Strain Gauge Graphs:")
        self.control_layout.addWidget(self.strain_label)
        
        self.strain_combo = QComboBox()
        self.strain_combo.addItems([f'Strain Gauge {i}' for i in range(1, 13)])
        self.strain_combo.currentTextChanged.connect(self.show_strain_gauge_graph)
        self.control_layout.addWidget(self.strain_combo)

    def load_sensor_data(self):
        """Load both accelerometer and strain gauge data"""
        try:
            # Load accelerometer data
            self.accel_data = pd.read_excel('Data_.xlsx', 
                                          sheet_name='Accelerometer Data',
                                          skiprows=0)  # Don't skip first row as it contains headers
            print("Accelerometer data loaded successfully")
            print("Columns:", self.accel_data.columns.tolist())
            
            # Load strain gauge data
            self.strain_data = pd.read_excel('Data_.xlsx',
                                           sheet_name='Strain Gauge Data',
                                           skiprows=0)
            print("Strain gauge data loaded successfully")
            print("Columns:", self.strain_data.columns.tolist())
            
        except Exception as e:
            print(f"Error loading sensor data: {e}")
            self.accel_data = None
            self.strain_data = None

    def show_accelerometer_graph(self, selection):
        """Show graph for selected accelerometer"""
        if self.accel_data is not None:
            try:
                # Extract accelerometer number
                accel_num = int(selection.split()[-1])
                
                # Get time and accelerometer data
                time_data = self.accel_data['Time (s)']
                accel_data = self.accel_data[f'Accelerometer {accel_num}']
                
                # Create and show graph
                title = f"Accelerometer {accel_num} Data"
                graph_window = AccelerometerGraph(time_data, accel_data, title, self)
                graph_window.exec_()
                
            except Exception as e:
                msg = QMessageBox()
                msg.setWindowTitle("Error")
                msg.setText(f"Error displaying accelerometer data: {str(e)}")
                msg.exec_()

    def show_strain_gauge_graph(self, selection):
        """Show graph for selected strain gauge"""
        if self.strain_data is not None:
            try:
                # Extract strain gauge number
                gauge_num = int(selection.split()[-1])
                
                # Get time and strain gauge data
                time_data = self.strain_data['Time (s)']
                strain_data = self.strain_data[f'Strain Gauge {gauge_num}']
                
                # Create and show graph
                title = f"Strain Gauge {gauge_num} Data"
                graph_window = AccelerometerGraph(time_data, strain_data, title, self)
                graph_window.exec_()
                
            except Exception as e:
                msg = QMessageBox()
                msg.setWindowTitle("Error")
                msg.setText(f"Error displaying strain gauge data: {str(e)}")
                msg.exec_()

        
    def setup_visualization(self):
        # Store current variable
        self.current_variable = 'U1'  # Default variable
        
        # Get columns for the selected variable
        cols = self.get_columns_for_variable(self.current_variable)
        
        # Read data
        df_weights = pd.read_excel('Data_.xlsx', 
                                 sheet_name='Variables for 5 Timesteps', 
                                 header=None, 
                                 skiprows=1,  # Skip first row
                                 usecols=[0] + [ord(col) - ord('A') for col in cols],  # Convert column letters to indices
                                 nrows=1882)
        
        # Rename columns appropriately
        df_weights.columns = ['number'] + [f'weight_t{i+1}' for i in range(5)]
        
        # Rest of the code remains the same until node_weights creation
        df_nodes = pd.read_excel('data.xlsx', sheet_name='Sheet1', header=None, skiprows=5, usecols='I:L', nrows=1882)
        df_nodes.columns = ['number', 'x', 'y', 'z']

        df_conn = pd.read_excel('data.xlsx', sheet_name='Sheet1', header=None, skiprows=4, usecols='A:E', nrows=1882)
        df_conn.columns = ['Element', 'Node1', 'Node2', 'Node3', 'Node4']

        # Create points
        points = vtk.vtkPoints()

        # Map node number to index and store weights
        self.node_to_index = {}
        self.node_weights = {}
        current_index = 0

        # Insert points and store weights
        for index, row in df_nodes.iterrows():
            node_num = int(row['number'])
            points.InsertNextPoint(row['x'], row['y'], row['z'])
            
            if node_num in df_weights['number'].values:
                weight_row = df_weights[df_weights['number'] == node_num].iloc[0]
                self.node_weights[node_num] = [
                    float(weight_row[f'weight_t{i+1}']) for i in range(5)
                ]
            else:
                self.node_weights[node_num] = [0.0] * 5
            
            self.node_to_index[node_num] = current_index
            current_index += 1

        # Create lookup table for colors
        self.lut = vtk.vtkLookupTable()
        self.lut.SetHueRange(0.0, 0.667)  # Red to Blue
        self.lut.SetSaturationRange(1.0, 1.0)
        self.lut.SetValueRange(1.0, 1.0)
        self.lut.SetNumberOfTableValues(64)
        self.lut.Build()

        # Create data structures
        self.point_polydata = vtk.vtkPolyData()
        self.point_polydata.SetPoints(points)

        self.edge_polydata = vtk.vtkPolyData()
        self.edge_polydata.SetPoints(points)

        self.plane_polydata = vtk.vtkPolyData()
        self.plane_polydata.SetPoints(points)

        # Store connectivity information
        self.edges = []
        self.planes = []

        for index, row in df_conn.iterrows():
            if pd.isna(row['Node3']):
                if int(row['Node1']) in self.node_to_index and int(row['Node2']) in self.node_to_index:
                    self.edges.append((int(row['Node1']), int(row['Node2'])))
            elif not pd.isna(row['Node4']):
                if all(int(row[f'Node{i}']) in self.node_to_index for i in [1, 2, 3, 4]):
                    self.planes.append((
                        int(row['Node1']),
                        int(row['Node2']),
                        int(row['Node3']),
                        int(row['Node4'])
                    ))

        # Create sphere source for points
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(0.1)

        # Create glyph for points
        glyph = vtk.vtkGlyph3D()
        glyph.SetInputData(self.point_polydata)
        glyph.SetSourceConnection(sphere.GetOutputPort())
        glyph.ScalingOff()

        # Create mappers
        self.point_mapper = vtk.vtkPolyDataMapper()
        self.point_mapper.SetInputConnection(glyph.GetOutputPort())
        self.point_mapper.SetLookupTable(self.lut)

        self.edge_mapper = vtk.vtkPolyDataMapper()
        self.edge_mapper.SetInputData(self.edge_polydata)
        self.edge_mapper.SetLookupTable(self.lut)
        self.edge_mapper.ScalarVisibilityOn()

        self.plane_mapper = vtk.vtkPolyDataMapper()
        self.plane_mapper.SetInputData(self.plane_polydata)
        self.plane_mapper.SetLookupTable(self.lut)
        self.plane_mapper.ScalarVisibilityOn()

        # Create actors
        self.point_actor = vtk.vtkActor()
        self.point_actor.SetMapper(self.point_mapper)
        self.point_actor.GetProperty().SetOpacity(1.0)
        self.point_actor.GetProperty().SetColor(1.0, 1.0, 1.0)  # White color

        self.edge_actor = vtk.vtkActor()
        self.edge_actor.SetMapper(self.edge_mapper)
        self.edge_actor.GetProperty().SetLineWidth(1)
        self.edge_actor.GetProperty().SetOpacity(1.0)

        self.plane_actor = vtk.vtkActor()
        self.plane_actor.SetMapper(self.plane_mapper)
        self.plane_actor.GetProperty().SetOpacity(1.0)

        # Add actors to renderer
        self.renderer.AddActor(self.plane_actor)
        self.renderer.AddActor(self.edge_actor)
        self.renderer.AddActor(self.point_actor)
        self.renderer.SetBackground(0.0, 0.0, 0.0)

        # Create scalar bar
        self.scalar_bar = vtk.vtkScalarBarActor()
        self.scalar_bar.SetLookupTable(self.lut)
        self.scalar_bar.SetTitle("Weight Values")
        self.scalar_bar.SetNumberOfLabels(5)
        self.scalar_bar.SetWidth(0.15)
        self.scalar_bar.SetHeight(0.3)
        self.scalar_bar.SetPosition(0.82, 0.65)

        # Configure scalar bar text properties
        scalar_bar_title = self.scalar_bar.GetTitleTextProperty()
        scalar_bar_title.SetColor(1.0, 1.0, 1.0)  # White text
        scalar_bar_title.SetFontSize(12)
        scalar_bar_title.SetBold(1)

        scalar_bar_labels = self.scalar_bar.GetLabelTextProperty()
        scalar_bar_labels.SetColor(1.0, 1.0, 1.0)  # White text
        scalar_bar_labels.SetFontSize(10)

        self.renderer.AddActor2D(self.scalar_bar)

        # Create node labels
        self.node_labels = []
        for node_num, index in self.node_to_index.items():
            point = points.GetPoint(index)
            
            follower = vtk.vtkBillboardTextActor3D()
            follower.SetInput(str(node_num))
            follower.SetPosition(point[0], point[1] + 1.0, point[2])
            
            text_property = follower.GetTextProperty()
            text_property.SetColor(1.0, 1.0, 0.0)  # Yellow color
            text_property.SetFontSize(6)
            text_property.SetBold(0)
            text_property.SetJustificationToCentered()
            text_property.SetVerticalJustificationToCentered()
            
            follower.SetPickable(0)
            follower.SetVisibility(1)
            
            self.node_labels.append(follower)
            self.renderer.AddActor(follower)

        # Initialize time step
        self.update_geometry(0)
        self.add_sensors()
        
    def update_labels(self, selection):
        if selection == 'Show All Labels':
            for label in self.node_labels:
                label.SetVisibility(1)
        elif selection == 'Hide All Labels':
            for label in self.node_labels:
                label.SetVisibility(0)
        elif selection == 'Show Random 50 Labels':
            visible_indices = set(random.sample(range(len(self.node_labels)), min(50, len(self.node_labels))))
            for i, label in enumerate(self.node_labels):
                label.SetVisibility(1 if i in visible_indices else 0)
        self.render_window.Render()

    def update_time_step(self, obj, event):
        current_time = time.time()
        # Only update if 1 second has passed
        if current_time - self.last_update >= 1.0:
            time_step = self.timer_count % 5  # Changed to cycle through 5 timesteps
            self.update_geometry(time_step)
            self.scalar_bar.SetTitle(f"Weight Values\nt = {time_step + 1}")
            self.timer_count += 1
            self.render_window.Render()
            self.last_update = current_time

    def update_geometry(self, time_step):
        current_weights = []
        
        # Update point weights
        point_weights = vtk.vtkDoubleArray()
        point_weights.SetName("Weights")
        for node_num in self.node_to_index.keys():
            weight = self.node_weights[node_num][time_step]
            point_weights.InsertNextValue(weight)
            current_weights.append(weight)
        
        # Update edge geometry and weights
        edge_cells = vtk.vtkCellArray()
        edge_weights = vtk.vtkDoubleArray()
        edge_weights.SetName("Edge Weights")
        
        for node1, node2 in self.edges:
            weight1 = self.node_weights[node1][time_step]
            weight2 = self.node_weights[node2][time_step]
            edge_weight = (weight1 + weight2) / 2.0
            edge_weights.InsertNextValue(edge_weight)
            current_weights.append(edge_weight)
            
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, self.node_to_index[node1])
            line.GetPointIds().SetId(1, self.node_to_index[node2])
            edge_cells.InsertNextCell(line)
        
        # Update plane geometry and weights
        plane_cells = vtk.vtkCellArray()
        plane_weights = vtk.vtkDoubleArray()
        plane_weights.SetName("Plane Weights")
        
        for node1, node2, node3, node4 in self.planes:
            weights_for_quad = [
                self.node_weights[node][time_step]
                for node in [node1, node2, node3, node4]
            ]
            plane_weight = sum(weights_for_quad) / 4.0
            plane_weights.InsertNextValue(plane_weight)
            current_weights.append(plane_weight)
            
            quad = vtk.vtkQuad()
            quad.GetPointIds().SetId(0, self.node_to_index[node1])
            quad.GetPointIds().SetId(1, self.node_to_index[node2])
            quad.GetPointIds().SetId(2, self.node_to_index[node3])
            quad.GetPointIds().SetId(3, self.node_to_index[node4])
            plane_cells.InsertNextCell(quad)
        
        # Update ranges and data
        current_min = min(current_weights)
        current_max = max(current_weights)
        
        self.lut.SetTableRange(current_min, current_max)
        self.lut.Build()
        
        self.point_polydata.GetPointData().SetScalars(point_weights)
        self.edge_polydata.SetLines(edge_cells)
        self.edge_polydata.GetCellData().SetScalars(edge_weights)
        self.plane_polydata.SetPolys(plane_cells)
        self.plane_polydata.GetCellData().SetScalars(plane_weights)
        
        self.point_mapper.SetScalarRange(current_min, current_max)
        self.edge_mapper.SetScalarRange(current_min, current_max)
        self.plane_mapper.SetScalarRange(current_min, current_max)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(100, 100, 1000, 800)
    window.show()
    
    # Initialize VTK interaction
    window.interactor.Initialize()
    window.interactor.Start()
    
    sys.exit(app.exec_())