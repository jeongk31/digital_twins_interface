import vtk
from PyQt5.QtWidgets import QMessageBox

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