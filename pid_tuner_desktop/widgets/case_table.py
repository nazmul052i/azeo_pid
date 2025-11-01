from __future__ import annotations
from typing import Dict, Iterable, Tuple
from PySide6 import QtCore, QtGui, QtWidgets


class CaseTable(QtWidgets.QTableWidget):
    """
    Case grid for controller/process parameters with columns:

      [Optimize] [Parameter] [Lower] [Upper] [Existing] [Initial] [Final]

    Features:
      - Inline editing (all numeric except Parameter)
      - Tri-state Optimize checkbox per row
      - Copy/Paste TSV/CSV (preserves columns)
      - Context menu: Reset Final to Initial / Reset Row / Reset All
      - Signals: rowEdited(name, values dict), tableChanged(dict)

    API:
      set_rows(spec) where spec is an iterable of tuples:
        (name, optimize, low, high, existing, initial, final)
      get_rows() -> dict[name] = {...}
    """

    rowEdited = QtCore.Signal(str, dict)
    tableChanged = QtCore.Signal(dict)

    COL_OPT = 0
    COL_NAME = 1
    COL_LOW = 2
    COL_HIGH = 3
    COL_EXIST = 4
    COL_INIT = 5
    COL_FINAL = 6

    HEADERS = ["Optimize", "Parameter", "Lower", "Upper", "Existing", "Initial", "Final"]

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)
        self.itemChanged.connect(self._on_item_changed)
        self._in_change = False

        QtGui.QShortcut(QtGui.QKeySequence.Copy, self, self.copy_selection)
        QtGui.QShortcut(QtGui.QKeySequence.Paste, self, self.paste_into_selection)

    # ---------- API ----------
    def set_rows(self, rows: Iterable[Tuple[str, bool, float, float, float, float, float]]):
        self._in_change = True
        try:
            self.setRowCount(0)
            for (name, opt, low, high, exist, init, final) in rows:
                r = self.rowCount()
                self.insertRow(r)

                chk = QtWidgets.QTableWidgetItem()
                chk.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                chk.setCheckState(QtCore.Qt.Checked if opt else QtCore.Qt.Unchecked)
                self.setItem(r, self.COL_OPT, chk)

                name_item = QtWidgets.QTableWidgetItem(name)
                name_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.setItem(r, self.COL_NAME, name_item)

                for col, val in (
                    (self.COL_LOW, low),
                    (self.COL_HIGH, high),
                    (self.COL_EXIST, exist),
                    (self.COL_INIT, init),
                    (self.COL_FINAL, final),
                ):
                    self.setItem(r, col, self._num_item(val))
            self.resizeColumnsToContents()
        finally:
            self._in_change = False
        self.tableChanged.emit(self.get_rows())

    def get_rows(self) -> Dict[str, Dict[str, float | bool]]:
        out: Dict[str, Dict[str, float | bool]] = {}
        for r in range(self.rowCount()):
            name = self.item(r, self.COL_NAME).text()
            out[name] = {
                "optimize": self.item(r, self.COL_OPT).checkState() == QtCore.Qt.Checked,
                "lower": float(self.item(r, self.COL_LOW).text()),
                "upper": float(self.item(r, self.COL_HIGH).text()),
                "existing": float(self.item(r, self.COL_EXIST).text()),
                "initial": float(self.item(r, self.COL_INIT).text()),
                "final": float(self.item(r, self.COL_FINAL).text()),
            }
        return out

    # ---------- internals ----------
    @staticmethod
    def _fmt(v: float) -> str:
        return f"{v:.6g}"

    def _num_item(self, value: float) -> QtWidgets.QTableWidgetItem:
        it = QtWidgets.QTableWidgetItem(self._fmt(value))
        it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        it.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        return it

    def _open_menu(self, pos):
        rows = sorted({i.row() for i in self.selectedIndexes()}) or list(range(self.rowCount()))
        menu = QtWidgets.QMenu(self)
        act_reset_final = menu.addAction("Reset Final → Initial (Selected)")
        act_reset_row = menu.addAction("Reset Selected Row(s)")
        act_reset_all = menu.addAction("Reset All Rows")
        menu.addSeparator()
        act_copy = menu.addAction("Copy")
        act_paste = menu.addAction("Paste")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if not chosen:
            return
        if chosen == act_reset_final:
            self._in_change = True
            try:
                for r in rows:
                    self.item(r, self.COL_FINAL).setText(self.item(r, self.COL_INIT).text())
            finally:
                self._in_change = False
            self.tableChanged.emit(self.get_rows())
        elif chosen == act_reset_row:
            self._reset_rows(rows)
        elif chosen == act_reset_all:
            self._reset_rows(list(range(self.rowCount())))
        elif chosen == act_copy:
            self.copy_selection()
        elif chosen == act_paste:
            self.paste_into_selection()

    def _reset_rows(self, rows):
        self._in_change = True
        try:
            for r in rows:
                # reset to Existing->Initial->Final pipeline
                exist = self.item(r, self.COL_EXIST).text()
                for c in (self.COL_INIT, self.COL_FINAL):
                    self.item(r, c).setText(exist)
                # keep bounds and 'optimize' unchanged
        finally:
            self._in_change = False
        self.tableChanged.emit(self.get_rows())

    def _on_item_changed(self, item: QtWidgets.QTableWidgetItem):
        if self._in_change:
            return
        r, c = item.row(), item.column()
        name = self.item(r, self.COL_NAME).text()

        # validate numerics
        if c in (self.COL_LOW, self.COL_HIGH, self.COL_EXIST, self.COL_INIT, self.COL_FINAL):
            try:
                float(item.text())
            except ValueError:
                # revert to zero on invalid text
                self.blockSignals(True)
                item.setText("0")
                self.blockSignals(False)

        # ensure bounds low<=high
        if c in (self.COL_LOW, self.COL_HIGH):
            low = float(self.item(r, self.COL_LOW).text())
            high = float(self.item(r, self.COL_HIGH).text())
            if low > high:
                self.blockSignals(True)
                self.item(r, self.COL_LOW).setText(self._fmt(high))
                self.item(r, self.COL_HIGH).setText(self._fmt(low))
                self.blockSignals(False)

        self.rowEdited.emit(name, self.get_rows()[name])
        self.tableChanged.emit(self.get_rows())

    # ---------- Copy/Paste ----------
    def copy_selection(self):
        rows = sorted({i.row() for i in self.selectedIndexes()}) or list(range(self.rowCount()))
        cols = list(range(self.columnCount()))
        data = []
        for r in rows:
            row = []
            for c in cols:
                if c == self.COL_OPT:
                    row.append("1" if self.item(r, c).checkState() == QtCore.Qt.Checked else "0")
                else:
                    row.append(self.item(r, c).text())
            data.append("\t".join(row))
        QtWidgets.QApplication.clipboard().setText("\n".join(data))

    def paste_into_selection(self):
        text = QtWidgets.QApplication.clipboard().text()
        if not text.strip():
            return
        rows_in = [line for line in text.splitlines() if line.strip()]
        start_rows = sorted({i.row() for i in self.selectedIndexes()}) or [0]
        r0 = start_rows[0]
        self._in_change = True
        try:
            for i, line in enumerate(rows_in):
                parts = [p.strip() for p in line.replace(",", "\t").split("\t")]
                if not parts:
                    continue
                r = r0 + i
                if r >= self.rowCount():
                    break
                for c in range(min(len(parts), self.columnCount())):
                    if c == self.COL_OPT:
                        self.item(r, c).setCheckState(QtCore.Qt.Checked if parts[c] in ("1", "true", "True") else QtCore.Qt.Unchecked)
                    elif c == self.COL_NAME:
                        # don't allow renaming via paste
                        continue
                    else:
                        self.item(r, c).setText(parts[c])
        finally:
            self._in_change = False
        self.tableChanged.emit(self.get_rows())
