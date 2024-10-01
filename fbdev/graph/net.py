"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/01_graph/02_net.ipynb.

# %% ../../nbs/api/01_graph/02_net.ipynb 4
from __future__ import annotations
import asyncio
from types import MappingProxyType
from typing import Type, Callable, Any, Tuple, Coroutine, List, Dict, NewType
import uuid
import traceback

import fbdev
from .._utils import AttrContainer, TaskManager, StateCollection, StateHandler, await_multiple_events
from ..comp.packet import BasePacket
from ..comp.port import PortType, PortSpec, PortSpecCollection, BasePort, Port, PortCollection, PortID
from ..comp.base_component import BaseComponent
from .packet_registry import LocationUUID
from .graph_spec import GraphSpec, NodeSpec, EdgeSpec
from .packet_registry import TrackedPacket, PacketRegistry
from ..exceptions import ComponentError

# %% auto 0
__all__ = ['Address', 'Edge', 'NodePortCollection', 'Node', 'Net']

# %% ../../nbs/api/01_graph/02_net.ipynb 5
Address = NewType('Address', str)

# %% ../../nbs/api/01_graph/02_net.ipynb 7
location_uuid_entitities: Dict[LocationUUID, Edge|Node] = {}

def get_location_uuid(entity) -> LocationUUID:
    uuid_int = uuid.uuid4().int
    location_uuid_entitities[uuid_int] = entity
    
def lookup_location_uuid(uuid_int:LocationUUID) -> Edge|Node:
    return location_uuid_entitities[uuid_int]

# %% ../../nbs/api/01_graph/02_net.ipynb 9
class Edge():
    _address_delimiter = '|'

    def __init__(self, edge_spec: EdgeSpec, parent_net:Net) -> None:
        self._edge_spec = edge_spec
        self._loc_uuid:LocationUUID = get_location_uuid(self)
        self._parent_net: Net = parent_net
        self._task_manager = TaskManager(self)
        self._edge_in_bus_task: asyncio.Task = None
        self._edge_out_bus_task: asyncio.Task = None
        if edge_spec.maxsize == 0: raise ValueError("Edge maxsize cannot be 0.")
        self._packets = asyncio.Queue(maxsize=edge_spec.maxsize) if edge_spec.maxsize else asyncio.Queue()
        
        self._states:StateCollection = StateCollection()
        self._states._add_state(StateHandler("running", False), readonly=True)
        self._states._add_state(StateHandler("full", False), readonly=True)
        self._states._add_state(StateHandler("empty", True), readonly=True)
        
    @property
    def spec(self) -> EdgeSpec: return self._edge_spec
    @property
    def id(self) -> str: return self._edge_spec.id
    @property
    def states(self): return self._states
    @property
    def loc_uuid(self) -> LocationUUID: return self._loc_uuid
    
    @property
    def _packet_registry(self): return self._parent_net._packet_registry
    
    
    @property
    def tail(self) -> Node:
        if self._edge_spec.tail:
            node_id = Net.NET_ID if type(self._edge_spec.tail) == GraphSpec else self._edge_spec.tail.id
            return self._parent_net.get_node_by_id(node_id)
        else: return None
    @property
    def tail_port(self) -> NodePort:
        if self.tail:
            return self.tail.ports[self._edge_spec._tail_node_port_id]
        else: return None
    
    @property
    def head(self) -> Node:
        if self._edge_spec.head:
            node_id = Net.NET_ID if type(self._edge_spec.head) == GraphSpec else self._edge_spec.head.id
            return self._parent_net.get_node_by_id(node_id)
        else: return None
    @property
    def head_port(self) -> NodePort:
        if self.head:
            return self.head.ports[self._edge_spec._head_node_port_id]
        else: return None
        
    def start(self):
        self._edge_in_bus_task = self._task_manager.create_task(self._edge_in_bus())
        self._edge_out_bus_task = self._task_manager.create_task(self._edge_out_bus())
    
    async def stop(self):
        await self._task_manager.cancel_wait(self._edge_in_bus_task)
        await self._task_manager.cancel_wait(self._edge_out_bus_task)

    async def _edge_in_bus(self):
        packet = None
        if self.tail is None: return # TODO: Allow for attaching the tail and head after creation
        while True:
            try:
                packet_putted = self.tail_port.states.put_awaiting.get_state_event(True)
                edge_non_full = self.states.full.get_state_event(False)
                await await_multiple_events(packet_putted, edge_non_full)
                packet = await self.tail_port._get()
            finally:
                if packet is not None:
                    if not self._packet_registry.is_registered(packet):
                        packet = TrackedPacket(packet, self.tail.loc_uuid, self._packet_registry)
                    self._packet_registry.register_move(packet, origin=self.tail.loc_uuid, dest=self.loc_uuid, via=self.tail_port.id)
                    await self._packets.put(packet)
                    packet = None
                    self.states._empty.set(False)
                    if self._packets.full(): self.states._empty.set(True)

    async def _edge_out_bus(self):
        packet = None
        if self.head is None: return
        while True:
            try:
                packet_getted = self.head_port.states.get_awaiting.get_state_event(True)
                edge_non_empty = self.states.empty.get_state_event(False)
                await await_multiple_events(packet_getted, edge_non_empty)
                packet = await self._packets.get()
            finally:
                if packet is not None:
                    await self.head_port._put(packet)
                    self._packet_registry.register_move(packet, origin=self.loc_uuid, dest=self.head.loc_uuid, via=self.head_port.id) # I think this safely registers the move, as `await port._packet_queue.put(packet)` is the last await in `_put`
                    packet = None
                    self.states._full.set(False)
                    if self._packets.empty(): self.states._empty.set(True)

    @property
    def address(self) -> Address:
        return f"{self._parent_net.address}{Edge._address_delimiter}{self.id}"

# %% ../../nbs/api/01_graph/02_net.ipynb 11
class NodePort(BasePort):
    """Ports in a Node will be converted to NodePorts. This is to facilitate addressing. It's mostly cosmetics."""
    _address_delimiter = ':'
    
    def __init__(self, *, _port:Port, _parent_node: Net):
        self._port = _port
        self._parent_node: Net = _parent_node
    
    @property
    def address(self) -> Address:
        return f"{self._parent_node.address}{NodePort._address_delimiter}{self.port_type}.{self.name}"

    @property
    def spec(self) -> PortSpec: return self._port.spec
    @property
    def name(self) -> str: return self._port.name
    @property
    def id(self) -> str: return self._port.id
    @property
    def port_type(self) -> PortType: return self._port.port_type
    @property
    def dtype(self) -> type: return self._port.dtype
    @property
    def is_input_port(self) -> bool: return self._port.is_input_port
    @property
    def is_output_port(self) -> bool: return not self._port.is_output_port
    @property
    def data_validator(self) -> Callable[[Any], bool]: return self._port.data_validator
    @property
    def states(self) -> StateCollection: return self._port.states
        
    async def _put(self, packet:BasePacket): await self._port._put(packet)
    
    async def _get(self) -> BasePacket: return await self._port._get()

# %% ../../nbs/api/01_graph/02_net.ipynb 13
class NodePortCollection(PortCollection):
    def __init__(self, *, _port_collection:PortCollection, _parent_node:Node):
        self._port_spec_collection: PortSpecCollection = _port_collection._port_spec_collection
        self._ports: Dict[str, NodePort] = {}
        for port_type in PortType:
            setattr(self, port_type.label, AttrContainer({}, obj_name=f"{PortCollection.__name__}.{port_type.label}", dtype=NodePort))
        for port in _port_collection.iter_ports():
            self._ports[port.id] = node_port = NodePort(_port=port, _parent_node=_parent_node)
            getattr(self, port.port_type.label)._set(port.name, node_port)

# %% ../../nbs/api/01_graph/02_net.ipynb 15
class Node:
    NET_ID = 'NET'
    _address_delimiter = '->'
    
    def __init__(self, node_spec: NodeSpec, parent_net:Node|None) -> None:
        self._loc_uuid:LocationUUID = get_location_uuid(self)
        self._node_spec:NodeSpec = node_spec
        self._parent_net:Node = parent_net
        self._task_manager = TaskManager(self)
        
        self._packet_registry: PacketRegistry = None
        if self._parent_net:
            self._packet_registry: PacketRegistry = self._parent_net._packet_registry
        else:
            self._packet_registry = PacketRegistry()
            
        self._component_process = self._node_spec.component_type()
        self._component_process._task_manager.subscribe(self._handle_component_process_exception)
        self._ports = NodePortCollection(_port_collection=self._component_process.ports, _parent_node=self)
        
        self._states:StateCollection = StateCollection()
        self._states._add_state(StateHandler("started", False), readonly=True)
        self._states._add_state(StateHandler("terminated", False), readonly=True)
        
        self.__start_lock = asyncio.Lock()
        self.__terminate_lock = asyncio.Lock()
    
    @property
    def spec(self) -> EdgeSpec: return self._node_spec
    @property
    def id(self) -> str: return self._node_spec.id
    @property
    def states(self): return self._states
    @property
    def ports(self) -> PortCollection: return self._ports
    @property
    def port_specs(self) -> PortSpecCollection: return self.component_type.port_specs
    @property
    def loc_uuid(self) -> LocationUUID: return self._loc_uuid
    
    @property
    def edge_connections(self) -> MappingProxyType[PortID, Edge]:
        edges = {port_id : self._parent_graph.edges[edge_id] for port_id, edge_id in self._edge_connections.items()}
        return MappingProxyType(edges)
    
    @property
    def component_type(self) -> Type[BaseComponent]: return self._node_spec.component_type
    @property
    def component_name(self) -> str: return self._node_spec.component_name
    @property
    def component_process(self) -> BaseComponent: return self._component_process
    
    def _handle_component_process_exception(self, task:asyncio.Task, exception:Exception, source_trace:Tuple):
        try: raise ComponentError() from exception
        except ComponentError as e:
            self._task_manager.submit_exception(task, e, source_trace)
    
    async def start(self):
        async with self.__start_lock:
            if self.states.started.get(): raise RuntimeError("Node is already started.")
            if self.states.terminated.get(): raise RuntimeError("Cannot start an already terminated node.")
            self._component_process._parent_net = self
            await self._component_process.start()
            self.states._started.set(True)
        
    async def terminate(self):
        async with self.__terminate_lock:
            if not self.states.started.get(): raise RuntimeError("Node has not been started yet.")
            if self.states.terminated.get(): raise RuntimeError("Node is already terminated.")
    
    @property
    def address(self) -> Address:
        if self._parent_net:
            return f"{self._parent_net.address}{Node._address_delimiter}{self.id}"
        else: return 'NET'
        
    def get_child_by_address(self, address:Address) -> Node|Edge|NodePort:
        from fbdev.graph._utils.node_lookup_by_address import _get_node_child_by_address
        return _get_node_child_by_address(self, address)

# %% ../../nbs/api/01_graph/02_net.ipynb 16
class Net(Node):
    NET_ID = 'NET'
    
    def __init__(self, node_spec: NodeSpec, parent_net:Node|None=None) -> None:
        if not issubclass(node_spec.component_type, fbdev.graph.graph_component.GraphComponentFactory):
            raise ValueError(f"Net must have a component type that descends from GraphComponentFactory.")
        super().__init__(node_spec, parent_net=parent_net)
    
    @property
    def id(self) -> str:
        if self._parent_net: self._node_spec.id
        return Node.NET_ID
    @property
    def is_top_net(self) -> bool: return self._parent_net is None
    @property
    def is_subnet(self) -> bool: return not self.is_top_net
    
    @property
    def nodes(self) -> MappingProxyType[str, Node]: return self.component_process.nodes
    @property
    def edges(self) -> MappingProxyType[str, Edge]: return self.component_process.edges
    
    def get_node_by_id(self, node_id:str) -> Node|Net:
        if node_id == Net.NET_ID: return self
        else: return self.nodes[node_id]
        
    async def exec_coros(self, *coros: List[Coroutine], print_all_exceptions=True):
        """Run a coroutine and monitor for exceptions in the coroutine, as well as
        any exceptions that occurs in the task manager. Therefore, for it to work
        as expected, the coroutine must be starting tasks using self._task_manager.create_task().
        """
        async def all_coros():
            await asyncio.gather(*[asyncio.create_task(coro) for coro in coros])
        task = asyncio.create_task(all_coros())
        monitor_task = asyncio.create_task(self._task_manager.wait_for_exceptions())
        await asyncio.wait([task, monitor_task], return_when=asyncio.FIRST_COMPLETED)
        exceptions = self._task_manager.get_exceptions()
        if task.done():
            try: await task
            except Exception as e: exceptions.append((task, e, ()))
        if not monitor_task.done():
            monitor_task.cancel()
        
        if print_all_exceptions:
            for i, (task, e, source_trace) in enumerate(exceptions):
                msg = f"Message: {e}\n\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}\n\n"
                msg = "\n".join([f"    {line}" for line in msg.split("\n")])
                print(f"Exception {i+1} ({e.__class__.__name__}):")
                print(msg)
                
        for task, e, source_trace in exceptions:
            raise e
