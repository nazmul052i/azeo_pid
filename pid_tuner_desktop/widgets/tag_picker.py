from __future__ import annotations
from typing import Iterable, List, Dict
from PySide6 import QtCore, QtWidgets


class TagPicker(QtWidgets.QDialog):
    """
    Modal dialog to choose a tag for a role (SP/PV/OP).
    Provides a filter box, a list view, and optional sources per tab.

    Usage:
        dlg = TagPicker(parent)
        dlg.set_role_choices(["SP","PV","OP"])
        dlg.set_sources({"Signals": list_of_tags, "OPC UA": list_of_tags, "Database": list_of_tags})
        if dlg.exec() == QDialog.Accepted:
            role = dlg.selected_role()
            tag = dlg.selected_tag()

    Signals:
        tagChosen(role:str, tag:str)
    """

    tagChosen = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Tag")
        self.resize(500, 420)
        self._models: Dict[str, QtCore.QSortFilterProxyModel] = {}
        self._role_box = QtWidgets.QComboBox()
        self._filter_edit = QtWidgets.QLineEdit()
        self._filter_edit.setPlaceholderText("Filter…")
        self._tabs = QtWidgets.QTabWidget()
        self._ok = QtWidgets.QPushButton("OK")
        self._cancel = QtWidgets.QPushButton("Cancel")
        self._ok.setDefault(True)

        # Layout
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Role:"))
        top.addWidget(self._role_box)
        top.addSpacing(12)
        top.addWidget(self._filter_edit, 1)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self._ok)
        btns.addWidget(self._cancel)

        main = QtWidgets.QVBoxLayout(self)
        main.addLayout(top)
        main.addWidget(self._tabs, 1)
        main.addLayout(btns)

        # Connections
        self._filter_edit.textChanged.connect(self._apply_filter)
        self._ok.clicked.connect(self._accept)
        self._cancel.clicked.connect(self.reject)

        # Defaults
        self.set_role_choices(["SP", "PV", "OP"])
        self.set_sources({"Signals": [], "OPC UA": [], "Database": []})

    # ---------- API ----------
    def set_role_choices(self, roles: Iterable[str]):
        self._role_box.clear()
        self._role_box.addItems(list(roles))

    def set_sources(self, sources: Dict[str, List[str]]):
        """sources: {tab_name: [tag1, tag2, ...]}"""
        self._tabs.clear()
        self._models.clear()
        for name, tags in sources.items():
            view = QtWidgets.QListView()
            model = QtCore.QStringListModel(sorted(tags))
            proxy = QtCore.QSortFilterProxyModel(self)
            proxy.setSourceModel(model)
            proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
            view.setModel(proxy)
            view.doubleClicked.connect(self._accept)
            self._models[name] = proxy
            self._tabs.addTab(view, name)

    def selected_role(self) -> str:
        return self._role_box.currentText()

    def selected_tag(self) -> str:
        view: QtWidgets.QListView = self._tabs.currentWidget()
        idx = view.currentIndex()
        if not idx.isValid():
            return ""
        proxy: QtCore.QSortFilterProxyModel = view.model()
        src = proxy.mapToSource(idx)
        return proxy.sourceModel().data(src, QtCore.Qt.DisplayRole)

    # ---------- internals ----------
    def _apply_filter(self, text: str):
        for proxy in self._models.values():
            proxy.setFilterFixedString(text)

    @QtCore.Slot()
    def _accept(self):
        tag = self.selected_tag()
        if not tag:
            QtWidgets.QMessageBox.information(self, "Select a tag", "Please choose a tag from the list.")
            return
        role = self.selected_role()
        self.tagChosen.emit(role, tag)
        self.accept()
