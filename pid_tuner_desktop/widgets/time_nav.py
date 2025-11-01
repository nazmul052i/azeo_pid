from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


class TimeNav(QtWidgets.QToolBar):
    """
    Zoom/Pan helpers for a pyqtgraph.PlotWidget (time-series focus).
    Buttons:
      - ⟲ Reset
      - ⟸ Pan L
      - ⟹ Pan R
      - ⊕ Zoom In X
      - ⊖ Zoom Out X
      - ⊕Y Zoom In Y
      - ⊖Y Zoom Out Y
      - Fit Data

    Usage:
        nav = TimeNav()
        nav.set_target(plot_widget)

    Shortcuts:
        R (reset), Left/Right arrows (pan), +/- (zoom X), Shift +/- (zoom Y), F (fit)
    """

    def __init__(self, parent=None):
        super().__init__("TimeNav", parent)
        self._plot: pg.PlotWidget | None = None
        self.setIconSize(QtCore.QSize(18, 18))
        self.setMovable(False)

        self._act_reset = self.addAction("⟲ Reset", self.reset_view)
        self.addSeparator()
        self._act_pan_l = self.addAction("⟸", lambda: self._pan(xfrac=-0.2))
        self._act_pan_r = self.addAction("⟹", lambda: self._pan(xfrac=+0.2))
        self.addSeparator()
        self._act_zoom_in = self.addAction("⊕", lambda: self._zoom(xscale=0.8))
        self._act_zoom_out = self.addAction("⊖", lambda: self._zoom(xscale=1.25))
        self.addSeparator()
        self._act_zoom_in_y = self.addAction("⊕Y", lambda: self._zoom(yscale=0.8))
        self._act_zoom_out_y = self.addAction("⊖Y", lambda: self._zoom(yscale=1.25))
        self.addSeparator()
        self._act_fit = self.addAction("Fit", self.fit_data)

        # Shortcuts
        QtGui.QShortcut(QtGui.QKeySequence("R"), self, self.reset_view)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), self, lambda: self._pan(-0.2))
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self, lambda: self._pan(+0.2))
        QtGui.QShortcut(QtGui.QKeySequence("+"), self, lambda: self._zoom(0.8))
        QtGui.QShortcut(QtGui.QKeySequence("-"), self, lambda: self._zoom(1.25))
        QtGui.QShortcut(QtGui.QKeySequence("Shift++"), self, lambda: self._zoom(yscale=0.8))
        QtGui.QShortcut(QtGui.QKeySequence("Shift+-"), self, lambda: self._zoom(yscale=1.25))
        QtGui.QShortcut(QtGui.QKeySequence("F"), self, self.fit_data)

    # ---------- Public API ----------
    def set_target(self, plot: pg.PlotWidget):
        self._plot = plot

    @QtCore.Slot()
    def reset_view(self):
        if not self._plot:
            return
        vb = self._plot.getViewBox()
        vb.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
        vb.autoRange()

    @QtCore.Slot()
    def fit_data(self):
        if not self._plot:
            return
        self._plot.enableAutoRange(x=True, y=True)
        self._plot.getViewBox().autoRange()

    # ---------- Internals ----------
    def _pan(self, xfrac: float = 0.0):
        if not self._plot:
            return
        vb = self._plot.getViewBox()
        x_min, x_max = vb.viewRange()[0]
        dx = (x_max - x_min) * xfrac
        vb.setXRange(x_min + dx, x_max + dx, padding=0)

    def _zoom(self, xscale: float | None = None, yscale: float | None = None):
        if not self._plot:
            return
        vb = self._plot.getViewBox()
        (x_min, x_max), (y_min, y_max) = vb.viewRange()
        if xscale:
            x_mid = 0.5 * (x_min + x_max)
            half = 0.5 * (x_max - x_min) * xscale
            vb.setXRange(x_mid - half, x_mid + half, padding=0)
        if yscale:
            y_mid = 0.5 * (y_min + y_max)
            half = 0.5 * (y_max - y_min) * yscale
            vb.setYRange(y_mid - half, y_mid + half, padding=0)
