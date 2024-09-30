"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/01_graph/03_graph_component.ipynb.

# %% ../../nbs/api/01_graph/03_graph_component.ipynb 4
from __future__ import annotations
import asyncio
from abc import abstractmethod
from types import MappingProxyType
from typing import Type, Tuple, Dict

import fbdev
from ..comp.packet import BasePacket, Packet
from ..comp.port import PortType, PortSpec, PortSpecCollection, PortID
from ..comp.base_component import BaseComponent
from .graph_spec import GraphSpec, NodeSpec
from .packet_registry import TrackedPacket, PacketRegistry
from .net import Edge, Node, Net
from ..exceptions import NodeError, EdgeError

# %% auto 0
__all__ = ['GraphComponentFactory']

# %% ../../nbs/api/01_graph/03_graph_component.ipynb 6
class GraphComponentFactory(BaseComponent):
    is_factory = True
    expose_graph = True
    
    graph: GraphSpec = None
    
    def __init__(self):
        super().__init__()
        self._parent_net: Net = None # Is set by Net in Net.start()
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
            
    @property
    def nodes(self) -> MappingProxyType[str, Node]: return MappingProxyType(self._nodes)
    @property
    def edges(self) -> MappingProxyType[str, Edge]: return MappingProxyType(self._edges)
    
    @property
    def _packet_registry(self) -> PacketRegistry: return self._parent_net._packet_registry
    
    def _handle_node_exception(self, task:asyncio.Task, exception:Exception, source_trace:Tuple):
        try: raise NodeError() from exception
        except NodeError as e: self._task_manager.submit_exception(task, e, source_trace)
    
    def _handle_edge_exception(self, task:asyncio.Task, exception:Exception, source_trace:Tuple):
        try: raise EdgeError() from exception
        except EdgeError as e: self._task_manager.submit_exception(task, e, source_trace)
    
    async def put_packet(self, port_id:PortID, packet:BasePacket):
        await super().put_packet(port_id, packet)
        # Register that the packet is incoming from outside the net
        if not self._packet_registry.is_registered(packet) and self._parent_net:
            packet = TrackedPacket(packet, location=TrackedPacket.EXTERNAL_LOCATION, packet_registry=self._packet_registry)
            self._packet_registry.register_move(packet, origin=TrackedPacket.EXTERNAL_LOCATION, dest=self._parent_net.loc_uuid, via=port_id)
    
    async def get_packet(self, port_id:PortID) -> BasePacket:
        packet = await super().get_packet(port_id)
        # Register that the packet is leaving the net
        if not isinstance(packet, TrackedPacket): raise RuntimeError(f"Got packet '{packet.uuid}' via '{port_id}', that was not of type TrackedPacket.")
        self._packet_registry.register_move(packet, origin=self._parent_net.loc_uuid, dest=TrackedPacket.EXTERNAL_LOCATION, via=port_id)
        return packet
    
    @classmethod
    def create_component(cls, graph, expose_graph=True) -> Type[BaseComponent]:
        graph = graph.copy()
        graph.make_readonly()
        return cls._create_component_class(class_attrs={
            'graph' : graph,
            'expose_graph' : expose_graph,
            'port_specs' : graph._port_specs
        })
        
    async def _post_start(self):
        for node_spec in self.graph.nodes.values():
            self._nodes[node_spec.id] = Node(node_spec, self._parent_net)
            self._nodes[node_spec.id]._task_manager.subscribe(self._handle_node_exception)
        for edge_spec in self.graph.edges.values():
            self._edges[edge_spec.id] = Edge(edge_spec, self._parent_net)
            self._edges[edge_spec.id]._task_manager.subscribe(self._handle_edge_exception)
        
        for node in self._nodes.values():
            await node.start()
        for edge in self.edges.values():
            edge.start()
            
    async def _pre_terminate(self):
        for node in self._nodes.values():
            await node.terminate()
        for edge in self.edges.values():
            await edge.terminate()
