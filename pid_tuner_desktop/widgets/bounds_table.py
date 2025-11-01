from __future__ import annotations
from typing import Dict, List, Tuple
from PySide6 import QtCore, QtGui, QtWidgets


class BoundsTable(QtWidgets.QTableWidget):
    """
    Lower/Upper bounds editor with validation, copy/paste (TSV/CSV),
    context menu (Reset Selected / Reset All), and a 'locked' option
    to prevent edits.

    API:
        set_parameters(names, bounds=None) -> load rows
        get_bounds() -> {name: (low, high)}
        set_bounds(mapping) -> update a subset
        set_locked(True/False) -> enable/disable editing

    Signals:
        boundsChanged(dict[str, tuple[float,float]])
        cellEdited(name:str, low:float, high:float)
    """

    boundsChanged = QtCore.Signal(dict)
    cellEdited = QtCore.Signal(str, float, float)

    COL_NAME = 0
    COL_LOW = 1
    COL_HIGH = 2

    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        self.setHorizontalHeaderLabels(["Parameter", "Lower", "Upper"])
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self._locked = False
        self._validator = QtGui.QDoubleValidator(bottom=-1e12, top=1e12, decimals=6)
        self._default_low = -1e6
        self._default_high = 1e6
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)
        self.itemChanged.connect(self._on_item_changed)
        self._in_change = False

        # Shortcuts
        QtGui.QShortcut(QtGui.QKeySequence.Copy, self, self.copy_selection)
        QtGui.QShortcut(QtGui.QKeySequence.Paste, self, self.paste_into_selection)

    # ---------- Public API ----------
    def set_locked(self, locked: bool):
        self._locked = locked
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if not locked:
            flags |= QtCore.Qt.ItemIsEditable
        for r in range(self.rowCount()):
            for c in (self.COL_LOW, self.COL_HIGH):
                it = self.item(r, c)
                if it:
                    it.setFlags(flags)

    def set_parameters(self, names: List[str], bounds: Dict[str, Tuple[float, float]] | None = None):
        self._in_change = True
        try:
            self.setRowCount(0)
            for name in names:
                r = self.rowCount()
                self.insertRow(r)
                name_item = QtWidgets.QTableWidgetItem(name)
                name_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.setItem(r, self.COL_NAME, name_item)

                low, high = bounds.get(name, (self._default_low, self._default_high)) if bounds else (
                    self._default_low, self._default_high
                )
                low_item = self._make_num_item(low)
                high_item = self._make_num_item(high)
                self.setItem(r, self.COL_LOW, low_item)
                self.setItem(r, self.COL_HIGH, high_item)
            self.resizeColumnsToContents()
        finally:
            self._in_change = False
        self.boundsChanged.emit(self.get_bounds())

    def set_bounds(self, mapping: Dict[str, Tuple[float, float]]):
        # updates a subset of rows
        for r in range(self.rowCount()):
            name = self.item(r, self.COL_NAME).text()
            if name in mapping:
                low, high = mapping[name]
                self.item(r, self.COL_LOW).setText(self._fmt(low))
                self.item(r, self.COL_HIGH).setText(self._fmt(high))
        self.boundsChanged.emit(self.get_bounds())

    def get_bounds(self) -> Dict[str, Tuple[float, float]]:
        out: Dict[str, Tuple[float, float]] = {}
        for r in range(self.rowCount()):
            name = self.item(r, self.COL_NAME).text()
            low = float(self.item(r, self.COL_LOW).text())
            high = float(self.item(r, self.COL_HIGH).text())
            out[name] = (low, high)
        return out

    # ---------- Internals ----------
    def _make_num_item(self, value: float) -> QtWidgets.QTableWidgetItem:
        it = QtWidgets.QTableWidgetItem(self._fmt(value))
        it.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter))
        it.setFlags((QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled |
                    (QtCore.Qt.ItemIsEditable if not self._locked else QtCore.Qt.ItemIsSelectable)))
        return it

    @staticmethod
    def _fmt(v: float) -> str:
        # compact float formatting
        return f"{v:.6g}"

    def _open_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        act_reset_sel = menu.addAction("Reset Selected")
        act_reset_all = menu.addAction("Reset All")
        menu.addSeparator()
        act_copy = menu.addAction("Copy")
        act_paste = menu.addAction("Paste")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if not chosen:
            return
        if chosen == act_reset_sel:
            self._reset_rows(self._selected_rows())
        elif chosen == act_reset_all:
            self._reset_rows(list(range(self.rowCount())))
        elif chosen == act_copy:
            self.copy_selection()
        elif chosen == act_paste:
            self.paste_into_selection()

    def _reset_rows(self, rows: List[int]):
        self._in_change = True
        try:
            for r in rows:
                self.item(r, self.COL_LOW).setText(self._fmt(self._default_low))
                self.item(r, self.COL_HIGH).setText(self._fmt(self._default_high))
        finally:
            self._in_change = False
        self.boundsChanged.emit(self.get_bounds())

    def _selected_rows(self) -> List[int]:
        rows = sorted({i.row() for i in self.selectedIndexes()})
        return rows or list(range(self.rowCount()))

    def _on_item_changed(self, item: QtWidgets.QTableWidgetItem):
        if self._in_change or item.column() not in (self.COL_LOW, self.COL_HIGH):
            return

        # validate numeric and low<=high
        try:
            float(item.text())
        except ValueError:
            # revert to previous valid text
            self.blockSignals(True)
            item.setText("0")
            self.blockSignals(False)
            return

        r = item.row()
        low = float(self.item(r, self.COL_LOW).text())
        high = float(self.item(r, self.COL_HIGH).text())
        if low > high:
            # swap to enforce low<=high
            self.blockSignals(True)
            self.item(r, self.COL_LOW).setText(self._fmt(high))
            self.item(r, self.COL_HIGH).setText(self._fmt(low))
            self.blockSignals(False)
            low, high = high, low

        name = self.item(r, self.COL_NAME).text()
        self.boundsChanged.emit(self.get_bounds())
        self.cellEdited.emit(name, low, high)

    # ---------- Copy/Paste ----------
    def copy_selection(self):
        rows = self._selected_rows()
        cols = [self.COL_NAME, self.COL_LOW, self.COL_HIGH]
        data: List[List[str]] = []
        for r in rows:
            data.append([self.item(r, c).text() for c in cols])
        text = "\n".join("\t".join(row) for row in data)
        QtWidgets.QApplication.clipboard().setText(text)

    def paste_into_selection(self):
        text = QtWidgets.QApplication.clipboard().text()
        if not text.strip():
            return
        lines = [line for line in text.splitlines() if line.strip()]
        start_rows = self._selected_rows()
        r0 = start_rows[0] if start_rows else 0

        self._in_change = True
        try:
            for i, line in enumerate(lines):
                parts = [p.strip() for p in line.replace(",", "\t").split("\t")]
                if not parts:
                    continue
                r = r0 + i
                if r >= self.rowCount():
                    break
                # allow either [name, low, high] or [low, high]
                if len(parts) == 3:
                    name, low, high = parts
                    if name and name != self.item(r, self.COL_NAME).text():
                        # keep row name; ignore pasted name
                        low, high = parts[1], parts[2]
                elif len(parts) >= 2:
                    low, high = parts[0], parts[1]
                else:
                    continue
                try:
                    float(low); float(high)
                except ValueError:
                    continue
                self.item(r, self.COL_LOW).setText(self._fmt(float(low)))
                self.item(r, self.COL_HIGH).setText(self._fmt(float(high)))
        finally:
            self._in_change = False
        self.boundsChanged.emit(self.get_bounds())
