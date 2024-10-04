"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/00_comp/00_packet.ipynb.

# %% ../../nbs/api/00_comp/00_packet.ipynb 4
from __future__ import annotations
from typing import Any, Type
from datetime import datetime
from datetime import datetime, timezone
from abc import ABC, abstractmethod
import uuid

import fbdev
from .._utils import SingletonMeta

# %% auto 0
__all__ = ['PacketUUID', 'BasePacket', 'Packet']

# %% ../../nbs/api/00_comp/00_packet.ipynb 5
PacketUUID = int

# %% ../../nbs/api/00_comp/00_packet.ipynb 7
class BasePacket(ABC):
    @property
    def is_empty(self): return self._dtype == 'EmptyPayload'
    
    @property
    @abstractmethod
    def uuid(self) -> PacketUUID: ...
    @property
    @abstractmethod
    def creation_timestamp(self) -> datetime: ...
    @property
    @abstractmethod
    def dtype(self) -> Type: ...
    @property
    @abstractmethod
    def is_consumed(self) -> bool: ...
    
    @abstractmethod
    async def consume(self): ...
    
    @abstractmethod
    async def peek(self): ...
    
    @classmethod
    @abstractmethod
    def get_empty(cls) -> BasePacket: ...

# %% ../../nbs/api/00_comp/00_packet.ipynb 9
class Packet(BasePacket):
    def __init__(self, data:Any):
        self._uuid:PacketUUID = uuid.uuid4().int
        self._creation_timestamp:datetime = datetime.now(timezone.utc)
        self._data:Any = data
        self._dtype:type = type(data)
        self._is_consumed:bool = False
            
    @property
    def uuid(self) -> PacketUUID: return self._uuid
    @property
    def creation_timestamp(self) -> datetime: return self._creation_timestamp
    @property
    def dtype(self) -> Type: return self._dtype
    @property
    def is_consumed(self) -> bool: return self._is_consumed
    
    async def consume(self):
        if self._is_consumed: raise RuntimeError("Packet is already consumed.")
        self._is_consumed = True
        return self._data
    
    async def peek(self):
        if self._is_consumed: raise RuntimeError("Packet is already consumed.")
        return self._data
    
    @classmethod
    def get_empty(cls) -> Packet:
        packet = cls(None)
        packet._dtype = 'EmptyPayload'
        return packet
