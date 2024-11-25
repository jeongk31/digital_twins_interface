import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

def main():
    # initialize the qt application
    app = QApplication(sys.argv)
    
    # create and show the main window
    window = MainWindow()
    window.setGeometry(100, 100, 1000, 800)
    window.show()
    
    # initialize vtk interaction
    window.interactor.Initialize()
    window.interactor.Start()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()