"""
OPC UA acquisition using asyncua.
Subscribes to mapped nodes and pushes samples into a writer queue.
"""
import asyncio
import time
from typing import Dict, Optional, Callable
from asyncua import Client, ua

class UaAcquirer:
    """
    endpoint: "opc.tcp://host:port"
    node_map: {"PV": "ns=2;s=...", "OP": "ns=2;s=...", "SP": "...", "MODE": "..."}
    on_sample: callable(ts, nodeid_str, value, quality) -> None (usually writer.enqueue)
    """
    def __init__(self, endpoint: str, node_map: Dict[str, str],
                 on_sample: Callable[[float, str, float, int], None]):
        self.endpoint = endpoint
        self.node_map = dict(node_map)
        self.on_sample = on_sample
        self._sub = None
        self._handles = {}
        self._client: Optional[Client] = None

    async def run(self, period_ms: int = 250):
        async with Client(url=self.endpoint) as client:
            self._client = client
            self._sub = await client.create_subscription(period_ms, self)
            for role, nodeid in self.node_map.items():
                node = client.get_node(nodeid)
                handle = await self._sub.subscribe_data_change(node)
                self._handles[handle] = role
            # keep alive
            while True:
                await asyncio.sleep(1.0)

    # Subscription handler API
    def datachange_notification(self, node, val, data):
        ts = time.time()
        nodeid_s = node.nodeid.to_string()
        quality = int(data.monitored_item.Value.StatusCode.value)
        try:
            v = float(val)
        except Exception:
            # store NaN or 0 on non-numeric; here we choose NaN as float("nan")
            v = float("nan")
        self.on_sample(ts, nodeid_s, v, quality)

    async def stop(self):
        try:
            if self._sub:
                await self._sub.delete()
            if self._client:
                await self._client.disconnect()
        except Exception:
            pass