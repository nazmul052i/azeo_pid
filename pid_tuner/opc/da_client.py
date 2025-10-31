"""
OPC DA acquisition (optional).
If running on Windows with OpenOPC + pywin32, you can poll DA tags.
Alternatively, run your .NET QuickOPC bridge and skip this module.
"""
import time
from typing import List, Callable, Dict

try:
    import OpenOPC  # type: ignore
except Exception:
    OpenOPC = None

class DaPoller:
    """
    server_progid: e.g., "Kepware.KEPServerEX.V6"
    tags: dict role-> fully qualified tag name, e.g., {"PV": "Channel1.Device1.PV", ...}
    on_sample: callable(ts, tagname, value, quality) -> None
    """
    def __init__(self, server_progid: str, tags: Dict[str, str],
                 on_sample: Callable[[float, str, float, int], None]):
        self.server_progid = server_progid
        self.tags = dict(tags)
        self.on_sample = on_sample
        self._opc = None

    def connect(self):
        if OpenOPC is None:
            raise RuntimeError("OpenOPC not available. Install OpenOPC+pywin32 or use your .NET collector.")
        self._opc = OpenOPC.client()
        self._opc.connect(self.server_progid)

    def poll_loop(self, period_s: float = 0.25):
        if self._opc is None:
            self.connect()
        tag_list = list(self.tags.values())
        while True:
            try:
                results = self._opc.read(tag_list, group='g1')
                ts = time.time()
                # results: list of (value, quality, timestamp)
                for (tag, role), (val, q, _ts) in zip(self.tags.items(), results):
                    try:
                        v = float(val)
                    except Exception:
                        v = float("nan")
                    self.on_sample(ts, self.tags[role], v, int(q))
                time.sleep(period_s)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(period_s)