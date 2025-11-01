from __future__ import annotations
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets
from viewmodels.app_state import AppState

# custom item roles/types
ROLE_NODE_TYPE = QtCore.Qt.UserRole + 1
TYPE_ROOT = "root"
TYPE_SIGNALS = "signals"
TYPE_SIGNAL = "signal"
TYPE_IMPORTED = "imported"
TYPE_CASES = "cases"
TYPE_CASE = "case"


class ProjectBrowser(QtWidgets.QTreeWidget):
    """
    Project tree with three groups:
      - Signals            (tag list: PV/SP/OP etc.)
      - Imported Models    (future model items)
      - Loop Tuning Cases  (case nodes)

    Features
    --------
    - Right-click context menu with OPC UA/DA actions and case ops
    - Inline rename (F2) for signals and cases
    - Drag & Drop: signals are draggable; mime text = tag name
    - Double-click on a signal triggers "Subscribe Live"
    - Delete key removes selected node (where applicable)

    Signals (to MainWindow/services)
    --------------------------------
    request_opc_ua_discover()                   # discover local UA servers
    request_opc_ua_connect_browse(str)          # endpoint url (manual connect/browse)
    request_opc_da_browse(str)                  # host ("" = local)
    add_signal_requested(str)                   # newly created tag name
    subscribe_live_requested(str)               # tag name
    new_case_requested()
    delete_node_requested(str, str)             # (nodeType, name)
    """

    request_opc_ua_discover = QtCore.Signal()
    request_opc_ua_connect_browse = QtCore.Signal(str)
    request_opc_da_browse = QtCore.Signal(str)
    add_signal_requested = QtCore.Signal(str)
    subscribe_live_requested = QtCore.Signal(str)
    new_case_requested = QtCore.Signal()
    delete_node_requested = QtCore.Signal(str, str)

    def __init__(self, state: AppState, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.state = state

        self.setHeaderHidden(True)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setUniformRowHeights(True)
        self.setExpandsOnDoubleClick(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # build initial tree
        self._build()

    # --------- Tree construction / helpers ----------

    def _mk(self, text: str, node_type: str, editable: bool = False) -> QtWidgets.QTreeWidgetItem:
        it = QtWidgets.QTreeWidgetItem([text])
        it.setData(0, ROLE_NODE_TYPE, node_type)
        if editable:
            it.setFlags(it.flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        else:
            it.setFlags(it.flags() | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        return it

    def _build(self):
        self.clear()
        root = self._mk("PID Tuner Project", TYPE_ROOT)

        # Signals group
        self.node_signals = self._mk("Signals", TYPE_SIGNALS)
        for tag in ["TCAF", "PCAF", "TCBE", "TCCF", "TCCD", "TCAF.SP"]:
            self.node_signals.addChild(self._mk(tag, TYPE_SIGNAL, editable=True))

        # Imported Models
        self.node_imported = self._mk("Imported Models", TYPE_IMPORTED)

        # Cases
        self.node_cases = self._mk("Loop Tuning Cases", TYPE_CASES)
        self.node_cases.addChild(self._mk(self.state.current_case(), TYPE_CASE, editable=True))

        root.addChild(self.node_signals)
        root.addChild(self.node_imported)
        root.addChild(self.node_cases)
        self.addTopLevelItem(root)
        self.expandItem(root)
        self.expandItem(self.node_signals)
        self.expandItem(self.node_cases)

    # --------------- Context Menu ----------------

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        it = self.itemAt(event.pos())
        if not it:
            return
        node_type = it.data(0, ROLE_NODE_TYPE)
        name = it.text(0)

        menu = QtWidgets.QMenu(self)

        # ROOT or SIGNALS group → add/import/discover
        if node_type in (TYPE_ROOT, TYPE_SIGNALS):
            menu.addSection("Signals")
            act_add = menu.addAction("Add Signal…")
            act_rename = menu.addAction("Rename Selected…")
            act_remove = menu.addAction("Remove Selected")
            menu.addSeparator()
            act_subua = menu.addAction("Import from OPC UA…")
            act_subda = menu.addAction("Import from OPC DA…")
            menu.addSeparator()
            act_disc = menu.addAction("OPC UA: Discover Local Servers")

        # individual SIGNAL → subscribe/rename/remove
        elif node_type == TYPE_SIGNAL:
            menu.addSection(name)
            act_sub = menu.addAction("Subscribe Live")
            act_rename = menu.addAction("Rename…")
            act_del = menu.addAction("Remove")

        # CASES group → new case
        elif node_type == TYPE_CASES:
            menu.addSection("Cases")
            act_new = menu.addAction("New Case")

        # individual CASE → duplicate/delete/rename
        elif node_type == TYPE_CASE:
            menu.addSection(name)
            act_dup = menu.addAction("Duplicate Case")
            act_rename = menu.addAction("Rename…")
            act_del = menu.addAction("Delete Case")

        chosen = menu.exec(self.mapToGlobal(event.pos()))
        if not chosen:
            return

        # ---- Signals group / root actions
        if 'act_add' in locals() and chosen == act_add:
            text, ok = QtWidgets.QInputDialog.getText(self, "Add Signal", "Tag name:")
            if ok and text.strip():
                self._add_signal(text.strip())

        if 'act_rename' in locals() and chosen == act_rename:
            self.editItem(it, 0)

        if 'act_remove' in locals() and chosen == act_remove and node_type in (TYPE_SIGNAL,):
            parent = it.parent() or self.invisibleRootItem()
            parent.removeChild(it)
            self.delete_node_requested.emit(TYPE_SIGNAL, name)

        if 'act_subua' in locals() and chosen == act_subua:
            endpoint, ok = QtWidgets.QInputDialog.getText(self, "OPC UA Endpoint", "e.g. opc.tcp://localhost:4840")
            if ok and endpoint.strip():
                self.request_opc_ua_connect_browse.emit(endpoint.strip())

        if 'act_subda' in locals() and chosen == act_subda:
            host, ok = QtWidgets.QInputDialog.getText(self, "OPC DA Host", "Computer name (blank = local):")
            if ok:
                self.request_opc_da_browse.emit(host.strip())

        if 'act_disc' in locals() and chosen == act_disc:
            self.request_opc_ua_discover.emit()

        # ---- Individual signal actions
        if node_type == TYPE_SIGNAL:
            if chosen == locals().get('act_sub'):
                self.subscribe_live_requested.emit(name)
            if chosen == locals().get('act_del'):
                parent = it.parent() or self.invisibleRootItem()
                parent.removeChild(it)
                self.delete_node_requested.emit(TYPE_SIGNAL, name)
            if chosen == locals().get('act_rename'):
                self.editItem(it, 0)

        # ---- Cases group
        if node_type == TYPE_CASES and chosen == locals().get('act_new'):
            self._add_case("new case")

        # ---- Case node actions
        if node_type == TYPE_CASE:
            if chosen == locals().get('act_dup'):
                self._duplicate_case(it)
            if chosen == locals().get('act_del'):
                parent = it.parent() or self.invisibleRootItem()
                parent.removeChild(it)
                self.delete_node_requested.emit(TYPE_CASE, name)
            if chosen == locals().get('act_rename'):
                self.editItem(it, 0)

    # --------------- Editing / Drag ---------------

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        it = self.currentItem()
        if not it:
            return super().keyPressEvent(e)
        node_type = it.data(0, ROLE_NODE_TYPE)

        if e.key() == QtCore.Qt.Key_F2 and it.flags() & QtCore.Qt.ItemIsEditable:
            self.editItem(it, 0)
            return
        if e.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            if node_type in (TYPE_SIGNAL, TYPE_CASE):
                parent = it.parent() or self.invisibleRootItem()
                name = it.text(0)
                parent.removeChild(it)
                self.delete_node_requested.emit(node_type, name)
                return
        return super().keyPressEvent(e)

    def mimeData(self, items: List[QtWidgets.QTreeWidgetItem]) -> QtCore.QMimeData:
        # Provide plain-text tag for drag targets (e.g., live table)
        md = super().mimeData(items)
        if items:
            t = items[0].data(0, ROLE_NODE_TYPE)
            if t == TYPE_SIGNAL:
                md.setText(items[0].text(0))
        return md

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        it = self.itemAt(e.position().toPoint())
        if it and it.data(0, ROLE_NODE_TYPE) == TYPE_SIGNAL:
            self.subscribe_live_requested.emit(it.text(0))
        super().mouseDoubleClickEvent(e)

    # --------------- Public helpers ---------------

    def _add_signal(self, name: str):
        child = self._mk(name, TYPE_SIGNAL, editable=True)
        self.node_signals.addChild(child)
        self.expandItem(self.node_signals)
        self.setCurrentItem(child)
        self.add_signal_requested.emit(name)

    def _add_case(self, name: str):
        child = self._mk(name, TYPE_CASE, editable=True)
        self.node_cases.addChild(child)
        self.expandItem(self.node_cases)
        self.setCurrentItem(child)
        self.new_case_requested.emit()

    def _duplicate_case(self, it: QtWidgets.QTreeWidgetItem):
        name = it.text(0)
        dup = self._mk(f"{name} (copy)", TYPE_CASE, editable=True)
        it.parent().addChild(dup)
        self.expandItem(it.parent())

    # convenience getters
    def list_signals(self) -> List[str]:
        out: List[str] = []
        for i in range(self.node_signals.childCount()):
            out.append(self.node_signals.child(i).text(0))
        return out

    def list_cases(self) -> List[str]:
        out: List[str] = []
        for i in range(self.node_cases.childCount()):
            out.append(self.node_cases.child(i).text(0))
        return out
