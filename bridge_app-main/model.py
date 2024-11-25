import sys

import csv
import math
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget, QWidget, QHBoxLayout, QVBoxLayout, QToolBar, QAction, QCheckBox, QComboBox
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QLinearGradient, QColor
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# OpenGL Widget for rendering 3D elements with WASD controls and mouse rotation
class GLWidget(QOpenGLWidget):
    animation_updated = pyqtSignal(int)
    update_min_max = pyqtSignal(float, float)

    def __init__(self, node_data, element_data, node_weights, variables, parent=None):
        super(GLWidget, self).__init__(parent)
        self.node_data = node_data
        self.element_data = element_data
        self.node_weights = node_weights


        self.variables = variables  # List of variable names
        self.current_variable = variables[0]  # Default variable
        self.is_playing = True
        self.show_labels = False  # Control label display

        # Initialize camera and controls
        self.camera_pos = [57.58, 5.00, 4.71]
        # self.camera_speed = 0.5
        self.distance = 25.0  # Distance from target
        self.rotation_x = 20.0  # Initial x rotation angle
        self.rotation_y = 20.0  # Initial y rotation angle
        self.zoom_speed = 0.1
        self.rotation_damping = 0.1  # Damping for smooth rotation
        self.zoom_damping = 0.9  # Damping for smooth zoom
        
        self.keys_pressed = set()
        self.last_pos = None
        self.click_start_pos = None
        self.mouse_moved = False

        # Timer for updating animation
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(60)
        self.current_time = 0
        self.animation_duration = 3000

        # Calculate number of keyframes
        # Assuming all variables have the same number of keyframes
        first_node = next(iter(node_weights.keys()))
        first_variable = self.current_variable
        self.num_keyframes = len(node_weights[first_node][first_variable])

        # Initialize min and max weights
        self.calculate_min_max_weights()

        # Initialize previous min and max weights
        self.previous_min_weight = None
        self.previous_max_weight = None

        # Timer for camera movement
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.update_position)
        # self.timer.start(16)
        # self.setFocusPolicy(Qt.StrongFocus)
        # self.setFocus()
        self.picking = False  # Flag to indicate picking mode

        self.node_id_to_color = {}
        self.color_to_node_id = {}

    def calculate_min_max_weights(self):
        # Recalculate min and max weights for the current variable
        weights = []
        for node_idx in self.node_weights:
            weights.extend(self.node_weights[node_idx][self.current_variable])
        self.min_weight = min(weights)
        self.max_weight = max(weights)

    def set_current_variable(self, variable_name):
        self.current_variable = variable_name
        self.calculate_min_max_weights()
        self.previous_min_weight = None  # Reset to force gradient bar update
        self.previous_max_weight = None
        self.update()  # Redraw the scene

    def initializeGL(self):
        self.makeCurrent()
        glClearColor(0.1, 0.1, 0.1, 1.0)  # Darker background
        
        # Enable key features for better rendering
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_MULTISAMPLE)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)
        
        
        # Material properties
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)
        
        # Smooth shading
        glShadeModel(GL_SMOOTH)


    def resizeGL(self, width, height):
        self.makeCurrent()  # Ensure context is current
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width / height if height != 0 else 1, 1, 1000.0)  # Adjusted near clipping plane
        glMatrixMode(GL_MODELVIEW)

    def render_scene(self):
        # Draw surfaces first
        for element in self.element_data:
            if len(element) == 4:
                node_positions = [self.node_data[node] for node in element]
                node_indices = element
                self.draw_surface(node_positions, node_indices)

        # Draw lines on top
        for element in self.element_data:
            if len(element) == 2:
                node_positions = [self.node_data[node] for node in element]
                node_indices = element
                self.draw_line(node_positions, node_indices)

        # Draw small white spheres at each node position
        for node_idx, pos in self.node_data.items():
            glPushMatrix()
            glTranslatef(*pos)
            glColor3f(1.0, 1.0, 1.0)  # Set color to white
            glutSolidSphere(0.1, 10, 10)  # Adjust radius and segments for size and detail
            glPopMatrix()

        # Draw node labels with weights in 3D space if enabled
        if self.show_labels:
            for node_idx, pos in self.node_data.items():
                # Get the current weight for this node
                weight = self.current_node_weights.get(node_idx, 0.0)

                # Create label text with the node index and weight in exponential notation
                label_text = f"{weight:.2e}"  # Exponential notation

                # Set color to bright yellow for maximum contrast
                glColor3f(1.0, 1.0, 0.0)

                # Set the raster position for the label at the node position
                glRasterPos3f(*pos)

                # Render each character of the label with a larger font
                for ch in label_text:
                    glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(ch))  # Larger font size

    def render_for_picking(self):
        # Disable lighting and textures for picking
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)

        # Assign a unique color to each node
        self.node_id_to_color.clear()
        self.color_to_node_id.clear()
        for idx, node_idx in enumerate(self.node_data.keys()):
            color_id = idx + 1  # Avoid using color_id=0
            r = (color_id & 0xFF0000) >> 16
            g = (color_id & 0x00FF00) >> 8
            b = (color_id & 0x0000FF)

            self.node_id_to_color[node_idx] = (r, g, b)
            self.color_to_node_id[(r, g, b)] = node_idx

        # Draw pickable nodes with unique colors
        for node_idx, pos in self.node_data.items():
            r, g, b = self.node_id_to_color[node_idx]
            glColor3ub(r, g, b)

            # Draw a small quad at the node position
            glPushMatrix()
            glTranslatef(*pos)
            glBegin(GL_QUADS)
            size = 1  # Adjust size as needed
            glVertex3f(-size, -size, 0)
            glVertex3f(size, -size, 0)
            glVertex3f(size, size, 0)
            glVertex3f(-size, size, 0)
            glEnd()
            glPopMatrix()

        # Re-enable lighting and textures
        # glEnable(GL_LIGHTING)
        # glEnable(GL_TEXTURE_2D)

    def get_color(self, value):
        # Map the normalized value to a color gradient from blue to red
        t = value  # direct normalized mapping, could add custom easing here
        if t < 0.25:
            r, g, b = 0.0, 4 * t, 1.0  # Blue to cyan
        elif t < 0.5:
            r, g, b = 0.0, 1.0, 1 - (4 * (t - 0.25))  # Cyan to green
        elif t < 0.75:
            r, g, b = 4 * (t - 0.5), 1.0, 0.0  # Green to yellow
        else:
            r, g, b = 1.0, 1 - (4 * (t - 0.75)), 0.0  # Yellow to red
        return (r, g, b)

    def paintGL(self):
        self.makeCurrent()  # Ensure context is current
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        # Render background gradient
        glPushMatrix()
        glDisable(GL_DEPTH_TEST)  # Disable depth test to ensure background is at the back
        glBegin(GL_QUADS)

        # Top - Light Blue
        glColor3f(0.5, 0.7, 1.0)
        glVertex3f(-1.0, 1.0, -1.0)
        glVertex3f(1.0, 1.0, -1.0)

        # Bottom - Darker Blue
        glColor3f(0.0, 0.0, 0.5)
        glVertex3f(1.0, -1.0, -1.0)
        glVertex3f(-1.0, -1.0, -1.0)
        glEnd()
        glPopMatrix()

        camera_x = self.camera_pos[0] + self.distance * math.cos(math.radians(self.rotation_y)) * math.cos(math.radians(self.rotation_x))
        camera_y = self.camera_pos[1] + self.distance * math.sin(math.radians(self.rotation_x))
        camera_z = self.camera_pos[2] + self.distance * math.sin(math.radians(self.rotation_y)) * math.cos(math.radians(self.rotation_x))
        gluLookAt(
            camera_x, camera_y, camera_z,
            self.camera_pos[0], self.camera_pos[1], self.camera_pos[2],
            0.0, 1.0, 0.0
        )

        # Reset the view matrix
        glPushMatrix()
        # Calculate weights for the current frame per node
        keyframe_duration = self.animation_duration / (self.num_keyframes - 1)
        current_keyframe = int((self.current_time % self.animation_duration) / keyframe_duration)
        next_keyframe = (current_keyframe + 1) % self.num_keyframes
        keyframe_time = ((self.current_time % self.animation_duration) % keyframe_duration) / keyframe_duration

        self.current_node_weights = {}
        for node_idx in self.node_weights:
            weights = self.node_weights[node_idx][self.current_variable]
            weight = (1 - keyframe_time) * weights[current_keyframe] + keyframe_time * weights[next_keyframe]
            self.current_node_weights[node_idx] = weight

        # Compute current min and max weights
        current_min_weight = min(self.current_node_weights.values())
        current_max_weight = max(self.current_node_weights.values())

        # Check if the min or max weight has changed
        if (current_min_weight != self.previous_min_weight) or (current_max_weight != self.previous_max_weight):
            self.update_min_max.emit(current_min_weight, current_max_weight)
            self.previous_min_weight = current_min_weight
            self.previous_max_weight = current_max_weight

        if self.picking:
            # Render scene for picking
            self.render_for_picking()
        else:
            # Normal rendering
            self.render_scene()

        glPopMatrix()

        self.display_coordinates()
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1.0, 1.0)

    def display_coordinates(self):
        glPushMatrix()
        glLoadIdentity()
        
        # Set the position for displaying text
        glColor3f(1.0, 1.0, 1.0)  # Set text color to white
        glRasterPos3f(-1.0, 0.9, -1.0)  # Adjust position to top-left corner

        # Display the camera position


        glPopMatrix()
    
    def play_animation(self):
        self.is_playing = True
        self.animation_timer.start(60)

    def stop_animation(self):
        self.is_playing = False
        self.animation_timer.stop()

    def step_forward(self):
        if not self.is_playing:
            self.current_time += self.animation_duration / self.num_keyframes
            if self.current_time >= self.animation_duration:
                self.current_time = 0
            self.update()

    def step_backward(self):
        if not self.is_playing:
            self.current_time -= self.animation_duration / self.num_keyframes
            if self.current_time < 0:
                self.current_time = self.animation_duration - (self.animation_duration / self.num_keyframes)
            self.update()

    def update_animation(self):
        if self.is_playing:
            self.current_time += 30
            if self.current_time >= self.animation_duration:
                self.current_time = 0  # Loop animation
        self.update()
        current_frame = int((self.current_time % self.animation_duration) / (self.animation_duration / self.num_keyframes))
        self.animation_updated.emit(current_frame)

    def draw_line(self, positions, node_indices):
        glLineWidth(2.0)
        glBegin(GL_LINES)
        for pos, node_idx in zip(positions, node_indices):
            weight = self.current_node_weights[node_idx]
            if self.max_weight - self.min_weight != 0:
                normalized_weight = (weight - self.min_weight) / (self.max_weight - self.min_weight)
            else:
                normalized_weight = 0.0
            r, g, b = self.get_color(normalized_weight)
            glColor4f(r, g, b, 0.8)
            glVertex3f(*pos)
        glEnd()

    def draw_surface(self, positions, node_indices):
        glEnable(GL_POLYGON_OFFSET_FILL)
        glBegin(GL_QUADS)
        for pos, node_idx in zip(positions, node_indices):
            weight = self.current_node_weights[node_idx]
            if self.max_weight - self.min_weight != 0:
                normalized_weight = (weight - self.min_weight) / (self.max_weight - self.min_weight)
            else:
                normalized_weight = 1.0
            r, g, b = self.get_color(normalized_weight)
            glColor4f(r, g, b, 0.7)  # Add transparency
            glVertex3f(*pos)
        glEnd()
        # Draw edges
        glLineWidth(1.0)
        glColor4f(0.2, 0.2, 0.2, 1.0)  # Dark edges
        glBegin(GL_LINE_LOOP)
        for pos in positions:
            glVertex3f(*pos)
        glEnd()
        
        glDisable(GL_BLEND)

    def mousePressEvent(self, event):
        self.click_start_pos = event.pos()
        self.last_pos = event.pos()
        self.mouse_moved = False

    # Mouse move event to update rotation with smoothing
    def mouseMoveEvent(self, event):
        if self.last_pos:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()

            # Apply a damping factor to smooth rotation
            damping_factor = 0.1
            self.rotation_x += dy * damping_factor
            self.rotation_y += dx * damping_factor

            # Redraw the scene only after minor adjustments
            if abs(dx) > 1 or abs(dy) > 1:
                self.update()
            self.last_pos = event.pos()

            # If mouse moved significantly, set mouse_moved to True
            if abs(event.x() - self.click_start_pos.x()) > 5 or abs(event.y() - self.click_start_pos.y()) > 5:
                self.mouse_moved = True

    def mouseReleaseEvent(self, event):
        if self.last_pos:
            dx = event.x() - self.click_start_pos.x()
            dy = event.y() - self.click_start_pos.y()
            distance = (dx*dx + dy*dy) ** 0.5
            if distance < 10:  # Threshold to consider it a click
                # It's a click, perform picking
                self.perform_picking(event.x(), event.y())
            else:
                print("Mouse moved, not a click")
        self.last_pos = None
        self.mouse_moved = False

    def perform_picking(self, x, y):
        self.picking = True
        self.makeCurrent()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Set up the same view as normal rendering
        glPushMatrix()
        glRotatef(self.rotation_x, 1.0, 0.0, 0.0)
        glRotatef(self.rotation_y, 0.0, 1.0, 0.0)
        glTranslatef(-self.camera_pos[0], -self.camera_pos[1], -self.camera_pos[2])

        # Render for picking
        self.render_for_picking()
        glPopMatrix()
        glFlush()
        glFinish()

        # Read the pixel color at the mouse position
        viewport = glGetIntegerv(GL_VIEWPORT)
        x = int(x)
        y = int(y)
        # Read the pixel data into a numpy array
        pixel = glReadPixels(x, viewport[3] - y, 1, 1, GL_RGB, GL_UNSIGNED_BYTE)
        pixel = np.frombuffer(pixel, dtype=np.uint8)

        if pixel.size >= 3:
            r, g, b = pixel[0], pixel[1], pixel[2]
        else:
            print('Failed to read pixel data')
            return

        # Map color back to node_idx
        node_idx = self.color_to_node_id.get((r, g, b))
        if node_idx is not None:
            # Node was clicked
            print(f"Node {node_idx} was clicked via picking")
            self.node_clicked(node_idx)
        else:
            print("No node was clicked via picking")

        self.picking = False
        self.update()  # Redraw the scene normally

    def node_clicked(self, node_idx):
        try:
            print(f"Node {node_idx} clicked")
            # Get weights for all variables
            weights_dict = self.node_weights[node_idx]
            self.plot_window = PlotWindow(node_idx, weights_dict, self.variables)
            self.plot_window.show()
        except Exception as e:
            print(f"Error displaying plot window: {e}")

    # def keyPressEvent(self, event):
    #     self.keys_pressed.add(event.key())
    #     self.update_position()  # Immediate position update on key press

    # def keyReleaseEvent(self, event):
    #     self.keys_pressed.discard(event.key())

    # def update_position(self):
    #     if Qt.Key_W in self.keys_pressed:
    #         self.camera_pos[0] += self.camera_speed * math.sin(math.radians(self.rotation_y))
    #         self.camera_pos[2] -= self.camera_speed * math.cos(math.radians(self.rotation_y))
    #     if Qt.Key_S in self.keys_pressed:
    #         self.camera_pos[0] -= self.camera_speed * math.sin(math.radians(self.rotation_y))
    #         self.camera_pos[2] += self.camera_speed * math.cos(math.radians(self.rotation_y))

    #     if Qt.Key_A in self.keys_pressed:
    #         self.camera_pos[0] -= self.camera_speed * math.cos(math.radians(self.rotation_y))
    #         self.camera_pos[2] -= self.camera_speed * math.sin(math.radians(self.rotation_y))
    #     if Qt.Key_D in self.keys_pressed:
    #         self.camera_pos[0] += self.camera_speed * math.cos(math.radians(self.rotation_y))
    #         self.camera_pos[2] += self.camera_speed * math.sin(math.radians(self.rotation_y))

    #     if Qt.Key_Q in self.keys_pressed:
    #         self.camera_pos[1] -= self.camera_speed
    #     if Qt.Key_E in self.keys_pressed:
    #         self.camera_pos[1] += self.camera_speed

    #     self.update()  # Redraw the scene
    def wheelEvent(self, event):
        # Get the scroll delta
        delta = event.angleDelta().y() / 120.0
        
        # Adjust zoom speed and limits
        zoom_speed = 0.1  # Smaller value for finer control
        min_distance = 1.0  # Minimum zoom (closest)
        max_distance = 200.0  # Increase this value to allow more zoom out
        
        # Update distance with damping
        self.distance *= 1.0 - (delta * zoom_speed)
        
        # Clamp distance between min and max values
        self.distance = max(min_distance, min(max_distance, self.distance))
        
        # Request update
        self.update()
# Updated PlotWindow class to handle multiple variables
class PlotWindow(QWidget):
    def __init__(self, node_idx, weights_dict, variables, parent=None):
        super(PlotWindow, self).__init__(parent)
        self.setWindowTitle(f'Readings for Node {node_idx}')
        self.resize(400, 300)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.plot(weights_dict, variables)

    def plot(self, weights_dict, variables):
        ax = self.figure.add_subplot(111)
        for var in variables:
            weights = weights_dict[var]
            timesteps = list(range(1, len(weights)+1))
            ax.plot(timesteps, weights, marker='o', label=var)
        ax.set_title('Readings vs Timestep')
        ax.set_xlabel('Timestep')
        ax.set_ylabel('Reading')
        ax.legend()
        self.canvas.draw()

# GradientBarWidget class remains the same
class GradientBarWidget(QWidget):
    def __init__(self, parent=None, min_value=0.0, max_value=1.0):
        super(GradientBarWidget, self).__init__(parent)
        self.min_value = min_value
        self.max_value = max_value

    def update_range(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value
        self.update()  # Refresh the widget

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        # Create a vertical gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())

        # Match the color stops with GLWidget's get_color method
        gradient.setColorAt(0.0, QColor(0, 0, 255))      # Blue
        gradient.setColorAt(0.25, QColor(0, 255, 255))   # Cyan
        gradient.setColorAt(0.5, QColor(0, 255, 0))      # Green
        gradient.setColorAt(0.75, QColor(255, 255, 0))   # Yellow
        gradient.setColorAt(1.0, QColor(255, 0, 0))      # Red

        painter.fillRect(rect, gradient)

        # Determine display format for min and max values
        min_display = f"{self.min_value:.2e}" if abs(self.min_value) < 1e-2 else f"{self.min_value:.2f}"
        max_display = f"{self.max_value:.2e}" if abs(self.max_value) < 1e-2 else f"{self.max_value:.2f}"

        # Draw min and max values in the gradient bar
        painter.setPen(Qt.black)
        painter.drawText(rect.left() + 5, rect.top() + 15, max_display)
        painter.drawText(rect.left() + 5, rect.bottom() - 5, min_display)

from PyQt5.QtWidgets import QSlider, QLabel

from PyQt5.QtWidgets import QHBoxLayout


class MainWindow(QMainWindow):
    def __init__(self, node_data, element_data, node_weights, variables):
        super(MainWindow, self).__init__()
        self.setWindowTitle('3D Model - Animation Controls')
        self.setGeometry(100, 100, 1200, 800)

        # Central widget with horizontal layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side (OpenGL widget and timeline slider)
        left_layout = QVBoxLayout()

        # OpenGL widget
        self.glWidget = GLWidget(node_data, element_data, node_weights, variables, self)
        left_layout.addWidget(self.glWidget)

        # Timeline controls at the bottom
        self.timeline_layout = QHBoxLayout()

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self.glWidget.num_keyframes - 1)
        self.slider.setValue(0)
        self.slider.setSingleStep(1)
        self.slider.setTickInterval(1)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.valueChanged.connect(self.slider_changed)
        self.slider.setFixedHeight(25)  # Reduce slider height

        self.frame_label = QLabel("Frame: 0/0")
        self.update_frame_label(0)
        self.frame_label.setFixedHeight(25)  # Match label height to slider

        timeline_container = QWidget()  # Create a container for the timeline layout
        timeline_container.setLayout(self.timeline_layout)
        timeline_container.setFixedHeight(50)  # Set total height for the timeline section

        self.timeline_layout.addWidget(QLabel("Timeline:"))
        self.timeline_layout.addWidget(self.slider)
        self.timeline_layout.addWidget(self.frame_label)

        # Add the timeline container to the left layout
        left_layout.addWidget(timeline_container)


        main_layout.addLayout(left_layout)

        # Right side (Gradient bar)
        self.gradientBar = GradientBarWidget(self, min_value=self.glWidget.min_weight, max_value=self.glWidget.max_weight)
        self.gradientBar.setFixedWidth(100)
        main_layout.addWidget(self.gradientBar)

        # Toolbar with playback controls
        toolbar = QToolBar("Playback Controls")
        self.addToolBar(Qt.BottomToolBarArea, toolbar)

        play_action = QAction("Play", self)
        play_action.triggered.connect(self.glWidget.play_animation)
        toolbar.addAction(play_action)

        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.glWidget.stop_animation)
        toolbar.addAction(stop_action)

        # Checkbox to enable/disable labels
        self.label_checkbox = QCheckBox("Show Labels")
        self.label_checkbox.setChecked(False)  # Labels are shown by default
        self.label_checkbox.stateChanged.connect(self.toggle_labels)
        toolbar.addWidget(self.label_checkbox)

        # Dropdown to select variable
        self.variable_dropdown = QComboBox()
        self.variable_dropdown.addItems(variables)
        self.variable_dropdown.currentTextChanged.connect(self.change_variable)
        toolbar.addWidget(self.variable_dropdown)

        # Connect GLWidget's signal to gradient bar's update_range method
        self.glWidget.update_min_max.connect(self.gradientBar.update_range)

        # Synchronize GLWidget and slider
        self.glWidget.animation_updated.connect(self.sync_slider)

    def slider_changed(self, value):
        self.glWidget.current_time = value * (self.glWidget.animation_duration / self.glWidget.num_keyframes)
        self.glWidget.update()
        self.update_frame_label(value)

    def sync_slider(self, current_frame):
        self.slider.blockSignals(True)
        self.slider.setValue(current_frame)
        self.slider.blockSignals(False)
        self.update_frame_label(current_frame)

    def update_frame_label(self, frame):
        self.frame_label.setText(f"Frame: {frame}/{self.glWidget.num_keyframes - 1}")

    def toggle_labels(self, state):
        self.glWidget.show_labels = (state == Qt.Checked)
        self.glWidget.update()  # Redraw the OpenGL widget

    def change_variable(self, variable_name):
        self.glWidget.set_current_variable(variable_name)
        self.gradientBar.update_range(self.glWidget.min_weight, self.glWidget.max_weight)
        self.gradientBar.update()



import csv

def read_node_edge_csv(filename):
    node_data = {}
    element_data = []

    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            # Load node data
            if row.get('NODE_number'):
                node_num = int(row['NODE_number'])
                x = float(row['x'].replace(',', '.')) if row['x'] else None
                y = float(row['y'].replace(',', '.')) if row['y'] else None
                z = float(row['z'].replace(',', '.')) if row['z'] else None
                if x is not None and y is not None and z is not None:
                    node_data[node_num] = (x, y, z)

            # Load element data
            element = []
            if row.get('Element1'):
                element.append(int(row['Element1']))
            if row.get('Element2'):
                element.append(int(row['Element2']))
            if row.get('Element3'):
                element.append(int(row['Element3']))
            if row.get('Element4'):
                element.append(int(row['Element4']))
            if len(element) >= 2:
                element_data.append(element)
    
    return node_data, element_data

import csv

def read_heatmap_csv(filename):
    node_weights = {}
    base_variables = set()  # Use a set to collect unique base variable names

    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')

        # Strip any BOM from the field names
        reader.fieldnames = [field.lstrip('\ufeff') for field in reader.fieldnames]

        # Extract unique base variable names from the header
        for field in reader.fieldnames[1:]:  # Skip 'NODES_1' column
            base_var = field.split('_')[0]  # Remove timestep suffix (e.g., 'U1' from 'U1_1')
            base_variables.add(base_var)

        base_variables = sorted(base_variables)  # Convert set to sorted list for consistent ordering

        for row in reader:
            # Parse the node number
            node_num = int(row['NODES_1'])
            node_weights[node_num] = {base_var: [] for base_var in base_variables}  # Initialize lists for each base variable

            # Populate each base variable with its timestep values
            for field, value in row.items():
                if field == 'NODES_1':
                    continue

                base_var = field.split('_')[0]  # Get the base variable name
                try:
                    # Convert string to float, replacing commas with dots for consistency
                    value_float = float(value.replace(',', '.'))
                    node_weights[node_num][base_var].append(value_float)  # Append timestep value to base variable
                except ValueError:
                    print(f"Skipping invalid value '{value}' in row for node {node_num}")

    return node_weights, base_variables  # Return unique base variables list

if __name__ == '__main__':
    # Load nodes and edges from original file
    node_data, element_data = read_node_edge_csv("nodes_animated.csv")
    
    # Load heatmap data from new CSV file
    node_weights, variables = read_heatmap_csv("heatmap.csv")

    app = QApplication(sys.argv) 
    print(variables, node_weights)
    window = MainWindow(node_data, element_data, node_weights, variables)
    print(variables)
    window.show()
    sys.exit(app.exec_())