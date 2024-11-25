import pandas as pd
import numpy as np

class BridgeDataProcessor:
    @staticmethod
    def load_data(filepath):
        """
        Load bridge data from Excel file with the specific format provided.
        """
        try:
            # Read element connectivity (columns A-E, skipping 4 rows)
            df_conn = pd.read_excel(
                filepath,
                sheet_name='Sheet1',
                header=None,
                skiprows=4,
                usecols='A:E',
                names=['Element', 'Node1', 'Node2', 'Node3', 'Node4']
            )
            
            # Read node coordinates (columns I-L, skipping 5 rows)
            df_nodes = pd.read_excel(
                filepath,
                sheet_name='Sheet1',
                header=None,
                skiprows=5,
                usecols='I:L',
                names=['number', 'x', 'y', 'z']
            )
            
            return df_conn, df_nodes
        except Exception as e:
            print(f"Error loading data: {e}")
            return None, None

    @staticmethod
    def find_connecting_elements(df_conn, node_sequences):
        """
        Find connecting elements between consecutive nodes in sequences.
        
        Parameters:
        df_conn: DataFrame with element connectivity
        node_sequences: Dictionary of node sequences to process
        
        Returns:
        Dictionary of element numbers connecting the nodes
        """
        results = {}
        
        for segment_name, points in node_sequences.items():
            results[segment_name] = {}
            
            for point_name, nodes in points.items():
                connecting_elements = []
                
                # Find elements connecting consecutive nodes
                for i in range(len(nodes)-1):
                    node1, node2 = nodes[i], nodes[i+1]
                    
                    # Look for elements where these nodes are connected
                    element = df_conn[
                        (
                            ((df_conn['Node1'] == node1) & (df_conn['Node2'] == node2)) |
                            ((df_conn['Node1'] == node2) & (df_conn['Node2'] == node1))
                        ) &
                        (df_conn['Node3'].isna())  # Ensure it's a 2-node element (edge)
                    ]
                    
                    if not element.empty:
                        connecting_elements.append(int(element.iloc[0]['Element']))
                    
                results[segment_name][point_name] = connecting_elements
        
        return results

# Define the node sequences
node_sequences = {
    'ARC1': {
        'point1': [625, 1056, 1055, 1054, 1053, 1052, 1051, 700],
        'point2': [700, 1050, 699, 1140, 745],
        'point3': [745, 1149, 1148, 1147, 878],
        'point4': [878, 1214, 848, 1126, 849],
        'point5': [849, 1201, 1200, 1199, 920],
        'point6': [920, 1198, 945, 1197, 944],
        'point7': [944, 1236, 1235, 1234, 825],
        'point8': [825, 1103, 826, 1230, 823],
        'point9': [823, 1094, 1093, 1092, 1091, 1090, 1089, 822]
    },
    'ARC2': {
        'point1': [948, 1215, 1216, 1217, 1218, 1219, 1220, 828],
        'point2': [828, 1107, 827, 1229, 949],
        'point3': [949, 1257, 1258, 1259, 900],
        'point4': [900, 1174, 901, 1175, 889],
        'point5': [889, 1176, 1177, 1178, 694],
        'point6': [694, 1041, 695, 1042, 696],
        'point7': [696, 1043, 1044, 1045, 697],
        'point8': [697, 1046, 698, 1139, 715],
        'point9': [715, 1141, 1142, 1143, 1144, 1145, 1146, 712]
    },
    'BARS': {
        'bar1': [826, 1104, 1105, 1106, 827],
        'bar2': [945, 1254, 1255, 1256, 901],
        'bar3': [848, 1123, 1124, 1125, 695],
        'bar4': [699, 1047, 1048, 1049, 698]
    }
}

def process_and_print_results(filepath):
    """
    Process the data and print results in a clear format.
    """
    # Load data
    processor = BridgeDataProcessor()
    df_conn, df_nodes = processor.load_data(filepath)
    
    if df_conn is None or df_nodes is None:
        print("Failed to load data")
        return
    
    # Find connecting elements
    results = processor.find_connecting_elements(df_conn, node_sequences)
    
    # Print results in a clear format
    for segment_name, points in results.items():
        print(f"\n{segment_name}:")
        for point_name, elements in points.items():
            print(f"\n{point_name}:")
            nodes = node_sequences[segment_name][point_name]
            for i, element in enumerate(elements):
                print(f"  Element {element}: connects nodes {nodes[i]}-{nodes[i+1]}")

# Usage
# process_and_print_results('path_to_your_data.xlsx')

process_and_print_results('data.xlsx')
