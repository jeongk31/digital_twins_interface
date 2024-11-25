import vtk
import pandas as pd

class SensorManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.sensor_actors = []
        self.sensor_info = []

        # Define color mapping for sensor types
        self.sensor_colors = {
            'Accelerometer': (1.0, 0.0, 0.0),    # Red
            'Strain Gauge': (0.0, 1.0, 0.0),     # Green
            'Camera': (1.0, 0.65, 0.0)           # Orange
        }

    def add_sensors(self):
        try:
            # Read sensor data from Excel
            df_sensors = pd.read_excel('../data/Data_.xlsx', 
                                       sheet_name='Sensor Location',
                                       skiprows=1)  # Skip header row
            df_sensors.columns = ['Sensors', 'Descriptions', 'Location', 'x(m)', 'y(m)', 'z(m)', 'Color']

            # Process each sensor
            for _, row in df_sensors.iterrows():
                sensor_name = str(row['Sensors'])
                sensor_type = next((t for t in self.sensor_colors if t.lower() in sensor_name.lower()), None)
                if not sensor_type:
                    continue

                # Get coordinates
                try:
                    x, y, z = float(row['x(m)']), float(row['y(m)']), float(row['z(m)'])
                except ValueError:
                    continue

                # Create sphere for sensor
                sphere = vtk.vtkSphereSource()
                sphere.SetCenter(x, y, z)
                sphere.SetRadius(0.5)

                # Create mapper and actor
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(sphere.GetOutputPort())

                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.GetProperty().SetColor(self.sensor_colors[sensor_type])
                actor.GetProperty().SetOpacity(0.7)

                # Store sensor information and actor reference
                self.sensor_info.append({
                    'type': sensor_type,
                    'description': row['Descriptions'],
                    'location': row['Location'],
                    'x': x,
                    'y': y,
                    'z': z
                })
                self.sensor_actors.append(actor)

                # Add to renderer
                self.renderer.AddActor(actor)

        except Exception as e:
            print(f"Error loading sensor data: {e}")
