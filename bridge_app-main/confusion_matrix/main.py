import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(100, 100, 1000, 800)
    window.show()
    window.interactor.Initialize()
    window.interactor.Start()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()