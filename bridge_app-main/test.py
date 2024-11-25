import sys
import csv
import math
import numpy as np  # Add numpy import
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget, QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QLinearGradient, QColor
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtGui import QFont
from OpenGL.GLUT import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class GLWidget(QOpenGLWidget):
    def __init__(self, node_data, element_data, node_weights, parent=None):
        super(GLWidget, self).__init__(parent)
        self.node_data = node_data
        self.element_data = element_data
        self.node_weights = node_weights

        # Initialize camera and controls
        self.camera_pos = [0.0, 5.0, 20.0]
        self.camera_speed = 0.5
        self.rotation_x = 0.0
        self.rotation_y = 0.0
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
        self.num_keyframes = len(next(iter(node_weights.values())))
        self.min_weight = min(min(weights) for weights in node_weights.values())
        self.max_weight = max(max(weights) for weights in node_weights.values())

        # Timer for camera movement
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # Variables for color picking
        self.picking = False  # Flag to indicate picking mode
        self.node_id_to_color = {}
        self.color_to_node_id = {}

    def initializeGL(self):
        self.makeCurrent()  # Ensure context is current
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_MULTISAMPLE)  # Enable multisampling for smoother edges

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        light_position = [0.0, 10.0, 10.0, 1.0]
        glLightfv(GL_LIGHT0, GL_POSITION, light_position)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)  # Enable two-sided lighting
        glShadeModel(GL_SMOOTH)  # Smooth shading mode to blend lighting
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)

    def resizeGL(self, width, height):
        self.makeCurrent()  # Ensure context is current
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width / height if height != 0 else 1, 1, 1000.0)  # Adjusted near clipping plane
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        self.makeCurrent()  # Ensure context is current
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Reset the view matrix
        glPushMatrix()
        glRotatef(self.rotation_x, 1.0, 0.0, 0.0)
        glRotatef(self.rotation_y, 0.0, 1.0, 0.0)
        glTranslatef(-self.camera_pos[0], -self.camera_pos[1], -self.camera_pos[2])

        # Calculate weights for the current frame per node
        keyframe_duration = self.animation_duration / (self.num_keyframes - 1)
        current_keyframe = int((self.current_time % self.animation_duration) / keyframe_duration)
        next_keyframe = (current_keyframe + 1) % self.num_keyframes
        keyframe_time = ((self.current_time % self.animation_duration) % keyframe_duration) / keyframe_duration

        self.current_node_weights = {}
        for node_idx, weights in self.node_weights.items():
            weight = (1 - keyframe_time) * weights[current_keyframe] + keyframe_time * weights[next_keyframe]
            self.current_node_weights[node_idx] = weight

        if self.picking:
            # Render scene for picking
            self.render_for_picking()
        else:
            # Normal rendering
            self.render_scene()

        glPopMatrix()

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

        # Draw node labels with weights in 3D space
        for node_idx, pos in self.node_data.items():
            # Get the current weight for this node
            weight = self.current_node_weights.get(node_idx, 0.0)

            # Create label text with the node index and weight in exponential notation
            label_text = f"{weight:.2e}"  # Exponential notation

            # Set color to bright white for maximum contrast
            glColor3f(1.0, 1.0, 1.0)

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
            size = 0.5  # Adjust size as needed
            glVertex3f(-size, -size, 0)
            glVertex3f(size, -size, 0)
            glVertex3f(size, size, 0)
            glVertex3f(-size, size, 0)
            glEnd()
            glPopMatrix()

        # Re-enable lighting and textures
        glEnable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)

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

    def draw_line(self, positions, node_indices):
        glLineWidth(5.0)
        glBegin(GL_LINES)
        for pos, node_idx in zip(positions, node_indices):
            weight = self.current_node_weights[node_idx]
            if self.max_weight - self.min_weight != 0:
                normalized_weight = (weight - self.min_weight) / (self.max_weight - self.min_weight)
            else:
                normalized_weight = 0.0
            r, g, b = self.get_color(normalized_weight)
            glColor3f(r, g, b)
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
            glColor3f(r, g, b)
            glVertex3f(*pos)
        glEnd()

    def update_animation(self):
        self.current_time += 30
        self.update()

    def mousePressEvent(self, event):
        self.click_start_pos = event.pos()
        self.last_pos = event.pos()
        self.mouse_moved = False

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
            if distance < 5:  # Threshold to consider it a click
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
            weights = self.node_weights[node_idx]
            self.plot_window = PlotWindow(node_idx, weights)
            self.plot_window.show()
        except Exception as e:
            print(f"Error displaying plot window: {e}")

    def keyPressEvent(self, event):
        self.keys_pressed.add(event.key())
        self.update_position()  # Immediate position update on key press

    def keyReleaseEvent(self, event):
        self.keys_pressed.discard(event.key())

    def update_position(self):
        if Qt.Key_W in self.keys_pressed:
            self.camera_pos[0] += self.camera_speed * math.sin(math.radians(self.rotation_y))
            self.camera_pos[2] -= self.camera_speed * math.cos(math.radians(self.rotation_y))
        if Qt.Key_S in self.keys_pressed:
            self.camera_pos[0] -= self.camera_speed * math.sin(math.radians(self.rotation_y))
            self.camera_pos[2] += self.camera_speed * math.cos(math.radians(self.rotation_y))

        if Qt.Key_A in self.keys_pressed:
            self.camera_pos[0] -= self.camera_speed * math.cos(math.radians(self.rotation_y))
            self.camera_pos[2] -= self.camera_speed * math.sin(math.radians(self.rotation_y))
        if Qt.Key_D in self.keys_pressed:
            self.camera_pos[0] += self.camera_speed * math.cos(math.radians(self.rotation_y))
            self.camera_pos[2] += self.camera_speed * math.sin(math.radians(self.rotation_y))

        if Qt.Key_Q in self.keys_pressed:
            self.camera_pos[1] -= self.camera_speed
        if Qt.Key_E in self.keys_pressed:
            self.camera_pos[1] += self.camera_speed

        self.update()  # Redraw the scene

# PlotWindow class remains the same
class PlotWindow(QWidget):
    def __init__(self, node_idx, weights, parent=None):
        super(PlotWindow, self).__init__(parent)
        self.setWindowTitle(f'Readings for Node {node_idx}')
        self.resize(400, 300)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.plot(weights)

    def plot(self, weights):
        ax = self.figure.add_subplot(111)
        timesteps = list(range(1, len(weights)+1))
        ax.plot(timesteps, weights, marker='o')
        ax.set_title('Readings vs Timestep')
        ax.set_xlabel('Timestep')
        ax.set_ylabel('Reading')
        self.canvas.draw()

# GradientBarWidget class remains the same
class GradientBarWidget(QWidget):
    def __init__(self, parent=None, min_value=0.0, max_value=1.0):
        super(GradientBarWidget, self).__init__(parent)
        self.min_value = min_value
        self.max_value = max_value

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

        # Draw min and max values
        painter.setPen(Qt.black)
        painter.drawText(rect.left() + 5, rect.top() + 15, f"{self.max_value:.2f}")
        painter.drawText(rect.left() + 5, rect.bottom() - 5, f"{self.min_value:.2f}")

# MainWindow class remains the same
class MainWindow(QMainWindow):
    def __init__(self, node_data, element_data, node_weights):
        super(MainWindow, self).__init__()
        self.setWindowTitle('3D Model - Nodes and Elements with WASD Controls')
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.glWidget = GLWidget(node_data, element_data, node_weights, self)
        layout.addWidget(self.glWidget)

        # Create GradientBarWidget
        self.gradientBar = GradientBarWidget(self, min_value=self.glWidget.min_weight, max_value=self.glWidget.max_weight)
        self.gradientBar.setFixedWidth(50)  # Adjust the width as needed
        layout.addWidget(self.gradientBar)

def read_csv(filename):
    node_data = {}
    node_weights = {}
    element_data = []

    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        rows = list(reader)

    # First, read node data
    for row in rows:
        try:
            if row.get('NODE_number'):
                node_num = int(row['NODE_number'])
                x = float(row['x'].replace(',', '.')) if row['x'] else None
                y = float(row['y'].replace(',', '.')) if row['y'] else None
                z = float(row['z'].replace(',', '.')) if row['z'] else None
                if x is not None and y is not None and z is not None:
                    node_data[node_num] = (x, y, z)
                # Read weights per node
                u_weight = []
                for i in range(1, 100):  # Assuming up to 100 timesteps
                    key = f'U2_{i}'
                    if key in row and row[key]:
                        u_weight.append(float(row[key].replace(',', '.')))
                    else:
                        break  # Stop if no more weights
                node_weights[node_num] = u_weight
        except KeyError as e:
            print(f"Error: Missing column {e}")
        except ValueError as e:
            print(f"Error: Invalid data format {e}")

    # Then, read element data
    for row in rows:
        try:
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
        except KeyError as e:
            print(f"Error: Missing column {e}")
        except ValueError as e:
            print(f"Error: Invalid data format {e}")

    return node_data, element_data, node_weights

if __name__ == '__main__':
    node_data, element_data, node_weights = read_csv("nodes_animated.csv")
    app = QApplication(sys.argv)
    window = MainWindow(node_data, element_data, node_weights)
    window.show()
    sys.exit(app.exec_())
