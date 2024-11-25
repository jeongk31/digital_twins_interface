# visualization.py
import vtk
import pandas as pd
import numpy as np
from data_handler import DataHandler
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtWidgets import QLabel, QComboBox, QHBoxLayout, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer

class Visualization:
    def __init__(self, renderer):
        self.renderer = renderer
        self.point_polydata = vtk.vtkPolyData()
        self.edge_polydata = vtk.vtkPolyData()
        self.plane_polydata = vtk.vtkPolyData()
        self.node_labels = []
        self.highlighted_nodes = []
        
        # Define damage data
        self.damage_data = {
            4: {"status": "No", "damage_type": "", "location": None},
            6: {"status": "Yes", "damage_type": "20%", "location": 1},
            8: {"status": "Yes", "damage_type": "40%", "location": 2},
            10: {"status": "Yes", "damage_type": "Failure", "location": 3},
            12: {"status": "Yes", "damage_type": "Failure", "location": 4},
            14: {"status": "Yes", "damage_type": "Failure", "location": 5},
            16: {"status": "Yes", "damage_type": "Failure", "location": 6},
            18: {"status": "Yes", "damage_type": "Failure", "location": 7},
            20: {"status": "Yes", "damage_type": "Failure", "location": 8},
            22: {"status": "Yes", "damage_type": "Failure", "location": 9}
        }
        
        self.times = sorted(self.damage_data.keys())
        self.current_time_index = 0
        
        # Color mapping for damage types
        self.damage_colors = {
            "": (0.0, 1.0, 0.0),      # Green for safe
            "20%": (1.0, 1.0, 0.0),   # Yellow for 20% damage
            "40%": (1.0, 0.5, 0.0),   # Orange for 40% damage
            "Failure": (1.0, 0.0, 0.0) # Red for failure
        }
        
        # Define the parts structure
        self.parts = {
            'part1': {
                'arc1': [979, 978, 977, 976, 975, 974, 973],
                'arc2': [1358, 1359, 1360, 1361, 1362, 1363, 1364]
            },
            'part2': {
                'arc1': [991, 990, 1403, 1402],
                'arc2': [996, 997, 1375, 1376],
                'bar': [992, 993, 994, 995]
            },
            'part3': {
                'arc1': [1427, 1426, 1425, 1424],
                'arc2': [1569, 1570, 1571, 1572]
            },
            'part4': {
                'arc1': [1310, 1309, 1308, 1307],
                'arc2': [1210, 1211, 1212, 1213],
                'bar': [1537, 1538, 1539, 1540]
            },
            'part5': {
                'arc1': [1314, 1313, 1312, 1311],
                'arc2': [1214, 1215, 1216, 1217]
            },
            'part6': {
                'arc1': [1330, 1329, 1061, 1060],
                'arc2': [695, 696, 697, 698],
                'bar': [1056, 1057, 1058, 1059]
            },
            'part7': {
                'arc1': [1147, 1146, 1145, 1144],
                'arc2': [699, 700, 701, 702]
            },
            'part8': {
                'arc1': [710, 709, 1079, 1078],
                'arc2': [703, 704, 1076, 1077],
                'bar': [705, 706, 707, 708]
            },
            'part9': {
                'arc1': [717, 716, 715, 714, 713, 712, 711],
                'arc2': [1090, 1091, 1092, 1093, 1094, 1095, 1096]
            }
        }
        
        # Initialize element colors dictionary with default colors
        self.element_colors = {}
        self.set_initial_colors()

        self.status_actor = None
        self.status_message = "Bridge is safe"
        
        # Create timer for automatic updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_next_time)
        self.timer.start(2000)

    def set_initial_colors(self):
        # Set all elements to white first
        for part in self.parts.values():
            for group in part.values():
                for element in group:
                    self.element_colors[element] = (1.0, 1.0, 1.0)  # White
        
        # Set arch and bar elements to green
        for part in self.parts.values():
            for group_type in ['arc1', 'arc2', 'bar']:  # Added 'bar' to the list
                if group_type in part:
                    for element in part[group_type]:
                        self.element_colors[element] = (0.0, 1.0, 0.0)  # Green

    def update_time(self, time_str):
        time = int(time_str)
        damage_info = self.damage_data[time]
        
        # Reset colors to initial state
        self.set_initial_colors()
        
        # Update colors based on damage
        if damage_info["status"] == "Yes":
            location = damage_info["location"]
            damage_type = damage_info["damage_type"]
            damage_color = self.damage_colors[damage_type]
            
            # Update colors for the specified location
            if f'part{location}' in self.parts:
                for group_type in ['arc1', 'arc2']:
                    if group_type in self.parts[f'part{location}']:
                        for element in self.parts[f'part{location}'][group_type]:
                            self.element_colors[element] = damage_color
        
        # Update status message
        if damage_info["status"] == "Yes":
            self.status_message = f"{damage_info['damage_type']} damage at location {damage_info['location']}"
        else:
            self.status_message = "Bridge is safe"
        
        self.update_status_text()
        self.update_geometry(self.current_node_to_index, self.current_edges, self.current_planes)


    def setup_ui(self, parent_layout):
        # Create dropdown for time selection
        time_layout = QHBoxLayout()
        time_label = QLabel("Time:")
        self.time_combo = QComboBox()
        
        # Add times to dropdown
        times = sorted(self.damage_data.keys())
        for time in times:
            self.time_combo.addItem(str(time))
        
        # Connect dropdown to update function
        self.time_combo.currentTextChanged.connect(self.update_time)
        
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_combo)
        time_layout.addStretch()
        
        parent_layout.addLayout(time_layout)

    

    def update_next_time(self):
        # Update to next time
        self.current_time_index = (self.current_time_index + 1) % len(self.times)
        current_time = self.times[self.current_time_index]
        
        # Update visualization for current time
        damage_info = self.damage_data[current_time]
        
        # Reset colors to initial state
        self.set_initial_colors()
        
        # Update colors based on damage
        if damage_info["status"] == "Yes":
            location = damage_info["location"]
            damage_type = damage_info["damage_type"]
            damage_color = self.damage_colors[damage_type]
            
            # Update colors for the specified location
            if f'part{location}' in self.parts:
                # Update arcs and bars
                for group_type in ['arc1', 'arc2', 'bar']:  # Added 'bar' here
                    if group_type in self.parts[f'part{location}']:
                        for element in self.parts[f'part{location}'][group_type]:
                            self.element_colors[element] = damage_color
        
        # Update status message
        if damage_info["status"] == "Yes":
            self.status_message = f"Time {current_time}: {damage_info['damage_type']} damage at location {damage_info['location']}"
        else:
            self.status_message = f"Time {current_time}: Bridge is safe"
        
        self.update_status_text()
        self.update_geometry(self.current_node_to_index, self.current_edges, self.current_planes)

        
    def update_status_text(self):
        if self.status_actor:
            self.renderer.RemoveActor(self.status_actor)
        
        # Create status text actor
        self.status_actor = vtk.vtkTextActor()
        self.status_actor.SetInput(self.status_message)
        
        # Set text properties
        text_property = self.status_actor.GetTextProperty()
        text_property.SetColor(1.0, 1.0, 1.0)  # White text
        text_property.SetFontSize(16)
        text_property.SetJustificationToCentered()
        text_property.SetVerticalJustificationToBottom()
        
        # Position at bottom center
        self.status_actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        self.status_actor.SetPosition(0.5, 0.02)
        
        self.renderer.AddActor2D(self.status_actor)
        self.renderer.GetRenderWindow().Render()


    def update_visualization(self):
        # Get current colors
        current_time = int(self.time_combo.currentText())
        damage_info = self.damage_data[current_time]
        
        # Reset colors to initial state
        self.set_initial_colors()
        
        # Update colors based on damage
        if damage_info["status"] == "Yes":
            location = damage_info["location"]
            damage_type = damage_info["damage_type"]
            damage_color = self.damage_colors[damage_type]
            
            # Update colors for the specified location
            if f'part{location}' in self.parts:
                for group_type in ['arc1', 'arc2']:
                    if group_type in self.parts[f'part{location}']:
                        for element in self.parts[f'part{location}'][group_type]:
                            self.element_colors[element] = damage_color
        
        # Update the visualization
        self.update_geometry(self.current_node_to_index, self.current_edges, self.current_planes)
        self.renderer.GetRenderWindow().Render()    

    def create_color_legend(self):
        # Remove old legend if it exists
        if hasattr(self, 'legend_actors'):
            for actor in self.legend_actors:
                self.renderer.RemoveActor(actor)
        
        self.legend_actors = []
        
        # Legend entries with colors and descriptions
        legend_items = [
            ("Safe", (0.0, 1.0, 0.0)),         # Green
            ("20% Damage", (1.0, 1.0, 0.0)),   # Yellow
            ("40% Damage", (1.0, 0.5, 0.0)),   # Orange
            ("Failure", (1.0, 0.0, 0.0))       # Red
        ]
        
        # Position for the first line of text (top-right corner)
        y_position = 0.95
        x_position = 0.85
        
        for text, color in legend_items:
            # Create text actor
            text_actor = vtk.vtkTextActor()
            text_actor.SetInput(f"■ {text}")
            
            # Set text properties
            text_property = text_actor.GetTextProperty()
            text_property.SetColor(*color)  # Use the color for both square and text
            text_property.SetFontSize(14)
            text_property.SetBold(1)
            
            # Position the text
            text_actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
            text_actor.SetPosition(x_position, y_position)
            
            # Add to renderer and store reference
            self.renderer.AddActor2D(text_actor)
            self.legend_actors.append(text_actor)
            
            # Update y position for next item
            y_position -= 0.05

    def setup_visualization(self):
        # Load geometry data
        df_nodes, df_conn = DataHandler.load_geometry_data()
        if df_nodes is None or df_conn is None:
            return None

        # Create points
        points = vtk.vtkPoints()
        node_to_index = {}
        current_index = 0
        
        # Define key points to label
        key_points = [
            (115, 0, 0),
            (115, 0, 12.4),
            (0, 0, 0),
            (0, 0, 12.4)
        ]
        tolerance = 0.1

        # Insert points and create labels
        for index, row in df_nodes.iterrows():
            node_num = int(row['number'])
            x, y, z = row['x'], row['y'], row['z']
            points.InsertNextPoint(x, y, z)
            node_to_index[node_num] = current_index
            
            # Check if this point should be labeled
            should_label = False
            
            # Check if point matches any key points
            for kx, ky, kz in key_points:
                if (abs(x - kx) < tolerance and 
                    abs(y - ky) < tolerance and 
                    abs(z - kz) < tolerance):
                    should_label = True
                    break
            
            # Check if y > 0 (arch points)
            if y > 1 and y > 12:
                should_label = True
            
            
            current_index += 1

        # Set points for all polydata objects
        self.point_polydata.SetPoints(points)
        self.edge_polydata.SetPoints(points)
        self.plane_polydata.SetPoints(points)

        # Process connectivity
        edges = []
        planes = []

        for index, row in df_conn.iterrows():
            if pd.isna(row['Node3']):
                if int(row['Node1']) in node_to_index and int(row['Node2']) in node_to_index:
                    edges.append((int(row['Node1']), int(row['Node2'])))
            elif not pd.isna(row['Node4']):
                if all(int(row[f'Node{i}']) in node_to_index for i in [1, 2, 3, 4]):
                    planes.append((
                        int(row['Node1']),
                        int(row['Node2']),
                        int(row['Node3']),
                        int(row['Node4'])
                    ))

        self.create_visualization_actors(points)
        self.update_geometry(node_to_index, edges, planes)

        # Add legend
        self.create_color_legend()
        
        # Set camera position for better initial view
        camera = self.renderer.GetActiveCamera()
        camera.SetPosition(0, 100, 100)
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 1, 0)
        self.renderer.ResetCamera()

        self.current_node_to_index = node_to_index
        self.current_edges = edges
        self.current_planes = planes

        self.update_status_text()

    def highlight_node(self, x, y, z):
        """Create a highlighted sphere for important nodes"""
        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(x, y, z)
        sphere.SetRadius(0.3)  # Larger radius for emphasis
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # Red color
        actor.GetProperty().SetOpacity(0.8)
        
        self.highlighted_nodes.append(actor)
        self.renderer.AddActor(actor)

    def create_visualization_actors(self, points):
        # Create sphere source for regular points
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

        self.edge_mapper = vtk.vtkPolyDataMapper()
        self.edge_mapper.SetInputData(self.edge_polydata)

        self.plane_mapper = vtk.vtkPolyDataMapper()
        self.plane_mapper.SetInputData(self.plane_polydata)

        # Create actors with white color
        self.point_actor = vtk.vtkActor()
        self.point_actor.SetMapper(self.point_mapper)
        self.point_actor.GetProperty().SetColor(1.0, 1.0, 1.0)

        self.edge_actor = vtk.vtkActor()
        self.edge_actor.SetMapper(self.edge_mapper)
        self.edge_actor.GetProperty().SetColor(1.0, 1.0, 1.0)
        self.edge_actor.GetProperty().SetLineWidth(1)

        self.plane_actor = vtk.vtkActor()
        self.plane_actor.SetMapper(self.plane_mapper)
        self.plane_actor.GetProperty().SetColor(1.0, 1.0, 1.0)

        # Add actors to renderer
        self.renderer.AddActor(self.plane_actor)
        self.renderer.AddActor(self.edge_actor)
        self.renderer.AddActor(self.point_actor)
        self.renderer.SetBackground(0.0, 0.0, 0.0)

    def update_geometry(self, node_to_index, edges, planes):
        # Update edge geometry
        edge_cells = vtk.vtkCellArray()
        edge_colors = vtk.vtkUnsignedCharArray()
        edge_colors.SetNumberOfComponents(3)
        edge_colors.SetName("Colors")
        
        # Get the connectivity data once
        df_nodes, df_conn = DataHandler.load_geometry_data()
        
        # Process edges and assign colors
        for node1, node2 in edges:
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, node_to_index[node1])
            line.GetPointIds().SetId(1, node_to_index[node2])
            edge_cells.InsertNextCell(line)
            
            # Find the element number for this edge
            element_found = False
            element_rows = df_conn[
                (pd.isna(df_conn['Node3'])) & 
                (
                    ((df_conn['Node1'] == node1) & (df_conn['Node2'] == node2)) |
                    ((df_conn['Node1'] == node2) & (df_conn['Node2'] == node1))
                )
            ]
            
            if not element_rows.empty:
                element_num = int(element_rows.iloc[0]['Element'])
                if element_num in self.element_colors:
                    color = self.element_colors[element_num]
                    edge_colors.InsertNextTuple3(
                        int(color[0] * 255),
                        int(color[1] * 255),
                        int(color[2] * 255)
                    )
                    element_found = True
            
            if not element_found:
                edge_colors.InsertNextTuple3(255, 255, 255)  # White for non-specified edges
        
        # Update plane geometry
        plane_cells = vtk.vtkCellArray()
        for node1, node2, node3, node4 in planes:
            quad = vtk.vtkQuad()
            quad.GetPointIds().SetId(0, node_to_index[node1])
            quad.GetPointIds().SetId(1, node_to_index[node2])
            quad.GetPointIds().SetId(2, node_to_index[node3])
            quad.GetPointIds().SetId(3, node_to_index[node4])
            plane_cells.InsertNextCell(quad)
        
        # Set geometry
        self.edge_polydata.SetLines(edge_cells)
        self.edge_polydata.GetCellData().SetScalars(edge_colors)
        self.plane_polydata.SetPolys(plane_cells)

        self.renderer.GetRenderWindow().Render()