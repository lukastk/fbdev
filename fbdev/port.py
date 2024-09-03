"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/01_port.ipynb.

# %% auto 0
__all__ = ['PortType', 'PortSpec', 'ConfigPortSpec', 'PortTypeSpec', 'PortSpecCollection', 'BasePort', 'InputPort', 'ConfigPort',
           'OutputPort', 'PortCollection']

# %% ../nbs/api/01_port.ipynb 3
import asyncio
from abc import ABC, abstractmethod
from typing import Type, Optional, Callable, Any, Union
from enum import Enum
import inspect

from .utils import AttrContainer
from .packet import Packet

# %% ../nbs/api/01_port.ipynb 6
class PortType(Enum):
    INPUT = ("input", True)
    OUTPUT = ("output", False)
    CONFIG = ("config", True)
    SIGNAL = ("signal", False)
    
    def __init__(self, label, is_input_port):
        self._label = label
        self._is_input_port = is_input_port
        
    @property
    def label(self): return self._label
    @property
    def is_input_port(self): return self._is_input_port
    
    def get(self, port_type_label:str):
        for port_type in self:
            if port_type.label == port_type_label:
                return port_type
        raise RuntimeError(f"Port type {port_type_label} does not exist.")

# %% ../nbs/api/01_port.ipynb 8
class PortSpec:
    def __init__(self, name=None, port_type=None, dtype=None, data_validator=None):
        self._name = name
        self._port_type = port_type
        self._dtype = dtype
        self._data_validator = data_validator
            
    @property
    def name(self): return self._name
    @property
    def port_type(self): return self._port_type
    @property
    def is_input_port(self): return self._port_type.is_input_port
    @property
    def dtype(self): return self._dtype
    @property
    def data_validator(self): return self._data_validator
    
    @property
    def has_dtype(self): return self._dtype is not None
    @property
    def has_data_validator(self): return self._data_validator is not None
    
    def __str__(self) -> str:
        return f"{self.port_type}.{self.name}"
    
    def __repr__(self) -> str:
        return str(self)

    def copy(self):
        port_spec = PortSpec()
        port_spec._name = self._name
        port_spec._port_type = self._port_type
        port_spec._dtype = self._dtype
        port_spec._data_validator = self._data_validator
        return port_spec

# %% ../nbs/api/01_port.ipynb 10
class ConfigPortSpec(PortSpec):
    _NO_DEFAULT = object()  # Sentinel value for no default provided
    
    def __init__(self, name=None, dtype=Optional[Type], data_validator=None, is_optional=False, default=_NO_DEFAULT):
        super().__init__(name, PortType.CONFIG, dtype, data_validator)
        self._is_optional = is_optional
        
        if default != self._NO_DEFAULT:
            self._default = default
            
        if self.is_optional and self.has_default:
            raise RuntimeError("Config port {self.name} cannot have both be optional and have a default value.")
            
    @property
    def name(self): return self._name
    @property
    def dtype(self): return self._dtype
    @property
    def data_validator(self): return self._data_validator
    @property
    def is_optional(self): return self._is_optional
    @property
    def default(self):
        if not self.has_default: raise RuntimeError(f"Config port {self.name} does not have a default value.")
        return self._default
        
    @property
    def has_default(self): return hasattr(self, '_default')

    def copy(self):
        port_spec = ConfigPortSpec(is_optional=self._is_optional)
        port_spec._name = self._name
        port_spec._port_type = self._port_type
        port_spec._dtype = self._dtype
        port_spec._data_validator = self._data_validator
        if hasattr(self, "_default"):
            setattr(port_spec, "_default", self._default)
        return port_spec

# %% ../nbs/api/01_port.ipynb 12
class PortTypeSpec(AttrContainer):
    def __init__(self, **port_specs):
        super().__init__({}, obj_name=type(self).__name__)
        self._port_type = None
        self._is_input_port = None
        for port_name, port_spec in port_specs.items():
            if not isinstance(port_spec, PortSpec):
                raise TypeError(f"{PortSpec.__name__} {port_name} is not of type {PortSpec.__name__}.")
            self._set(port_name, port_spec)
            port_spec._name = port_name
            
    @property
    def port_type(self): return self._port_type
    @property
    def is_input_port(self): return self.port_type.is_input_port
            
    def _initialise(self, port_type):
        self._port_type = port_type
        for port_spec in self.values():
            if port_type != PortType.CONFIG and type(port_spec) == ConfigPortSpec:
                raise ValueError(f"Invalid port spec {ConfigPortSpec.__name__} for port type {port_type}.")
            if port_type == PortType.CONFIG and type(port_spec) != ConfigPortSpec:
                raise ValueError(f"Invalid port spec {port_spec.name} for port type {port_type}.")
            self[port_spec.name]._port_type = port_type
            
    def _add_port(self, port_spec: PortSpec):
        self._set(port_spec.name, port_spec)
        if port_spec._port_type is None:
            port_spec._port_type = self.port_type
        elif port_spec.port_type != self.port_type:
            raise ValueError(f"Port spec {port_spec.name} has port type {port_spec.port_type}, but port type should be {self.port_type}.")
            
    def __str__(self) -> str:
        return f"{self.port_type} : {[port_spec.name for port_spec in self.values()]}"
    
    def __repr__(self) -> str:
        return str(self)

    def copy(self):
        return PortTypeSpec(**dict(self.items()))

# %% ../nbs/api/01_port.ipynb 14
# TODO perhaps should make these immutable, or dataclasses
class PortSpecCollection:
    def __init__(self, input:PortTypeSpec=None, output:PortTypeSpec=None, config:PortTypeSpec=None, signal:PortTypeSpec=None):
        self._input = input or PortTypeSpec()
        self._input._initialise(PortType.INPUT)
        
        self._output = output or PortTypeSpec()
        self._output._initialise(PortType.OUTPUT)
        
        self._config = config or PortTypeSpec()
        self._config._initialise(PortType.CONFIG)
        
        self._signal = signal or PortTypeSpec()
        self._signal._initialise(PortType.SIGNAL)
    
    @property
    def input(self): return self._input
    @property
    def output(self): return self._output
    @property
    def config(self): return self._config
    @property
    def signal(self): return self._signal
    
    def __iter__(self):
        return iter([self.input, self.output, self.config, self.signal])
    
    def __getitem__(self, key:Union[str, PortType]):
        if type(key) == PortType:
            key = key.label
        return getattr(self, key)
    
    def __contains__(self, key):
        port_type, port_name = key
        return port_name in getattr(self, port_type.label)
    
    def get_port_names(self):
        keys = set()
        for port_type_spec in self:
            for port_name, port_spec in port_type_spec.items():
                keys.add((port_type_spec.name, port_name))
        return keys
    
    def iter_ports(self):
        for port_type_spec in self:
            for port_name, port_spec in port_type_spec.items():
                yield port_spec
    
    def __str__(self) -> str:
        lines = []
        for port_type_spec in self:
            lines.append(f"{port_type_spec.port_type}:")
            for port_name, port_spec in port_type_spec.items():
                line = f"  {str(port_spec.name)}"
                if port_spec.dtype is not None: line += f":{port_spec.dtype.__name__}"
                if type(port_spec)==ConfigPortSpec and port_spec.has_default: line += f"={port_spec.default}"
                lines.append(line)
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return str(self)

    def copy(self):
        return PortSpecCollection(
            input=self.input.copy(),
            output=self.output.copy(),
            config=self.config.copy(),
            signal=self.signal.copy()
        )

# %% ../nbs/api/01_port.ipynb 16
class BasePort:
    def __init__(self, port_spec:PortSpec, parent):
        self._name = port_spec.name
        self._port_type = port_spec.port_type
        self._parent = parent
        self._dtype = port_spec.dtype
        self._data_validator = port_spec.data_validator
            
    def _validate_packet_dtype(self, packet):
        if self.dtype is not None:
            if self.dtype != packet.dtype:
                raise TypeError(f"Packet is of type {packet.dtype.__name__}, but should be of type {self.dtype.__name__}.")
            
    async def _validate_packet(self, packet):
        if self.data_validator is not None:
            payload = await packet.consume()
            if not self.data_validator(payload):
                #TODO logging in BasePort._validate_packet_data
                #TODO proper exceptions in BasePort._validate_packet_data
                #TODO unit test BasePort._validate_packet_data
                raise RuntimeError("Packet payload failed data validation.")
            return Packet(payload)
        return packet

    @property
    def name(self): return self._name    
    @property
    def port_type(self): return self._port_type
    @property
    def idx(self): return self._idx
    @property
    def parent(self): return self._parent
    @property
    def dtype(self): return self._dtype
    @property
    def data_validator(self): return self._data_validator
    
    def __str__(self) -> str:
        return f"{self.port_type}.{self.name}"
    
    def __repr__(self) -> str:
        return str(self)

# %% ../nbs/api/01_port.ipynb 18
class InputPort(BasePort):
    def __init__(self, port_spec:PortSpec, parent):
        super().__init__(port_spec, parent)
        self._packet = None
        self._packet_waiting = asyncio.Event() # Set by a Node, when there is an edge waiting to sent to the packet
        self._requesting_packet = asyncio.Event() # Set when the port is requesting a package
        self._received_packet = asyncio.Event() # Set when the port has returned a package to the component process
        
    def _load_packet(self, packet:Packet):
        if not isinstance(packet, Packet):
            raise TypeError(f"Port {self.parent.__class__.__name__}.{self.name} received a non-packet object.")
        if self._packet is not None:
            raise RuntimeError(f"Port {self.parent.__class__.__name__}.{self.name} is already receiving a packet.")
        if not self._requesting_packet.is_set():
            raise RuntimeError(f"Port {self.parent.__class__.__name__}.{self.name} is not requesting a packet.")
        self._packet = packet
        self._received_packet.set()
        
    async def receive(self):
        self._requesting_packet.set()
        await self._received_packet.wait()
        self._requesting_packet.clear()
        self._received_packet.clear()
        packet = self._packet
        self._validate_packet_dtype(packet)
        self._packet = None
        packet = await self._validate_packet(packet)
        return packet
    
    async def receive_payload(self):
        packet = await self.receive()
        return await packet.consume()

# %% ../nbs/api/01_port.ipynb 20
class ConfigPort(InputPort):
    def __init__(self, port_spec:PortSpec, parent):
        super().__init__(port_spec, parent)
        
    async def receive(self):
        raise NotImplementedError("Not available for Config ports.")
    
    async def receive_payload(self):
        raise NotImplementedError("Not available for Config ports.")
    
    async def _receive(self):
        return super().receive()
    
    async def _receive_payload(self):
        return super().receive_payload()

# %% ../nbs/api/01_port.ipynb 22
class OutputPort(BasePort):
    def __init__(self, port_spec:PortSpec, parent):
        super().__init__(port_spec, parent)
        self._packet = None
        self._edge_available = asyncio.Event() # Set by a Node, when there is an edge available for being sent a packet
        self._ready_to_unload = asyncio.Event() # Set when the port is requesting to send out a packet
        self._package_sent = asyncio.Event() # Set when the port has returned a package to the component process
        
    def _unload_packet(self):
        if self._packet is None:
            raise RuntimeError(f"Port {self.parent.__class__.__name__}.{self.name} does not have a packet to send.")
        if not self._ready_to_unload.is_set():
            raise RuntimeError(f"Port {self.parent.__class__.__name__}.{self.name} is not ready to send a packet.")
        packet = self._packet
        self._packet = None
        self._package_sent.set()
        return packet
        
    async def put(self, packet:Packet):
        if not isinstance(packet, Packet): raise TypeError(f"`packet` must be of type {Packet.__name__}.")
        self._validate_packet_dtype(packet)
        packet = await self._validate_packet(packet)
        self._packet = packet
        self._ready_to_unload.set()
        await self._package_sent.wait()
        self._ready_to_unload.clear()
        self._package_sent.clear()
        
    async def put_payload(self, packet_payload):
        packet = Packet(packet_payload)
        await self.put(packet)

# %% ../nbs/api/01_port.ipynb 24
class PortCollection(AttrContainer):
    def __init__(self, port_spec_collection:PortSpecCollection, parent):
        super().__init__({}, obj_name=f"{parent.__class__.__name__}.ports")
        self._parent = parent
        self._port_spec_collection = port_spec_collection
        for port_type_spec in port_spec_collection:
            self._set(port_type_spec.port_type.label, AttrContainer({}, obj_name=f"{parent.__class__.__name__}.{port_type_spec.port_type.label}"))
            self._set(port_type_spec.port_type, self[port_type_spec.port_type.label])
            self._attach_ports(port_type_spec)

    def _attach_ports(self, port_type_spec):
        for port_name, port_spec in port_type_spec.items():
            if port_spec.is_input_port:
                if type(port_spec) == ConfigPortSpec:
                    port = ConfigPort(port_spec, self)
                else:
                    port = InputPort(port_spec, self)
            else: port = OutputPort(port_spec, self)
            self[port_type_spec.port_type.label]._set(port_name, port)
    
    def __iter__(self):
        return iter([self.input, self.output, self.config, self.signal])
    
    def __str__(self) -> str:
        return str(self._port_spec_collection)
    
    def __repr__(self) -> str:
        return str(self)
