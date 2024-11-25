import sys
import csv
import math
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PyQt5.QtWidgets import QMessageBox

# OpenGL Widget for rendering 3D elements with WASD controls and mouse rotation
class GLWidget(QOpenGLWidget):
    positionChanged = pyqtSignal(float, float, float)  # Signal to emit camera position

    def __init__(self, node_data, element_data, node_weights, parent=None):
        super(GLWidget, self).__init__(parent)
        self.node_data = node_data  # Dictionary with node number and positions
        self.element_data = element_data  # List with element connections
        self.node_weights = node_weights  # Dictionary with weight data per node
        # Define spheres with their positions and colors
        self.spheres = [
            {"color": (1.0, 0.0, 0.0), "position": [0, 0, 4.6], "label": "Accelerometer", "radius": 1.0},
            {"color": (0.0, 0.0, 1.0), "position": [46, 21, 6], "label": "Strain Gauge", "radius": 1.0},
            {"color": (0.0, 1.0, 0.0), "position": [70, 21, 6], "label": "Displacement Sensor", "radius": 1.0},
            {"color": (1.0, 1.0, 0.0), "position": [114, 0, 6], "label": "Camera", "radius": 1.0}
        ]

        # Camera control variables
        self.camera_pos = [0.0, 5.0, 20.0]
        self.camera_speed = 0.5
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.keys_pressed = set()
        self.last_pos = None

        # Timer for updating animation
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(60)  # ~16ms per frame
        self.current_time = 0  # Track time in milliseconds
        self.animation_duration = 3000  # 3 seconds

        # Number of keyframes based on weights
        self.num_keyframes = len(next(iter(node_weights.values())))  # Number of weight steps
        all_weights = [weight for weights in self.node_weights.values() for weight in weights]
        self.min_weight = min(all_weights) or 0.0
        self.max_weight = max(all_weights) or 1.0

        # Timer for camera movement
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)  # ~60 FPS

        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # Emit initial camera position
        self.positionChanged.emit(self.camera_pos[0], self.camera_pos[1], self.camera_pos[2])

    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_MULTISAMPLE)  # Enable multisampling for smoother edges

        glEnable(GL_DEPTH_TEST)  # Enable depth testing
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
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width / height if height != 0 else 1, 1, 1000.0)  # Adjusted near clipping plane
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()  # Reset transformations
        glPushMatrix()

        # Apply rotation and translation for camera movement
        glRotatef(self.rotation_x, 1.0, 0.0, 0.0)
        glRotatef(self.rotation_y, 0.0, 1.0, 0.0)
        glTranslatef(-self.camera_pos[0], -self.camera_pos[1], -self.camera_pos[2])

        # Now get the matrices
        self.modelview_matrix = glGetDoublev(GL_MODELVIEW_MATRIX)
        self.projection_matrix = glGetDoublev(GL_PROJECTION_MATRIX)
        self.viewport = glGetIntegerv(GL_VIEWPORT)

        # Draw elements and spheres
        for element in self.element_data:
            if len(element) == 4:
                node_positions = [self.node_data[node] for node in element]
                self.draw_surface(node_positions, element)
            elif len(element) == 2:
                node_positions = [self.node_data[node] for node in element]
                self.draw_line(node_positions, element)

        # Draw spheres
        for sphere in self.spheres:
            self.draw_sphere(sphere["position"], sphere["color"], sphere["radius"])

        glPopMatrix()

    def draw_sphere(self, position, color, radius):
        glPushMatrix()
        glTranslatef(*position)
        glColor3f(*color)
        glutSolidSphere(radius, 20, 20)  # Use the radius from sphere data
        glPopMatrix()


    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        x = event.x()
        y = event.y()
        adjusted_y = self.height() - y  # Convert to OpenGL coordinates

        self.makeCurrent()  # Ensure OpenGL context is current

        modelview = self.modelview_matrix
        projection = self.projection_matrix
        viewport = self.viewport

        # Get the near and far points in world coordinates
        near = gluUnProject(x, adjusted_y, 0.0, modelview, projection, viewport)
        far = gluUnProject(x, adjusted_y, 1.0, modelview, projection, viewport)

        ray_origin = np.array(near)
        ray_direction = np.array(far) - np.array(near)
        ray_direction = ray_direction / np.linalg.norm(ray_direction)  # Normalize

        for sphere in self.spheres:
            sphere_center = np.array(sphere["position"])
            sphere_radius = sphere["radius"]  # Use the sphere's actual radius

            pick_tolerance = 0.5  # Adjust this value to increase tolerance
            pick_radius = sphere_radius + pick_tolerance

            # Ray-sphere intersection test
            oc = ray_origin - sphere_center
            a = np.dot(ray_direction, ray_direction)
            b = 2.0 * np.dot(oc, ray_direction)
            c = np.dot(oc, oc) - pick_radius ** 2
            discriminant = b ** 2 - 4 * a * c

            if discriminant >= 0:
                # The ray intersects the sphere
                self.show_popover(sphere["label"])
                break  # Stop after first hit


    def show_popover(self, label):
        msg = QMessageBox()
        msg.setWindowTitle("Sensor Information")
        msg.setText(f"{label} data:\nDummy Value: 123")
        msg.exec_()

    def draw_line(self, positions, node_indices):
        glLineWidth(5.0)
        glBegin(GL_LINES)
        # Set a fixed color for lines (e.g., white)
        glColor3f(1.0, 1.0, 1.0)
        for pos in positions:
            glVertex3f(*pos)
        glEnd()

    def draw_surface(self, positions, node_indices):
        glEnable(GL_POLYGON_OFFSET_FILL)
        glBegin(GL_QUADS)
        # Set a fixed color for surfaces (e.g., blue)
        glColor3f(0.0, 0.0, 1.0)
        for pos in positions:
            glVertex3f(*pos)
        glEnd()

    def update_animation(self):
        self.current_time += 30
        self.update()

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

    def mouseReleaseEvent(self, event):
        self.last_pos = None

    def keyPressEvent(self, event):
        # print(f"Key pressed: {event.key()}")  # Debug statement
        self.keys_pressed.add(event.key())
        self.update_position()  # Immediate position update on key press

    def keyReleaseEvent(self, event):
        # print(f"Key released: {event.key()}")  # Debug statement
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

        # Emit the signal with the new camera position
        self.positionChanged.emit(self.camera_pos[0], self.camera_pos[1], self.camera_pos[2])

        self.update()  # Redraw the scene

# Main window holding the OpenGL widget
class MainWindow(QMainWindow):
    def __init__(self, node_data, element_data, node_weights):
        super(MainWindow, self).__init__()
        self.setWindowTitle('3D Model - Nodes and Elements with WASD Controls')
        self.setGeometry(100, 100, 800, 600)
        self.glWidget = GLWidget(node_data, element_data, node_weights, self)
        self.setCentralWidget(self.glWidget)

        # Add a status bar
        self.statusBar = self.statusBar()
        self.statusBar.showMessage('Ready')

        # Connect signal from glWidget to update status bar
        self.glWidget.positionChanged.connect(self.update_status_bar)

    def update_status_bar(self, x, y, z):
        self.statusBar.showMessage(f"Camera Position: x={x:.2f}, y={y:.2f}, z={z:.2f}")

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
                u_weight = [
                    float(row['U2_1'].replace(',', '.')) if row['U2_1'] else 0.0,
                    float(row['U2_2'].replace(',', '.')) if row['U2_2'] else 0.0,
                    float(row['U2_3'].replace(',', '.')) if row['U2_3'] else 0.0
                ]
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
