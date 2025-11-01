from __future__ import annotations
from collections import deque
from typing import Deque, List, Tuple, Optional

from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


class PlotPanel(QtWidgets.QWidget):
    """
    Live PV/SP/OP plot with dual Y axes (PV/SP on left, OP on right).

    Features
    --------
    - Fast, incremental appends with a fixed capacity or sliding time-window
    - Dual y-axes using a secondary ViewBox linked to the main x-axis
    - Context menu: Fit, Clear, Toggle Grid, Toggle AA, Copy CSV
    - Helper APIs:
        append(t, sp, pv, op)
        set_history(ts, sps, pvs, ops)
        clear()
        fit()
        set_capacity(n) or set_time_window(seconds)
        set_pens(sp_pen, pv_pen, op_pen)
        set_right_axis_visible(True/False)

    Notes
    -----
    - Uses deques for O(1) append/pop and plots update only the changed data.
    - Secondary axis auto-rescales along with primary; ranges stay linked in X.
    """

    # Emitted on each update to help outer widgets (e.g., to refresh legends)
    updated = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, *, capacity: int = 5000):
        super().__init__(parent)
        self._capacity = max(100, int(capacity))
        self._time_window_s: Optional[float] = None  # if set, trims points older than (t_max - window)

        # --- data buffers
        self._ts: Deque[float] = deque(maxlen=self._capacity)
        self._sps: Deque[float] = deque(maxlen=self._capacity)
        self._pvs: Deque[float] = deque(maxlen=self._capacity)
        self._ops: Deque[float] = deque(maxlen=self._capacity)

        # --- UI
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("default")
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "PV / SP")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.addLegend(offset=(8, 8))

        # Curves on primary (left) axis
        self.cur_sp = self.plot.plot(name="SP", pen=pg.mkPen(QtGui.QColor("#0080ff"), width=1.5, style=QtCore.Qt.DashLine))
        self.cur_pv = self.plot.plot(name="PV", pen=pg.mkPen(QtGui.QColor("#00c853"), width=2.0))

        # Secondary (right) axis + curve (OP)
        self._right_vb = pg.ViewBox()
        self.plot.showAxis("right")
        self.plot.getAxis("right").setLabel("OP (%)")
        self.plot.scene().addItem(self._right_vb)
        self.plot.getAxis("right").linkToView(self._right_vb)
        self._right_vb.setXLink(self.plot.getViewBox())
        self.cur_op = pg.PlotCurveItem(pen=pg.mkPen(QtGui.QColor("#ff6d00"), width=1.8), name="OP")
        self._right_vb.addItem(self.cur_op)

        # Keep right axis aligned with main vb
        self.plot.getViewBox().sigResized.connect(self._update_views)

        # Context menu
        self.plot.setMenuEnabled(False)
        self.plot.scene().contextMenu = None
        self.plot.scene().sigMouseClicked.connect(self._maybe_context_menu)
        self._grid_on = True
        self._aa_on = True

        layout.addWidget(self.plot)

    # ------------- Public API -------------

    def set_capacity(self, capacity: int):
        """Switch to a fixed-length FIFO buffer of length `capacity`."""
        capacity = max(100, int(capacity))
        if capacity == self._capacity and self._time_window_s is None:
            return
        self._time_window_s = None
        self._capacity = capacity
        self._realloc_buffers(capacity)
        self._refresh_curves()

    def set_time_window(self, seconds: float):
        """Use a sliding time-window (seconds) instead of fixed capacity."""
        self._time_window_s = max(1.0, float(seconds))

    def set_right_axis_visible(self, visible: bool):
        self.plot.getAxis("right").setStyle(showValues=visible)
        self.plot.getAxis("right").setWidth(40 if visible else 1)
        self._right_vb.setVisible(visible)

    def set_pens(self, sp_pen=None, pv_pen=None, op_pen=None):
        if sp_pen is not None:
            self.cur_sp.setPen(sp_pen)
        if pv_pen is not None:
            self.cur_pv.setPen(pv_pen)
        if op_pen is not None:
            self.cur_op.setPen(op_pen)

    def set_history(self, ts: List[float], sps: List[float], pvs: List[float], ops: List[float]):
        n = min(len(ts), len(sps), len(pvs), len(ops))
        if n == 0:
            self.clear()
            return
        if self._time_window_s is None:
            # capacity mode
            cap = self._capacity
            self._ts = deque(ts[-cap:], maxlen=cap)
            self._sps = deque(sps[-cap:], maxlen=cap)
            self._pvs = deque(pvs[-cap:], maxlen=cap)
            self._ops = deque(ops[-cap:], maxlen=cap)
        else:
            # window mode
            tmax = ts[n - 1]
            tmin = tmax - self._time_window_s
            idx0 = 0
            while idx0 < n and ts[idx0] < tmin:
                idx0 += 1
            self._ts = deque(ts[idx0:], maxlen=None)
            self._sps = deque(sps[idx0:], maxlen=None)
            self._pvs = deque(pvs[idx0:], maxlen=None)
            self._ops = deque(ops[idx0:], maxlen=None)
        self._refresh_curves()

    def append(self, t: float, sp: float, pv: float, op: float):
        self._ts.append(float(t))
        self._sps.append(float(sp))
        self._pvs.append(float(pv))
        self._ops.append(float(op))

        if self._time_window_s is not None and len(self._ts) > 1:
            tmax = self._ts[-1]
            tmin = tmax - self._time_window_s
            while self._ts and self._ts[0] < tmin:
                self._ts.popleft(); self._sps.popleft(); self._pvs.popleft(); self._ops.popleft()

        # Cast to list for pyqtgraph
        self.cur_sp.setData(list(self._ts), list(self._sps))
        self.cur_pv.setData(list(self._ts), list(self._pvs))
        self.cur_op.setData(list(self._ts), list(self._ops))
        self.updated.emit()


    def clear(self):
        self._realloc_buffers(self._capacity)
        self._refresh_curves()

    def fit(self):
        """Autoscale both axes to current data."""
        vb = self.plot.getViewBox()
        vb.enableAutoRange(pg.ViewBox.XYAxes, enable=True)
        vb.autoRange()
        self._update_views()

    # ------------- Internals -------------

    def _realloc_buffers(self, capacity: int):
        self._ts = deque(maxlen=capacity)
        self._sps = deque(maxlen=capacity)
        self._pvs = deque(maxlen=capacity)
        self._ops = deque(maxlen=capacity)

    def _refresh_curves(self):
        self.cur_sp.setData(list(self._ts), list(self._sps))
        self.cur_pv.setData(list(self._ts), list(self._pvs))
        self.cur_op.setData(list(self._ts), list(self._ops))
        self.updated.emit()

    def _update_views(self):
        # Keep right viewbox vertically independent but x-linked and aligned
        self._right_vb.setGeometry(self.plot.getViewBox().sceneBoundingRect())
        # Manually trigger linked views' range update
        self._right_vb.linkedViewChanged(self.plot.getViewBox(), self._right_vb.XAxis)

    # ------------- Context menu -------------

    def _maybe_context_menu(self, ev: QtGui.QMouseEvent):
        if ev.button() != QtCore.Qt.RightButton:
            return
        menu = QtWidgets.QMenu(self)
        act_fit = menu.addAction("Fit Data")
        act_clear = menu.addAction("Clear")
        menu.addSeparator()
        act_grid = menu.addAction("Toggle Grid")
        act_grid.setCheckable(True)
        act_grid.setChecked(self._grid_on)
        act_aa = menu.addAction("Toggle Antialiasing")
        act_aa.setCheckable(True)
        act_aa.setChecked(self._aa_on)
        menu.addSeparator()
        act_copy = menu.addAction("Copy CSV to Clipboard")

        chosen = menu.exec(self.mapToGlobal(ev.position().toPoint()))
        if not chosen:
            return

        if chosen == act_fit:
            self.fit()
        elif chosen == act_clear:
            self.clear()
        elif chosen == act_grid:
            self._grid_on = not self._grid_on
            self.plot.showGrid(x=self._grid_on, y=self._grid_on, alpha=0.25 if self._grid_on else 0.0)
        elif chosen == act_aa:
            self._aa_on = not self._aa_on
            pg.setConfigOptions(antialias=self._aa_on)
            self._refresh_curves()
        elif chosen == act_copy:
            QtWidgets.QApplication.clipboard().setText(self._to_csv())

    def _to_csv(self) -> str:
        lines = ["t,SP,PV,OP"]
        for t, sp, pv, op in zip(self._ts, self._sps, self._pvs, self._ops):
            lines.append(f"{t:.6f},{sp:.6f},{pv:.6f},{op:.6f}")
        return "\n".join(lines)
