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
from ..graph.net import Edge, Node, Net
from ..graph.graph_component import GraphComponentFactory
from . import BaseNetRuntime
from ._utils import parse_args_into_port_packets, setup_packet_senders_and_receivers

# %% auto 0
__all__ = ['BatchExecutor']

# %% ../../nbs/api/02_runtime/01_batch_executor.ipynb 6
class BatchExecutor(BaseNetRuntime):
    """Executes a net like a batch process (input fed in the beginning, and no input during the execution, and output is returned at the end)."""
    def __init__(self, net:Net):
        super().__init__()
        self._net:Net = net
    
    def _setup_execution_coro(self, *args, config_vals={}, signals=set(), ports_to_get=None, **kwargs):
        if self._net.states.started.get(): raise RuntimeError("Net has already started.")
        if self._net.states.terminated.get(): raise RuntimeError("Cannot run terminated Net.")
        
        if ports_to_get is None:
            ports_to_get = [port.id for port in self._net.ports.output.values()]
        
        input_vals, config_vals, signals = parse_args_into_port_packets(self._net.port_specs, config_vals, signals, *args, **kwargs)
        
        output_vals, message_vals, input_senders, config_senders, output_receivers, message_receivers = \
            setup_packet_senders_and_receivers(self._net.ports, input_vals, config_vals, ports_to_get, *args, **kwargs)
        
        async def main():
            await self._net.start()
            await self._net.exec_coros(*input_senders, *config_senders, *output_receivers, *message_receivers)
            await self._net.exec_coros(self._net.terminate())
            
        return main(), output_vals

    def execute(self, *args, config={}, signals=set(), ports_to_get:List[PortID]|None=None, **kwargs):
        """Note: this method cannot be run from within an event loop."""
        exec_coro, output = self._setup_execution_coro(*args, config_vals=config, signals=signals, ports_to_get=ports_to_get, **kwargs)
        asyncio.run(exec_coro)
        return output
    
    async def aexecute(self, *args, config={}, signals=set(), ports_to_get:List[PortID]|None=None, **kwargs):
        exec_coro, output = self._setup_execution_coro(*args, config_vals=config, signals=signals, ports_to_get=ports_to_get, **kwargs)
        await exec_coro
        return output
    
    async def stop(self):
        if self._net is not None:
            if not self._net.states.terminated.get():
                await self._net.terminate()
            self._net = None
