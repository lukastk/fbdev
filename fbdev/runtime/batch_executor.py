"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/02_runtime/01_batch_executor.ipynb.

# %% ../../nbs/api/02_runtime/01_batch_executor.ipynb 4
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from types import MappingProxyType
from typing import Type, Tuple, Dict, List

import fbdev
from ..exceptions import NodeError, EdgeError
from ..comp.packet import Packet
from ..comp.port import PortType, PortSpec, PortSpecCollection, PortID
from ..comp.base_component import BaseComponent
from ..graph.graph_spec import GraphSpec, NodeSpec
from ..graph.packet_registry import TrackedPacket
from ..graph.net import Edge, Node, BaseNode
from ..graph.graph_component import GraphComponentFactory
from . import BaseRuntime
from ._utils import parse_args_into_port_packets, setup_packet_senders_and_receivers

# %% auto 0
__all__ = ['BatchExecutor']

# %% ../../nbs/api/02_runtime/01_batch_executor.ipynb 6
class BatchExecutor(BaseRuntime):
    """Executes a net like a batch process (input fed in the beginning, and no input during the execution, and output is returned at the end)."""
    def __init__(self, node:BaseNode):
        super().__init__()
        self._node:BaseNode = node
    
    def _setup_execution(self, *args, config_vals={}, signals=set(), ports_to_get=None, **kwargs):
        if self._node.states.started.get(): raise RuntimeError("Node has already started.")
        if self._node.states.stopped.get(): raise RuntimeError("Cannot run stopped node.")
        
        if ports_to_get is None:
            ports_to_get = [port.id for port in self._node.ports.output.values()]
        
        input_vals, config_vals, signals = parse_args_into_port_packets(self._node.port_specs, config_vals, signals, *args, **kwargs)
        
        output_vals, message_vals, input_senders, config_senders, output_receivers, message_receivers = \
            setup_packet_senders_and_receivers(self._node.ports, input_vals, config_vals, ports_to_get, *args, **kwargs)
        
        async def main():
            await self._node.start()
            await self._node.task_manager.exec_coros(*input_senders, *config_senders, *output_receivers, *message_receivers)
            await self._node.task_manager.exec_coros(self._node.stop())
            
        return main(), output_vals

    def start(self, *args, config={}, signals=set(), ports_to_get:List[PortID]|None=None, **kwargs):
        """Note: this method cannot be run from within an event loop."""
        super().start()
        coro, output = self._setup_execution(*args, config_vals=config, signals=signals, ports_to_get=ports_to_get, **kwargs)
        asyncio.run(coro)
        self._started = True
        return output
    
    async def astart(self, *args, config={}, signals=set(), ports_to_get:List[PortID]|None=None, **kwargs):
        await super().astart()
        coro, output = self._setup_execution(*args, config_vals=config, signals=signals, ports_to_get=ports_to_get, **kwargs)
        await coro
        self._started = True
        return output
    
    async def stop(self):
        await super().stop()
        if not self._node.states.stopped.get():
            if not self._node.states.stopped.get():
                await self._node.task_manager.exec_coros(self._node.stop())
        self._stopped = True
