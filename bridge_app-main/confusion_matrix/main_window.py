from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
from data_handler import DataHandler
from visualization import Visualization
from PyQt5.QtCore import QTimer


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowTitle("Bridge Visualization")
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor()
        layout.addWidget(self.vtkWidget)
        
        # Set up VTK pipeline
        self.render_window = self.vtkWidget.GetRenderWindow()
        self.renderer = vtk.vtkRenderer()
        self.render_window.AddRenderer(self.renderer)
        self.interactor = self.render_window.GetInteractor()
        
        # Set the basic interaction style
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)
        
        # Initialize visualization
        self.visualization = Visualization(self.renderer)
        self.visualization.setup_visualization()

    def setup_visualization(self):
        # Create visualization manager
        self.visualization = Visualization(self.renderer)
        self.visualization.setup_visualization()