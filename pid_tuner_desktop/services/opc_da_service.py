from __future__ import annotations
import threading, time
from typing import Callable, Dict, List, Optional


class OpcDaService:
    """
    Classic OPC DA bridge wrapper. This implementation provides:
      - list_servers(host) -> simulated list
      - subscribe(host, progid, item_ids, callback, period_s) -> polling simulator
      - unsubscribe()
      - is_connected()
    Replace internals with QuickOPC or an external bridge when ready; the public
    API will remain stable for your UI.
    """

    def __init__(self):
        self._host = ""
        self._progid = ""
        self._subs: List[str] = []
        self._cb: Optional[Callable[[str, float, float], None]] = None  # item_id, value, ts
        self._poll_thr: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._t = 0.0
        self._items: Dict[str, float] = {"Channel1.Device1.Random.PV": 42.0,
                                         "Channel1.Device1.Random.OP": 30.0,
                                         "Channel1.Device1.Random.SP": 50.0}

    def list_servers(self, host: str = "") -> List[str]:
        host = host or "(local)"
        # Deterministic set (extend as needed)
        return ["Kepware.KEPServerEX.V6", "Matrikon.OPC.Simulation.1"]

    def subscribe(self, host: str, progid: str, item_ids: List[str],
                  callback: Callable[[str, float, float], None], period_s: float = 1.0):
        self.unsubscribe()
        self._host = host or "(local)"
        self._progid = progid
        self._subs = list(item_ids)
        self._cb = callback
        self._stop.clear()
        self._poll_thr = threading.Thread(target=self._poll_loop, args=(max(0.1, float(period_s)),), daemon=True)
        self._poll_thr.start()

    def unsubscribe(self):
        self._stop.set()
        if self._poll_thr and self._poll_thr.is_alive():
            self._poll_thr.join(timeout=1.0)
        self._poll_thr = None
        self._subs.clear()
        self._cb = None

    def is_connected(self) -> bool:
        return self._poll_thr is not None and self._poll_thr.is_alive()

    # -------- internal polling sim --------
    def _poll_loop(self, dt: float):
        import math, time as _t
        while not self._stop.is_set():
            self._t += dt
            # simple evolutions
            self._items["Channel1.Device1.Random.SP"] = 50.0 + 10.0 * (1.0 if int(self._t) % 20 < 10 else -1.0)
            self._items["Channel1.Device1.Random.OP"] = 30.0 + 15.0 * math.sin(2 * math.pi * self._t / 25.0)
            self._items["Channel1.Device1.Random.PV"] += (self._items["Channel1.Device1.Random.SP"] - self._items["Channel1.Device1.Random.PV"]) * 0.06

            now = _t.time()
            if self._cb:
                for it in self._subs:
                    v = self._items.get(it, 0.0)
                    try:
                        self._cb(it, float(v), now)
                    except Exception:
                        pass
            _t.sleep(dt)
