"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/03_concurrent/00_multiprocessing.ipynb.

# %% ../../nbs/api/03_concurrent/00_multiprocessing.ipynb 4
from __future__ import annotations
import asyncio
from enum import Enum
from types import MappingProxyType
from typing import Type, Callable, Any, Tuple, Coroutine, List, Dict, NewType
import uuid
import traceback
import multiprocessing
from multiprocessing import Pipe
import uuid

import fbdev
from .._utils import AttrContainer, TaskManager, StateCollection, StateHandler, await_multiple_events
from ..exceptions import ComponentError
from ..comp.packet import BasePacket, Packet
from ..comp.port import PortType, PortSpec, PortSpecCollection, BasePort, Port, PortCollection, PortID
from ..comp.base_component import BaseComponent
from ..graph.packet_registry import LocationUUID
from ..graph.graph_spec import GraphSpec, NodeSpec, EdgeSpec
from ..graph.packet_registry import TrackedPacket, PacketRegistry
from ..graph.net import Node

# %% auto 0
__all__ = ['ProxyPortMessages', 'ProxyPort', 'RemotePortHandler']

# %% ../../nbs/api/03_concurrent/00_multiprocessing.ipynb 6
class ProxyPortMessages(Enum):
    PUT = 1
    PUT_SUCCESSFUL = 2
    GET = 3
    GET_SUCCESSFUL = 4

# %% ../../nbs/api/03_concurrent/00_multiprocessing.ipynb 8
class ProxyPort(BasePort):
    def __init__(self, port_spec:PortSpec, conn:Pipe):
        self._port_spec = port_spec
        self._conn = conn
        self._awaiting_puts:Dict[int, asyncio.Event] = {}
        self._awaiting_gets:Dict[int, asyncio.Queue] = {}
        self._monitor_task:asyncio.Task = None
        
        self._states = StateCollection()
        self._states._add_state(StateHandler("is_blocked", False)) # If input port, it's blocked if the component is currently getting. If output port, it's blocked if the component is currently putting.
        self._states._add_state(StateHandler("put_awaiting", False))
        self._states._add_state(StateHandler("get_awaiting", False))
        
        self._packet_queue = asyncio.Queue(maxsize=1)
        self._num_waiting_gets = 0
        self._num_waiting_puts = 0
        
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

    async def run(self):
        try:
            loop = asyncio.get_running_loop()
            while True:
                msg, packet, comm_id = await loop.run_in_executor(None, self._conn.recv)
                if msg == ProxyPortMessages.PUT_SUCCESSFUL:
                    self._awaiting_puts[comm_id].set()
                elif msg == ProxyPortMessages.GET_SUCCESSFUL:
                    await self._awaiting_gets[comm_id].put(packet)
                else:
                    raise RuntimeError(f"Unexpected message: {msg}")
        finally:
            self._conn.close()

    async def _put(self, packet:BasePacket):
        self._num_waiting_puts += 1
        if self.is_output_port: self.states._is_blocked.set(True)
        self.states._put_awaiting.set(True)
        loop = asyncio.get_running_loop()
        comm_id = uuid.uuid4().int
        self._awaiting_puts[comm_id] = asyncio.Event()
        self._conn.send((ProxyPortMessages.PUT, packet, comm_id))
        await self._awaiting_puts[comm_id].wait()
        del self._awaiting_puts[comm_id]
        self._num_waiting_puts -= 1
        if self._num_waiting_puts == 0:
            self.states._put_awaiting.set(False)
            if self.is_output_port: self.states._is_blocked.set(False)
    
    async def _get(self):
        if self.is_input_port: self.states._is_blocked.set(True)
        self._num_waiting_gets += 1
        self.states._get_awaiting.set(True)
        loop = asyncio.get_running_loop()
        comm_id = uuid.uuid4().int
        self._awaiting_gets[comm_id] = asyncio.Queue()
        self._conn.send((ProxyPortMessages.GET, None, comm_id))
        self._num_waiting_gets -= 1
        if self._num_waiting_gets == 0:
            self.states._get_awaiting.set(False)
            if self.is_input_port: self.states._is_blocked.set(False)
        packet = await self._awaiting_gets[comm_id].get()
        del self._awaiting_gets[comm_id]
        return packet

# %% ../../nbs/api/03_concurrent/00_multiprocessing.ipynb 10
class RemotePortHandler:
    def __init__(self, port:Port, conn:Pipe):
        self._port = port
        self._conn = conn
        self._monitor_task:asyncio.Task = None
        
    async def run(self):
        try:
            loop = asyncio.get_running_loop()
            while True:
                msg, packet, comm_id = await loop.run_in_executor(None, self._conn.recv)
                if msg == ProxyPortMessages.PUT:
                    asyncio.create_task(self._packet_putter(packet, comm_id))
                elif msg == ProxyPortMessages.GET:
                    asyncio.create_task(self._packet_getter(comm_id))
                else:
                    raise RuntimeError(f"Unexpected message: {msg}")
        finally:
            self._conn.close()
        
    async def _packet_putter(self, packet:BasePacket, comm_id:int):
        await self._port._put(packet)
        self._conn.send((ProxyPortMessages.PUT_SUCCESSFUL, None, comm_id))
        
    async def _packet_getter(self, comm_id:int):
        packet = await self._port._get()
        self._conn.send((ProxyPortMessages.GET_SUCCESSFUL, packet, comm_id))
