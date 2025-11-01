from __future__ import annotations
import os
import sys
from PySide6 import QtCore, QtGui, QtWidgets
#import qrc_resources  # ensures :/icons/... and :/qss/... exist


# High-DPI / Fusion style defaults
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

def _try_load_qss(app: QtWidgets.QApplication):
    # Prefer resource path first (:/qss/dark.qss), then filesystem qss/dark.qss
    for path in (":/qss/dark.qss", os.path.join(os.path.dirname(__file__), "qss", "dark.qss")):
        try:
            f = QtCore.QFile(path)
            if f.exists() and f.open(QtCore.QIODevice.ReadOnly | QtCore.QIODevice.Text):
                app.setStyleSheet(bytes(f.readAll()).decode("utf-8"))
                return
        except Exception:
            pass

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("PID Tuner & Loop Analyzer")
    app.setOrganizationName("PIDLab")
    app.setOrganizationDomain("pidlab.local")
    app.setStyle("Fusion")

    _try_load_qss(app)

    # Import lazily so UI is initialized with style
    from main_window import MainWindow
    win = MainWindow()
    win.show()

    # Optional: taskbar icon from qrc or filesystem
    icon = QtGui.QIcon(":/icons/app.ico")
    if icon.isNull():
        fs_icon = os.path.join(os.path.dirname(__file__), "qrc", "icons", "app.ico")
        if os.path.exists(fs_icon):
            icon = QtGui.QIcon(fs_icon)
    if not icon.isNull():
        app.setWindowIcon(icon)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
