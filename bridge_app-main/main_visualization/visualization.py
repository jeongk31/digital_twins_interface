import vtk
import random
import pandas as pd
from data_handler import DataHandler

class Visualization:
    def __init__(self, renderer):
        self.renderer = renderer
        self.setup_lookup_table()
        self.node_labels = []
        # Create data structures
        self.point_polydata = vtk.vtkPolyData()
        self.edge_polydata = vtk.vtkPolyData()
        self.plane_polydata = vtk.vtkPolyData()

    def setup_lookup_table(self):
        """Set up color lookup table for visualization with better defaults"""
        self.lut = vtk.vtkLookupTable()
        self.lut.SetHueRange(0.667, 0.0)  # Blue to Red (reversed)
        self.lut.SetSaturationRange(1.0, 1.0)
        self.lut.SetValueRange(1.0, 1.0)
        self.lut.SetNumberOfTableValues(256)  # Increased for smoother gradients
        self.lut.SetNanColor(0.0, 0.0, 0.0, 0.0)  # Make NaN values transparent
        self.lut.Build()

    def setup_visualization(self, current_variable='U1'):
        # Get columns for the selected variable
        cols = DataHandler.get_columns_for_variable(current_variable)
        
        # Read weights data
        df_weights = pd.read_excel('../data/Data_.xlsx', 
                                 sheet_name='Variables for 5 Timesteps', 
                                 header=None, 
                                 skiprows=1,
                                 usecols=[0] + [ord(col) - ord('A') for col in cols],
                                 nrows=1882)
        
        df_weights.columns = ['number'] + [f'weight_t{i+1}' for i in range(5)]
        
        # Load geometry data
        df_nodes, df_conn = DataHandler.load_geometry_data()
        if df_nodes is None or df_conn is None:
            return None, None, None, None

        # Create points
        points = vtk.vtkPoints()

        # Map node number to index and store weights
        node_to_index = {}
        node_weights = {}
        current_index = 0

        # Insert points and store weights
        for index, row in df_nodes.iterrows():
            node_num = int(row['number'])
            points.InsertNextPoint(row['x'], row['y'], row['z'])
            
            if node_num in df_weights['number'].values:
                weight_row = df_weights[df_weights['number'] == node_num].iloc[0]
                node_weights[node_num] = [
                    float(weight_row[f'weight_t{i+1}']) for i in range(5)
                ]
            else:
                node_weights[node_num] = [0.0] * 5
            
            node_to_index[node_num] = current_index
            current_index += 1

        # Set points for all polydata objects
        self.point_polydata.SetPoints(points)
        self.edge_polydata.SetPoints(points)
        self.plane_polydata.SetPoints(points)

        # Store connectivity information
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
        self.create_node_labels(points, node_to_index)
        
        return node_to_index, node_weights, edges, planes

    def create_visualization_actors(self, points):
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
        self.point_actor.GetProperty().SetColor(1.0, 1.0, 1.0)

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

        # Create and configure scalar bar
        self.setup_scalar_bar()

    def setup_scalar_bar(self):
        self.scalar_bar = vtk.vtkScalarBarActor()
        self.scalar_bar.SetLookupTable(self.lut)
        self.scalar_bar.SetTitle("Weight Values")
        self.scalar_bar.SetNumberOfLabels(5)
        self.scalar_bar.SetWidth(0.15)
        self.scalar_bar.SetHeight(0.3)
        self.scalar_bar.SetPosition(0.82, 0.65)
        
        # Improve label formatting
        self.scalar_bar.SetLabelFormat("%.3e")  # Scientific notation with 3 decimal places
        
        # Configure scalar bar text properties
        scalar_bar_title = self.scalar_bar.GetTitleTextProperty()
        scalar_bar_title.SetColor(1.0, 1.0, 1.0)
        scalar_bar_title.SetFontSize(12)
        scalar_bar_title.SetBold(1)
        
        scalar_bar_labels = self.scalar_bar.GetLabelTextProperty()
        scalar_bar_labels.SetColor(1.0, 1.0, 1.0)
        scalar_bar_labels.SetFontSize(10)
        
        self.renderer.AddActor2D(self.scalar_bar)

    def create_node_labels(self, points, node_to_index):
        for node_num, index in node_to_index.items():
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

    def update_geometry(self, time_step, node_weights, node_to_index, edges, planes):
        current_weights = []
        
        # Update point weights
        point_weights = vtk.vtkDoubleArray()
        point_weights.SetName("Weights")
        for node_num in node_to_index.keys():
            weight = node_weights[node_num][time_step]
            point_weights.InsertNextValue(weight)
            current_weights.append(weight)
        
        # Update edge geometry and weights
        edge_cells = vtk.vtkCellArray()
        edge_weights = vtk.vtkDoubleArray()
        edge_weights.SetName("Edge Weights")
        
        for node1, node2 in edges:
            weight1 = node_weights[node1][time_step]
            weight2 = node_weights[node2][time_step]
            edge_weight = (weight1 + weight2) / 2.0
            edge_weights.InsertNextValue(edge_weight)
            current_weights.append(edge_weight)
            
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, node_to_index[node1])
            line.GetPointIds().SetId(1, node_to_index[node2])
            edge_cells.InsertNextCell(line)
        
        # Update plane geometry and weights
        plane_cells = vtk.vtkCellArray()
        plane_weights = vtk.vtkDoubleArray()
        plane_weights.SetName("Plane Weights")
        
        for node1, node2, node3, node4 in planes:
            weights_for_quad = [
                node_weights[node][time_step]
                for node in [node1, node2, node3, node4]
            ]
            plane_weight = sum(weights_for_quad) / 4.0
            plane_weights.InsertNextValue(plane_weight)
            current_weights.append(plane_weight)
            
            quad = vtk.vtkQuad()
            quad.GetPointIds().SetId(0, node_to_index[node1])
            quad.GetPointIds().SetId(1, node_to_index[node2])
            quad.GetPointIds().SetId(2, node_to_index[node3])
            quad.GetPointIds().SetId(3, node_to_index[node4])
            plane_cells.InsertNextCell(quad)

        # Handle color scaling more robustly
        if current_weights:
            # Filter out extreme values (optional)
            filtered_weights = [w for w in current_weights if abs(w) < 1e10]  # Adjust threshold as needed
            if filtered_weights:
                current_min = min(filtered_weights)
                current_max = max(filtered_weights)
            else:
                current_min = min(current_weights)
                current_max = max(current_weights)

            # Prevent division by zero and handle equal min/max
            if abs(current_max - current_min) < 1e-10:
                current_min -= 0.5
                current_max += 0.5

            # Update lookup table with new range
            self.lut.SetTableRange(current_min, current_max)
            self.lut.Build()
        else:
            # Fallback range if no weights
            self.lut.SetTableRange(-1, 1)
            self.lut.Build()
        
        # Update polydata
        self.point_polydata.GetPointData().SetScalars(point_weights)
        self.edge_polydata.SetLines(edge_cells)
        self.edge_polydata.GetCellData().SetScalars(edge_weights)
        self.plane_polydata.SetPolys(plane_cells)
        self.plane_polydata.GetCellData().SetScalars(plane_weights)
        
        # Update scalar ranges consistently
        range = self.lut.GetTableRange()
        self.point_mapper.SetScalarRange(range)
        self.edge_mapper.SetScalarRange(range)
        self.plane_mapper.SetScalarRange(range)

    def update_scalar_bar_title(self, time_step):
        self.scalar_bar.SetTitle(f"Weight Values\nt = {time_step + 1}")