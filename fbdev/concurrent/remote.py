"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/03_concurrent/01_remote.ipynb.

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 4
from __future__ import annotations
import asyncio
from enum import Enum
from types import MappingProxyType
from typing import Type, Callable, Any, Tuple, Coroutine, List, Dict, Hashable, Set
import uuid
import traceback
from multiprocessing import Pipe
from multiprocessing.connection import Connection, Client, Listener
import uuid
import inspect
from abc import ABC, abstractmethod
import os, sys, time
import subprocess
from dataclasses import dataclass
import secrets

import fbdev
from .._utils import StateCollection, StateHandler, AttrContainer, TaskManager, EventCollection, EventHandler, find_available_port
from ..exceptions import NodeError
from ..comp.packet import BasePacket, Packet
from ..comp.port import PortType, PortSpec, PortSpecCollection, BasePort, Port, PortCollection, PortID
from ..comp.base_component import BaseComponent
from ..graph.packet_registry import LocationUUID
from ..graph.graph_spec import GraphSpec, NodeSpec, EdgeSpec
from ..graph.packet_registry import TrackedPacket, PacketRegistry
from ..graph.net import BaseNode, Node, NodePort, Edge, BaseNodePort

# %% auto 0
__all__ = ['RemoteController', 'get_client', 'ProxyEvent', 'ProxyEventMediator', 'ProxyStateHandler', 'ProxyStateHandlerMediator',
           'ProxyPort', 'ProxyPortMediator', 'ProxyPortCollection', 'start_subprocess_node_worker', 'RemoteNodeError',
           'ProxyNode', 'ProxyNodeMediator']

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 6
class RemoteController:
    DO = 0
    DO_SUCCESSFUL = 1
    READY = 2
        
    @dataclass(frozen=True)
    class Package:
        msg: int
        handle: Hashable = None
        routine_key: Hashable = None
        comm_id: int = None
        args: Tuple = None
        kwargs: Dict = None
        val: Any = None
        
        @property
        def msg_str(self):
            return {
                RemoteController.DO : 'DO',
                RemoteController.DO_SUCCESSFUL : 'DO_SUCCESSFUL',
                RemoteController.REMOTE_ROUTINES : 'REMOTE_ROUTINES',
            }[self.msg]
    
    def __init__(self, conn:Connection, task_manager:TaskManager, **routines_by_handle:Dict[Hashable, Coroutine|Callable]):
        self._conn:Connection = conn
        self._task_manager = task_manager
        self._routines_by_handle = routines_by_handle
        self._remote_routines = None
        self._send_tickets: Dict[int, asyncio.Queue] = {}
        self._receiver_task = self._task_manager.create_task(self._receiver())
        self._sender_task = None
        self._closed = False
        self._remote_is_ready_event = asyncio.Event()
        self._send_queue = asyncio.Queue()
        self._send_queue_is_empty_event = asyncio.Event()
        self._send_queue_is_empty_event.set()
        self._sent_ready = False
        
    def add_routine(self, handle:Hashable, routine_key:Hashable, routine:Coroutine|Callable):
        if handle not in self._routines_by_handle:
            self._routines_by_handle[handle] = {}
        if routine_key in self._routines_by_handle[handle]:
            raise ValueError(f"Routine '{routine_key}' already exists in handle '{handle}'")
        self._routines_by_handle[handle][routine_key] = routine
        
    @property
    def closed(self) -> bool: return self._conn.closed or self._closed
    
    async def await_ready(self):
        if not self._sent_ready:
            raise RuntimeError("Need to call RemoteController.send_ready() before RemoteController.await_ready()")
        await self._remote_is_ready_event.wait()
        self._sender_task = self._task_manager.create_task(self._sender())
        
    async def await_empty(self):
        return await self._send_queue_is_empty_event.wait()
        
    def send_ready(self):
        self._conn.send(self.Package(msg=self.READY))
        self._sent_ready = True
    
    async def _receiver(self):
        try:
            loop = asyncio.get_running_loop()
            while True:
                await asyncio.sleep(0)                    
                try:
                    pkg = await loop.run_in_executor(None, self._conn.recv)
                except ConnectionError:
                    self._closed = True
                    break
                except OSError:
                    self._closed = True
                    break
                except EOFError:
                    self._closed = True
                    break
                
                if pkg.msg == self.DO:
                    if not self._sent_ready: raise RuntimeError("RemoteController is not ready")
                    if pkg.val is not None: raise RuntimeError("Unexpected return value in DO:", pkg.val)
                    self._task_manager.create_task(
                        self._do_request(pkg.handle, pkg.routine_key, pkg.comm_id, pkg.args, pkg.kwargs)
                    )
                elif pkg.msg == self.DO_SUCCESSFUL:
                    if not self._sent_ready: raise RuntimeError("RemoteController is not ready")
                    if pkg.args is not None: raise RuntimeError("Unexpected args in DO_SUCCESSFUL:", pkg.args)
                    if pkg.kwargs is not None: raise RuntimeError("Unexpected kwargs in DO_SUCCESSFUL:", pkg.kwargs)
                    self._do_request_successful(pkg.handle, pkg.routine_key, pkg.comm_id, pkg.val)
                elif pkg.msg == self.READY:
                    if self._remote_is_ready_event.is_set(): raise RuntimeError("Remote is already ready")
                    self._remote_is_ready_event.set()
                else:
                    raise RuntimeError(f"Unexpected message: {pkg.msg_str}")
        except Exception as e:
            print(e)
            raise
    
    async def _sender(self):
        while True:
            pkg = await self._send_queue.get()
            if self._send_queue.empty():
                self._send_queue_is_empty_event.set()
            try:
                self._conn.send(pkg)
            except ConnectionError:
                self._closed = True
                continue
            except OSError:
                self._closed = True
                continue
            except EOFError:
                self._closed = True
                continue
    
    async def _do_request(self, handle, routine_key, comm_id, args, kwargs):
        if self.closed: raise RuntimeError("RemoteController is closed")
        if handle not in self._routines_by_handle:
            raise RuntimeError(f"Handle '{handle}' is not a remote handle")
        if routine_key not in self._routines_by_handle[handle]:
            raise RuntimeError(f"Routine '{routine_key}' is not a remote routine")
        func = self._routines_by_handle[handle][routine_key]
        if asyncio.iscoroutinefunction(func):
            val = await func(*args, **kwargs)
        else:
            val = func(*args, **kwargs)
        pkg = self.Package(msg=self.DO_SUCCESSFUL, handle=handle, routine_key=routine_key, comm_id=comm_id, val=val)
        await self._send_queue.put(pkg)
    
    def _do_request_successful(self, handle, routine_key, comm_id, val):
        if self.closed:
            raise RuntimeError(f"RemoteController is closed. handle='{handle}' routine_key='{routine_key}'")
        self._send_tickets[comm_id].put_nowait(val)
    
    async def do(self, handle:Hashable, routine_key:Hashable, *args, **kwargs):
        if self.closed:
            raise RuntimeError("RemoteController is closed")
        comm_id = uuid.uuid4().hex
        self._send_tickets[comm_id] = asyncio.Queue()
        pkg = self.Package(msg=self.DO, handle=handle, routine_key=routine_key, comm_id=comm_id, args=args, kwargs=kwargs)
        self._send_queue_is_empty_event.clear()
        await self._send_queue.put(pkg)
        val = await self._send_tickets[comm_id].get()
        del self._send_tickets[comm_id]
        return val
    
    def sync_do(self, handle:Hashable, routine_key:Hashable, *args, **kwargs):
        if self.closed:
            return
            #raise RuntimeError("RemoteController is closed")
        comm_id = uuid.uuid4().hex
        self._send_tickets[comm_id] = asyncio.Queue()
        pkg = self.Package(msg=self.DO, handle=handle, routine_key=routine_key, comm_id=comm_id, args=args, kwargs=kwargs)
        self._send_queue_is_empty_event.clear()
        self._send_queue.put_nowait(pkg)
        
    class RemoteHandleController:
        def __init__(self, *, _remote:RemoteController, _handle:Hashable):
            self._remote = _remote
            self._handle = _handle
        def add_routine(self, routine_key:Hashable, routine:Coroutine|Callable):
            self._remote.add_routine(self._handle, routine_key, routine)
        async def do(self, routine_key:Hashable, *args, **kwargs):
            return await self._remote.do(self._handle, routine_key, *args, **kwargs)
        def sync_do(self, routine_key:Hashable, *args, **kwargs):
            self._remote.sync_do(self._handle, routine_key, *args, **kwargs)
        
    def get_handle_remote(self, handle:Hashable):
        return self.RemoteHandleController(_remote=self, _handle=handle)

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 8
def get_client(address, authkey, max_retries=20, retry_delay=0.2):
    for _ in range(max_retries):
        try:
            client = Client(address, authkey=authkey)
            break
        except ConnectionError:
            time.sleep(retry_delay)
    if client is None:
        raise ConnectionError("Failed to connect to server")
    return client

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 11
class ProxyEvent:
    def __init__(self, handle:str, remote:RemoteController):
        self._handle = handle
        self._event = asyncio.Event()
        self._handle_remote = remote.get_handle_remote(self._handle)
        self._handle_remote.add_routine('remote_set', self._remote_set)
        self._handle_remote.add_routine('remote_clear', self._remote_clear)
            
    async def wait(self):
        await self._event.wait()
    
    def is_set(self):
        return self._event.is_set()
    
    def set(self): self._handle_remote.sync_do('set')
    def clear(self): self._handle_remote.sync_do('clear')
    
    def _remote_set(self): self._event.set()
    def _remote_clear(self): self._event.clear()
        
class ProxyEventMediator:
    """ProxyEventMediator._clear will have to be called manually if the event is set and cleared on the remote side."""
    def __init__(self, handle:str, remote:RemoteController, task_manager:TaskManager, event:asyncio.Event):
        self._handle = handle
        self._event = event
        self._task_manager = task_manager
        
        self._handle_remote = remote.get_handle_remote(self._handle)
        remote.add_routine(self._handle, 'set', self._set)
        remote.add_routine(self._handle, 'clear', self._clear)
        
        self._monitor_task = self._task_manager.create_task(self._monitor())
        
        if self._event.is_set():
            self._handle_remote.sync_do('remote_set')
        
    async def _monitor(self):
        await self._event.wait()
        await self._handle_remote.do('remote_set')
        self._monitor_task = None
            
    def _set(self): self._event.set()
    def _clear(self):
        if self._event.is_set():
            self._event.clear()
            self._monitor_task = self._task_manager.create_task(self._monitor_task())

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 13
class ProxyStateHandler(StateHandler):
    def __init__(self, name:str, parent_handle:Hashable, remote:RemoteController):
        self._name = name
        self._handle = (parent_handle, name)
        self._initialised = asyncio.Event()
        
        self._handle_remote = remote.get_handle_remote(self._handle)
        self._handle_remote.add_routine('synchronise', self._synchronise)
        
    async def await_initialised(self):
        await self._initialised.wait()
        
    def __first_synchronisation(self, state_dict):
        state_vals = list(state_dict.keys())
        current_state = [state for state in state_vals if state_dict[state]][0]
        StateHandler.__init__(self, self._name, current_state, state_vals)
        self._initialised.set()
        
    def __get_state_dict(self):
        return {s : e.is_set() for s, e in self._state_is_on.items()}
        
    def _synchronise(self, state_dict):
        if sum(list(state_dict.values())) != 1: raise ValueError("`state_dict` must have exactly one True value.")
        if not self._initialised.is_set(): self.__first_synchronisation(state_dict)
        for state, state_val in state_dict.items():
            if state_val: self.set(state)
            
    def set(self, state):
        if not self._initialised.is_set(): raise RuntimeError("`set` must be called after the first synchronisation.")
        old_state = self.get()
        super().set(state)
        if old_state != state:
            self._handle_remote.sync_do('synchronise', self.__get_state_dict())
        
    def wait(self, state, target_value=True):
        if not self._initialised.is_set(): raise RuntimeError("`wait` must be called after the first synchronisation.")
        return super().wait(state, target_value)
    
    def get_state_event(self, state, target_value=True):
        if not self._initialised.is_set(): raise RuntimeError("`get_state_event` must be called after the first synchronisation.")
        return super().get_state_event(state, target_value)
    
    def get_state_toggle_event(self, state=True, target_value=True):
        if not self._initialised.is_set(): raise RuntimeError("`get_state_toggle_event` must be called after the first synchronisation.")
        return super().get_state_toggle_event(state, target_value)
    
    def get_state_changed_event(self):
        if not self._initialised.is_set(): raise RuntimeError("`get_state_changed_event` must be called after the first synchronisation.")
        return super().get_state_changed_event()
    
class ProxyStateHandlerMediator:
    def __init__(self, parent_handle:Hashable, remote:RemoteController, task_manager:TaskManager, state_handler:StateHandler):
        self._remote = remote
        self._task_manager = task_manager
        self._state_handler = state_handler
        self._handle = (parent_handle, self._state_handler.name)
        self._monitor_task = self._task_manager.create_task(self._monitor())
        
        self._handle_remote = remote.get_handle_remote(self._handle)
        self._handle_remote.add_routine('synchronise', self._synchronise)
        
        self._handle_remote.sync_do('synchronise', self.__get_state_dict())
        
    async def _monitor(self):
        changed_event = self._state_handler.get_state_changed_event()
        while True:
            await changed_event.wait()
            changed_event = self._state_handler.get_state_changed_event()
            self._handle_remote.sync_do('synchronise', self.__get_state_dict())
        
    def _synchronise(self, state_dict):
        if sum(list(state_dict.values())) != 1: raise ValueError("`state_dict` must have exactly one True value.")
        for state, state_val in state_dict.items():
            if state_val: self._state_handler.set(state)
        
    def __get_state_dict(self):
        return {s : e.is_set() for s, e in self._state_handler._state_is_on.items()}
    
    def _set(self, state):
        self._state_handler.set(state)

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 15
class ProxyPort(BaseNodePort):
    def __init__(self, parent_handle:Hashable, remote:RemoteController, task_manager:TaskManager, port_spec:PortSpec, parent_node:Node):
        self._handle = (parent_handle, port_spec.port_type.label, port_spec.name)
        self._parent_node = parent_node
        self._port_spec = port_spec
        self._task_manager = task_manager
        self._remote_handler = remote.get_handle_remote(self._handle) # Not actually used for anything
        
        self._states = StateCollection()
        
        self._states._add_state(ProxyStateHandler("is_blocked", self._handle, remote))
        self._states._add_state(ProxyStateHandler("put_awaiting", self._handle, remote))
        self._states._add_state(ProxyStateHandler("get_awaiting", self._handle, remote))
        
        self._events = None # TODO: ProxyPort.events
        
        super().__init__()
        
    async def await_initialised(self):
        await asyncio.gather(*[state.await_initialised() for state in self._states.values() if type(state) == ProxyStateHandler])
        
    @property
    def spec(self) -> PortSpec: return self._port_spec
    @property
    def name(self) -> str: return self.spec.name
    @property
    def id(self) -> str: return self.spec.id
    @property
    def port_type(self) -> PortType: return self.spec.port_type
    @property
    def dtype(self) -> type: return self.spec.dtype
    @property
    def is_input_port(self) -> bool: return self.spec.is_input_port
    @property
    def is_output_port(self) -> bool: return self.spec.is_output_port
    @property
    def data_validator(self) -> Callable[[Any], bool]: return self.spec.data_validator
    @property
    def states(self) -> StateCollection: return self._states
    @property
    def events(self) -> EventCollection: raise NotImplementedError("TODO")
    @property
    def parent_node(self) -> BaseNode: return self._parent_node
    @property
    def packet_registry(self) -> PacketRegistry: return self._parent_node._packet_registry
        
    async def _put(self, packet:BasePacket):
        await self._remote_handler.do('parent_put', packet)
    
    async def _get(self):
        packet = await self._remote_handler.do('parent_get')
        return packet
    
    async def _put_from_external(self, packet:BasePacket):
        await NodePort._put_from_external(self, packet)
        
    async def _get_to_external(self) -> TrackedPacket:
        return await NodePort._get_to_external(self)
    
    async def _put_value_from_external(self, val:Any):
        await NodePort._put_value_from_external(self, val)
        
    async def _get_and_consume_to_external(self) -> Any:
        return await NodePort._get_and_consume_to_external(self)
        
#|export
class ProxyPortMediator:
    def __init__(self, parent_handle:Hashable, remote:RemoteController, task_manager:TaskManager, port:Port):
        self._handle = (parent_handle, port.port_type.label, port.name)
        self._port = port
        self._task_manager = task_manager
        
        self._remote_handler = remote.get_handle_remote(self._handle)
        self._remote_handler.add_routine('parent_put', self._parent_put)
        self._remote_handler.add_routine('parent_get', self._parent_get)
        
        self._proxy_state_handler_mediators = [
            ProxyStateHandlerMediator(self._handle, remote, task_manager, state)
            for state in self._port.states.values()
            if type(state) == StateHandler
        ]

    async def _parent_put(self, packet:BasePacket):
        await self._port._put(packet)
        
    async def _parent_get(self):
        return await self._port._get()

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 17
class ProxyPortCollection(PortCollection):
    def __init__(self, port_spec_collection:PortSpecCollection, parent_node:Node, parent_handle:Hashable, remote:RemoteController, task_manager:TaskManager):
        self._port_spec_collection: PortSpecCollection = port_spec_collection
        self._ports: Dict[str, Port] = {}
        for port_type in PortType:
            setattr(self, port_type.label, AttrContainer({}, obj_name=f"{ProxyPortCollection.__name__}.{port_type.label}"))
        for port_spec in port_spec_collection.iter_ports():
            self._add_port(ProxyPort(parent_handle, remote, task_manager, port_spec, parent_node))

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 19
def start_subprocess_node_worker(node_spec:NodeSpec, port_num:int, authkey:bytes):
    launch_script = f"""
from fbdev.concurrent.subprocess_node_launcher import subprocess_node_worker
# Don't think we need this import. Just keeping the comment for now...
#from {node_spec.component_type.__module__} import {node_spec.component_type.__name__}
subprocess_node_worker({port_num}, {authkey})
""".strip()
    proc = subprocess.Popen([sys.executable, '-c', launch_script])
    return proc

# %% ../../nbs/api/03_concurrent/01_remote.ipynb 20
class RemoteNodeError(NodeError): pass

class ProxyNode(BaseNode):
    def __init__(self, node_spec: NodeSpec, parent_net:BaseNode|None=None):
        super().__init__(node_spec, parent_net)
        self._packet_registry: PacketRegistry = None
        if self._parent_net:
            self._packet_registry: PacketRegistry = self._parent_net._packet_registry
        else:
            self._packet_registry = PacketRegistry()
            
        self.__start_lock = asyncio.Lock()
        self.__terminate_lock = asyncio.Lock()
        
        self._handle = ('main', self.spec.component_name)
        self._remote_port_num = find_available_port()
        self._remote_address = 'localhost'
        self._remote_authkey = secrets.token_bytes(32)
        
        self._node_proc = start_subprocess_node_worker(self.spec, self._remote_port_num, self._remote_authkey)
        self._remote_conn = get_client((self._remote_address, self._remote_port_num), authkey=self._remote_authkey)
        
        self._remote = RemoteController(self._remote_conn, self._task_manager)
        self._remote.add_routine('main', 'submit_exception_from_remote', self._submit_exception_from_remote)
        self._remote_handler = self._remote.get_handle_remote(self._handle)
        self._remote.send_ready()
        
        self._states:StateCollection = StateCollection()
        self._states._add_state(ProxyStateHandler("started", self._handle, self._remote))
        self._states._add_state(ProxyStateHandler("stopped", self._handle, self._remote))
        
        self._port_proxies = ProxyPortCollection(self.component_type.port_specs, self, self._handle, self._remote, self._task_manager)
        
        self._remote.sync_do('main', 'create_node', self.spec)
        
    async def await_initialised(self):
        await asyncio.gather(*[port.await_initialised() for port in self.ports.iter_ports()])
    
    @property
    def states(self): return self._states
    @property
    def ports(self) -> PortCollection: return self._port_proxies
    @property
    def edge_connections(self) -> MappingProxyType[PortID, Edge]: ...
    @property
    def component_process(self) -> BaseComponent:
        raise RuntimeError(f"{self.__class__.__name__} does not have a component_process.")
    @property
    def packet_registry(self) -> PacketRegistry: return self._packet_registry
    
    def _submit_exception_from_remote(self, task_str:str, exceptions:Tuple[Exception, ...], source_trace:Tuple, tracebacks:Tuple[str, ...]):
        try:
            raise RemoteNodeError() from exceptions[0]
        except RemoteNodeError as e:
            self.task_manager.submit_exception(task_str, exceptions + (e,), source_trace, tracebacks)
    
    async def start(self):
        async with self.__start_lock:
            await self._remote.await_ready()
            await self._remote.do('main', 'await_node_created')
            await self.await_initialised()
            await self._remote_handler.do('start_node')
        
    async def stop(self):
        async with self.__terminate_lock:
            await self._remote_handler.do('stop_node')
            await self.states.stopped.wait(True)
            await self._remote.await_empty()
            await self._remote.do('main', 'close_connection')
            self._remote_conn.close()
            self._node_proc.communicate()
                
class ProxyNodeMediator:
    def __init__(self, parent_handle:Hashable, remote:RemoteController, task_manager:TaskManager, node:Node):
        self._handle = (parent_handle, node.component_name)
        self._node = node
        self._task_manager = task_manager
        
        self._remote_handler = remote.get_handle_remote(self._handle)
        self._remote_handler.add_routine('start_node', self._start_node)
        self._remote_handler.add_routine('stop_node', self._stop_node)
        
        self._proxy_state_handler_mediators = [
            ProxyStateHandlerMediator(self._handle, remote, task_manager, state)
            for state in self._node.states.values()
            if type(state) == StateHandler
        ]
        
        self._proxy_port_mediators = [
            ProxyPortMediator(self._handle, remote, task_manager, port)
            for port in self._node.ports.iter_ports()
        ]
        
    async def _start_node(self):
        await self._node.start()

    async def _stop_node(self):
        await self._node.stop()
