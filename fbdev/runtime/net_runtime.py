"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/02_runtime/00_net_runtime.ipynb.

# %% ../../nbs/api/02_runtime/00_net_runtime.ipynb 4
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from types import MappingProxyType
from typing import Type, Tuple, Dict

import fbdev
from ..exceptions import NodeError, EdgeError
from ..comp.packet import Packet
from ..comp.port import PortType, PortSpec, PortSpecCollection, PortID
from ..comp.base_component import BaseComponent
from ..graph.graph_spec import GraphSpec, NodeSpec
from ..graph.packet_registry import TrackedPacket
from ..graph.net import Edge, Node, Net
from ..graph.graph_component import GraphComponentFactory

# %% auto 0
__all__ = ['NetRuntime']

# %% ../../nbs/api/02_runtime/00_net_runtime.ipynb 6
class NetRuntime(ABC):
    @classmethod
    def from_graph(cls, graph:GraphSpec):
        component_type = GraphComponentFactory.create_component(graph)
        net_spec = NodeSpec(component_type)
        net = Net(net_spec)
        return cls(net)
    
    @classmethod
    def from_component(cls, component:Type[BaseComponent]):
        if not issubclass(component, GraphComponentFactory):
            graph = GraphSpec()
            
        component_type = GraphComponentFactory.create_component(graph)
        net_spec = NodeSpec(component_type)
        net = Net(net_spec)
        return cls(net)
    
    @classmethod
    def execute_graph(cls, graph:GraphSpec, *args, config_vals={}, **kwargs):
        with cls.from_graph(graph) as netrun:
            return netrun.execute(*args, config_vals, **kwargs)
    
    @classmethod
    async def aexecute_graph(cls, graph:GraphSpec, *args, config_vals={}, **kwargs):
        async with cls.from_graph(graph) as netrun:
            return await netrun.aexecute(*args, config=config_vals, **kwargs)
    
    @abstractmethod
    def execute(self, *args, config={}, **kwargs): ...
    
    @abstractmethod
    async def aexecute(self, *args, config_vals={}, **kwargs): ...
    
    @abstractmethod
    async def stop(self): ...
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        asyncio.run(self.stop())
