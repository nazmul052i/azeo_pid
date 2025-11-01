from __future__ import annotations
import threading, time
from typing import Callable, Dict, List, Optional, Tuple

# Try to use asyncua if it exists; otherwise run a local simulator.
try:
    from asyncua import Client  # type: ignore
    HAS_ASYNCUA = True
except Exception:
    HAS_ASYNCUA = False


class OpcUaService:
    """
    Minimal OPC UA client wrapper with two modes:
      1) Real mode (asyncua present): discover/connect/browse/read/subscribe (polling)
      2) Sim mode (no asyncua): deterministic in-process tag generator you can 'subscribe' to.

    Public API (works both modes):
      - discover_local() -> List[str]
      - browse_root(endpoint) -> List[str]
      - subscribe(endpoint, node_ids: List[str], callback: callable(tag, value, ts))
      - unsubscribe()
      - is_connected()
    """

    def __init__(self):
        self._endpoint = ""
        self._poll_thr: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._subs: List[str] = []
        self._cb: Optional[Callable[[str, float, float], None]] = None  # tag, value, ts

        # simulator state
        self._sim_t = 0.0
        self._sim_tags = {"ns=2;s=Sim.PV": 0.0, "ns=2;s=Sim.OP": 0.0, "ns=2;s=Sim.SP": 5.0}

    # -------- Discovery / Browse (simple) --------
    def discover_local(self) -> List[str]:
        # NOTE: real LDS discovery would require asyncua's discovery client.
        # We return standard loopback endpoints; adjust as needed in real env.
        return ["opc.tcp://localhost:4840", "opc.tcp://127.0.0.1:4841"]

    def browse_root(self, endpoint_url: str) -> List[str]:
        if HAS_ASYNCUA:
            # basic browse of Root->Objects
            try:
                import asyncio
                async def _browse():
                    async with Client(url=endpoint_url) as client:
                        root = client.nodes.root
                        objects = client.nodes.objects
                        refs = await objects.get_children()
                        names = []
                        for n in refs:
                            try:
                                names.append(await n.read_display_name())
                            except Exception:
                                names.append(str(n))
                        return [str(x) for x in names]
                return asyncio.get_event_loop().run_until_complete(_browse())
            except Exception:
                return []
        # sim mode
        return ["Objects", "Types", "Views"]

    # -------- Subscription (polling) --------
    def subscribe(self, endpoint_url: str, node_ids: List[str], callback: Callable[[str, float, float], None], period_s: float = 1.0):
        """
        Subscribes to a group of node_ids. In 'real' mode we poll read_values.
        In sim mode we synthesize values deterministically.
        """
        self.unsubscribe()
        self._endpoint = endpoint_url
        self._subs = list(node_ids)
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

    # -------- internal polling --------
    def _poll_loop(self, dt: float):
        if HAS_ASYNCUA:
            import asyncio
            async def _poll():
                try:
                    async with Client(url=self._endpoint) as client:
                        nodes = [client.get_node(nid) for nid in self._subs]
                        while not self._stop.is_set():
                            now = time.time()
                            try:
                                vals = await asyncio.gather(*[n.read_value() for n in nodes])
                            except Exception:
                                vals = [None] * len(nodes)
                            if self._cb:
                                for nid, v in zip(self._subs, vals):
                                    try:
                                        self._cb(nid, float(v), now)
                                    except Exception:
                                        pass
                            await asyncio.sleep(dt)
                except Exception:
                    # connection failed; end loop
                    pass
            asyncio.get_event_loop().run_until_complete(_poll())
        else:
            # sim mode
            while not self._stop.is_set():
                now = time.time()
                self._sim_t += dt
                # simple deterministic waveforms
                self._sim_tags["ns=2;s=Sim.SP"] = 5.0 + 2.0 * (1.0 if int(self._sim_t) % 30 < 15 else -1.0)
                self._sim_tags["ns=2;s=Sim.OP"] = 50.0 + 10.0 * math.sin(2 * math.pi * self._sim_t / 40.0)
                self._sim_tags["ns=2;s=Sim.PV"] += (self._sim_tags["ns=2;s=Sim.SP"] - self._sim_tags["ns=2;s=Sim.PV"]) * 0.05
                if self._cb:
                    for nid in self._subs:
                        v = self._sim_tags.get(nid, 0.0)
                        try:
                            self._cb(nid, float(v), now)
                        except Exception:
                            pass
                time.sleep(dt)
