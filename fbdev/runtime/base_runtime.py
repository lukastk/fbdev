"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/02_runtime/00_base_runtime.ipynb.

# %% ../../nbs/api/02_runtime/00_base_runtime.ipynb 4
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Type, Dict

import fbdev
from ..comp.port import PortSpecCollection
from ..comp.base_component import BaseComponent
from ..graph.graph_spec import GraphSpec, NodeSpec
from ..graph.graph_component import GraphComponentFactory

# %% auto 0
__all__ = ['BaseRuntime']

# %% ../../nbs/api/02_runtime/00_base_runtime.ipynb 6
class BaseRuntime(ABC):
    def __init__(self):
        self._started = False
        self._stopped = False
    
    @property
    def started(self) -> bool: return self._started
    @property
    def stopped(self) -> bool: return self._stopped
    
    @classmethod
    def from_graph(cls, graph:GraphSpec, *args, **kwargs):
        component_type = GraphComponentFactory.create_component(graph)
        node_spec = NodeSpec(component_type)
        node = node_spec.create_node()
        return cls(node, *args, **kwargs)
    
    @classmethod
    def from_component(cls, component:Type[BaseComponent], prefix_ports_with_node_id=False, *args, **kwargs):
        graph = GraphSpec(PortSpecCollection(), inherit_base_component_ports=False)
        graph.add_node(component)
        graph.add_and_connect_unconnected_child_ports(prefix_with_node_id=prefix_ports_with_node_id, exclude_port_types=[])
        return cls.from_graph(graph, *args, **kwargs)
    
    @classmethod
    def execute_graph(cls, graph:GraphSpec, *args, config_vals={}, **kwargs):
        with cls.from_graph(graph) as run:
            return run.execute(*args, config_vals, **kwargs)
    
    @classmethod
    async def aexecute_graph(cls, graph:GraphSpec, *args, config_vals={}, **kwargs):
        async with cls.from_graph(graph) as run:
            return await run.aexecute(*args, config=config_vals, **kwargs)
    
    @abstractmethod
    def start(self):
        if self._started: raise RuntimeError("{self.__class__.__name__} has already been started.")
        if self._stopped: raise RuntimeError("{self.__class__.__name__} has been stopped.")
    
    @abstractmethod
    async def astart(self):
        if self._started: raise RuntimeError("{self.__class__.__name__} has already been started.")
        if self._stopped: raise RuntimeError("{self.__class__.__name__} has been stopped.")
    
    @abstractmethod
    async def stop(self):
        if not self._started: raise RuntimeError(f"{self.__class__.__name__} has not yet been started.")
        if self._stopped: raise RuntimeError("{self.__class__.__name__} has already been stopped.")
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if not self.stopped:
            await self.stop()
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        asyncio.run(self.stop())