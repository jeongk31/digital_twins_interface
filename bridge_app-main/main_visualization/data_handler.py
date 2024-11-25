import pandas as pd

class DataHandler:
    @staticmethod
    def load_sensor_data():
        """Load both accelerometer and strain gauge data."""
        try:
            accel_data = pd.read_excel('../data/Data_.xlsx', sheet_name='Accelerometer Data', skiprows=0)
            strain_data = pd.read_excel('../data/Data_.xlsx', sheet_name='Strain Gauge Data', skiprows=0)
            return accel_data, strain_data
        except Exception as e:
            print(f"Error loading sensor data: {e}")
            return None, None

    @staticmethod
    def get_columns_for_variable(variable):
        """Return columns corresponding to the variable for all timesteps."""
        variable_positions = {'U1': 0, 'U2': 1, 'U3': 2, 'R1': 3, 'R2': 4, 'R3': 5}
        base_cols = ['B', 'C', 'D', 'E', 'F', 'G']
        var_pos = variable_positions[variable]

        return [chr(ord('B') + var_pos + t * 6) for t in range(5)]

    @staticmethod
    def load_geometry_data():
        """Load node and connectivity data."""
        try:
            df_nodes = pd.read_excel('../data/data.xlsx', sheet_name='Sheet1', header=None, skiprows=5, usecols='I:L', nrows=1882)
            df_nodes.columns = ['number', 'x', 'y', 'z']

            df_conn = pd.read_excel('../data/data.xlsx', sheet_name='Sheet1', header=None, skiprows=4, usecols='A:E', nrows=1882)
            df_conn.columns = ['Element', 'Node1', 'Node2', 'Node3', 'Node4']

            return df_nodes, df_conn
        except Exception as e:
            print(f"Error loading geometry data: {e}")
            return None, None
