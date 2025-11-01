from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any
from PySide6 import QtCore


class AppState(QtCore.QObject):
    """
    Global application state shared across viewmodels.
    Emits granular signals on changes so panels can react.
    """

    # signals
    samplingIntervalChanged = QtCore.Signal(float)
    currentCaseChanged = QtCore.Signal(str)
    tagMapChanged = QtCore.Signal(dict)          # {"SP": "TCAF.SP", "PV": "TCAF", "OP":"PCAF"}
    themeChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sampling_interval_s: float = 1.0
        self._current_case: str = "tuning case"
        self._tags: Dict[str, str] = {"SP": "TCAF.SP", "PV": "TCAF", "OP": "PCAF"}
        self._theme: str = "dark"

    # --- sampling interval (seconds)
    def sampling_interval(self) -> float:
        return self._sampling_interval_s

    def set_sampling_interval(self, seconds: float):
        seconds = max(1e-6, float(seconds))
        if seconds != self._sampling_interval_s:
            self._sampling_interval_s = seconds
            self.samplingIntervalChanged.emit(seconds)

    # --- current case
    def current_case(self) -> str:
        return self._current_case

    def set_current_case(self, name: str):
        name = (name or "").strip() or "tuning case"
        if name != self._current_case:
            self._current_case = name
            self.currentCaseChanged.emit(name)

    # --- tag map (SP/PV/OP)
    def tags(self) -> Dict[str, str]:
        return dict(self._tags)

    def set_tag(self, role: str, tag: str):
        role = role.upper()
        if role in ("SP", "PV", "OP"):
            if self._tags.get(role) != tag:
                self._tags[role] = tag
                self.tagMapChanged.emit(dict(self._tags))

    # --- theme
    def theme(self) -> str:
        return self._theme

    def set_theme(self, theme: str):
        theme = theme.lower().strip() or "dark"
        if theme != self._theme:
            self._theme = theme
            self.themeChanged.emit(theme)

    # --- serialization helpers
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sampling_interval_s": self._sampling_interval_s,
            "current_case": self._current_case,
            "tags": dict(self._tags),
            "theme": self._theme,
        }

    def load_dict(self, data: Dict[str, Any]):
        self.set_sampling_interval(float(data.get("sampling_interval_s", self._sampling_interval_s)))
        self.set_current_case(str(data.get("current_case", self._current_case)))
        tags = data.get("tags", {})
        for role in ("SP", "PV", "OP"):
            if role in tags:
                self.set_tag(role, tags[role])
        self.set_theme(str(data.get("theme", self._theme)))
