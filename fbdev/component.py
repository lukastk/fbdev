"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/02_component.ipynb.

# %% auto 0
__all__ = ['BaseComponent', 'ComponentFactory', 'FunctionComponentFactory', 'func_component']

# %% ../nbs/api/02_component.ipynb 4
import asyncio
from abc import ABC, abstractmethod
import typing
from typing import Type, Optional, Callable, Any, Union, Tuple
from enum import Enum
import inspect

from .utils import AttrContainer, create_task_with_exception_handler
from .packet import Packet
from .port import PortType, PortSpec, ConfigPortSpec, PortTypeSpec, PortSpecCollection, BasePort, InputPort, ConfigPort, OutputPort, PortCollection

# %% ../nbs/api/02_component.ipynb 7
class BaseComponent(ABC):
    port_specs = PortSpecCollection(
        input=PortTypeSpec(),
        output=PortTypeSpec(),
        config=PortTypeSpec(),
        signal=PortTypeSpec(),
    )
    
    parent_factory = None
    is_factory = False

    def __init_subclass__(cls, **kwargs):
        """Prevents any subclass from defining an __init__ that accepts any argument other than 'self'."""
        super().__init_subclass__(**kwargs)
        init_method = cls.__dict__.get('__init__', None)
        if init_method:
            from inspect import signature
            sig = signature(init_method)
            params = tuple([p.name for p in sig.parameters.values()])
            if params != ('self',):
                raise TypeError(f"{cls.__name__}.__init__() must only accept 'self' as an argument.")
    
    def __init__(self):
        self.ports = PortCollection(self.port_specs, self)
        self.config = AttrContainer({}, obj_name="Component.config")
        for config_port_name, config_port_spec in self.port_specs.config.items():
            if config_port_spec.has_default:
                self.set_config(config_port_name, config_port_spec.default)
                    
    async def set_config(self, name:str, packet:Packet):
        value = await packet.consume()
        if self.port_specs.config[name].has_dtype and type(value) != self.port_specs.config[name].dtype:
            raise TypeError(f"Config value {value} is not of type {self.port_specs.config[name].dtype}, in config port {name}.")
        if self.port_specs.config[name].has_data_validator and not self.port_specs.config[name].data_validator(value):
            raise ValueError(f"Config value {value} is not valid for config port {name}, in config port {name}.")
        if name not in self.port_specs.config.keys():
            raise ValueError(f"Config port {name} is not a valid config port for component {self.__class__.__name__}.")
        self.config._set(name, value)
        
    def check_configured(self) -> bool:
        configured = True
        for config_port_name, config_port_spec in self.port_specs.config.items():
           if not config_port_name in self.config and not config_port_spec.is_optional:
               configured = False
               break
        return configured
    
    @classmethod
    def is_from_factory(cls):
        return cls.parent_factory is not None
    
    @abstractmethod
    async def execute(self):
        pass
    
    async def start_background_tasks(self):
        pass
    
    async def stop_background_tasks(self):
        pass
    
    async def destroy(self):
        pass
    
    def __del__(self):
        loop = asyncio.get_event_loop()
        if loop.is_running(): create_task_with_exception_handler(self.destroy())
        else: loop.run_until_complete(self.destroy())

# %% ../nbs/api/02_component.ipynb 10
class ComponentFactory(BaseComponent):
    is_factory = True
    
    def __init_subclass__(cls, **kwargs):
        """Overloads `BaseComponent.__init_subclass__`, to allow ComponentFactory subclasses to have constructors with arguments."""
        pass

    @classmethod
    def _create_component_class(cls, component_name=None, class_attrs={}, init_args=[], init_kwargs={}):
        if component_name is None:
            if cls.__name__.endswith("Factory"):
                component_name = cls.__name__[:-len("Factory")]
            else:
                component_name = cls.__name__
        return type(component_name, (cls,), {
            '__init__': lambda self: cls.__init__(self, *init_args, **init_kwargs),
            'parent_factory' : cls,
            'is_factory' : False,
            **class_attrs
        })

    @classmethod
    def get_component(cls, *init_args, **init_kwargs):
        """Creates a new instance of the component class, with the given arguments.
        Overload to modify the behaviour (for example, to allow modification of `port_spec`)
        """
        return cls._create_component_class()

# %% ../nbs/api/02_component.ipynb 13
class FunctionComponentFactory(ComponentFactory):
    def __init__(self, func):
        self._func = func
        super().__init__()
        
    @classmethod
    def get_component(cls, func, component_name=None):
        if component_name is None: component_name = func.__name__
        
        input_ports = {}
        config_ports = {}
        
        # Input and config ports
        signature = inspect.signature(func)
        for param in signature.parameters.values():
            port_name = param.name
            if isinstance(param.annotation, PortSpec):
                port_spec = param.annotation
                port_spec.name = port_name
                port_spec._port_type = PortType.CONFIG if type(param.annotation) == ConfigPortSpec else PortType.INPUT
                if port_spec.port_type == PortType.CONFIG:
                    if port_spec.has_default and param.default != inspect.Parameter.empty:
                        raise ValueError(f"Config port {port_name} is supplied multiple default values.")
            elif type(param.annotation) == type:
                if param.default != inspect.Parameter.empty:
                    port_spec = ConfigPortSpec(port_name, dtype=param.annotation, default=param.default)
                else:
                    port_spec = PortSpec(port_name, port_type=PortType.INPUT, dtype=param.annotation)
            elif param.annotation == inspect.Parameter.empty:
                if param.default != inspect.Parameter.empty:
                    port_spec = ConfigPortSpec(port_name, default=param.default)
                else:
                    port_spec = PortSpec(port_name, port_type=PortType.INPUT)
            else:
                raise ValueError(f"Unsupported annotation {param.annotation}")
            
            if port_spec.port_type == PortType.CONFIG: config_ports[port_name] = port_spec
            elif port_spec.port_type == PortType.INPUT: input_ports[port_name] = port_spec
        
        # Output ports
        if type(signature.return_annotation) == PortTypeSpec:
            output_ports = signature.return_annotation
        elif typing.get_origin(signature.return_annotation) == tuple:
            output_ports = PortTypeSpec(**{
                f'out{i}' : PortSpec(port_type=PortType.OUTPUT, dtype=t)
                for i, t in enumerate(typing.get_args(signature.return_annotation))
            })
        elif signature.return_annotation == inspect.Parameter.empty:
            output_ports = PortTypeSpec(out=PortSpec(port_type=PortType.OUTPUT))
        elif type(signature.return_annotation) == type:
            output_ports = PortTypeSpec(out=PortSpec(port_type=PortType.OUTPUT, dtype=signature.return_annotation))
        elif signature.return_annotation == None:
            output_ports = PortTypeSpec()
        else:
            raise ValueError(f"Unsupported return annotation {signature.return_annotation}")
        
        port_specs = PortSpecCollection(
            input=PortTypeSpec(**input_ports),
            config=PortTypeSpec(**config_ports),
            output=output_ports
        )
        
        return cls._create_component_class(component_name=component_name, class_attrs={'port_specs':port_specs}, init_args=[func])
    
    async def execute(self):
        kwargs = {}
        for port_name, port in self.ports.input.items():
            packet = await port.receive()
            packet_payload = await packet.consume()
            kwargs[port_name] = packet_payload
        for config_name, config_value in self.ports.config.items():
            kwargs[config_name] = config_value
            
        output = self._func(**kwargs)
        
        if len(self.ports.output) == 1:
            await self.ports.output.out.put(Packet(output))
        elif len(self.ports.output) > 1:
            if type(output) == tuple or type(output) == list:
                for output_i, port_i in zip(output, self.ports.output.values()):
                    await port_i.put(Packet(output_i))
            elif type(output) == dict:
                for output_key, output_val in output.items():
                    await self.ports.output[output_key].put(Packet(output_val))
            else:
                raise RuntimeError(f"Unsupported output type {type(output)}.")
    
    

# %% ../nbs/api/02_component.ipynb 14
def func_component(name=None):
    def decorator(func):
        return FunctionComponentFactory.get_component(func, name)
    return decorator
