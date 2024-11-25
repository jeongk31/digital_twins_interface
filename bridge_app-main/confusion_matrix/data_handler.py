import pandas as pd

class DataHandler:
    @staticmethod
    def load_geometry_data():
        """Load node and connectivity data"""
        try:
            # Read node data
            df_nodes = pd.read_excel('../data/data.xlsx', 
                                   sheet_name='Sheet1', 
                                   header=None, 
                                   skiprows=5, 
                                   usecols='I:L', 
                                   nrows=1882)
            df_nodes.columns = ['number', 'x', 'y', 'z']

            # Read connectivity data
            df_conn = pd.read_excel('../data/data.xlsx', 
                                  sheet_name='Sheet1', 
                                  header=None, 
                                  skiprows=4, 
                                  usecols='A:E', 
                                  nrows=1882)
            df_conn.columns = ['Element', 'Node1', 'Node2', 'Node3', 'Node4']

            return df_nodes, df_conn

        except Exception as e:
            print(f"Error loading geometry data: {e}")
            return None, None