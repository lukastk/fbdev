"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/00_comp/02_base_component.ipynb.

# %% ../../nbs/api/00_comp/02_base_component.ipynb 4
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Type, Any
from inspect import signature

import fbdev
from .._utils import AttrContainer, TaskManager, get_caller_module
from .packet import BasePacket, Packet
from .port import PortType, PortSpec, PortSpecCollection, Port, PortCollection, PortID

# %% auto 0
__all__ = ['BaseComponent']

# %% ../../nbs/api/00_comp/02_base_component.ipynb 6
class BaseComponent(ABC):
    is_factory = False
    
    port_specs = PortSpecCollection(
        PortSpec(PortType.MESSAGE, 'started'),
        PortSpec(PortType.MESSAGE, 'stopped')
    )
    
    def __init_subclass__(cls, inherit_ports=True, **kwargs):
        if inherit_ports and 'port_specs' in cls.__dict__:
            cls.port_specs.update(cls.__bases__[0].port_specs)
        cls.port_specs.make_readonly()
        
        if not cls.is_factory and len(signature(cls.__init__).parameters) > 1:
            raise RuntimeError(f"Invalid signature in {cls.__name__}.__init__. No arguments are allowed after `self` in components, unless it is a component factory. Got {str(signature(cls.__init__))}.")
        
    def __init__(self):
        self._task_manager = TaskManager(self)
        self._ports = PortCollection(self.port_specs)
        self._config = AttrContainer({}, obj_name="Component.config")
        self.__started = False
        self.__start_lock = asyncio.Lock()
        self.__stopped = False
        self.__stop_lock = asyncio.Lock()
        self.__base_constructor_was_called = True
         
    @property
    def ports(self) -> PortCollection: return self._ports
    @property
    def config(self) -> AttrContainer: return self._config
    @property
    def task_manager(self) -> TaskManager: return self._task_manager

    def __check_base_constructor_was_called(self):
        try: return self.__base_constructor_was_called
        except AttributeError: return False

    async def start(self):
        async with self.__start_lock:
            if self.__started: raise RuntimeError(f"Component {self.__class__.__name__} is already started.")
            if not self.__check_base_constructor_was_called():
                raise RuntimeError(f"{BaseComponent.__name__}.__init__() was not called in component {self.__class__.__name__}.")
            if self.__stopped:
                raise RuntimeError(f"Component {self.__class__.__name__} is stopped.")
            if self.is_factory:
                raise RuntimeError(f"Component {self.__class__.__name__} is a component factory.")
            await self.update_config()
            await self.send_message('started')
            await self._post_start()
            self.__started = True
    
    async def _post_start(self):
        """Post-hook for BaseComponent.start"""
        pass
    
    async def stop(self):
        async with self.__stop_lock:
            if self.__stopped: raise RuntimeError(f"Component {self.__class__.__name__} is already stopped.")
            await self._pre_stop()
            await self.task_manager.destroy()
            self.__stopped = True
            await self.send_message('stopped')
        
    async def _pre_stop(self):
        """Pre-hook for BaseComponent.stop"""
        pass
        
    async def update_config(self):
        async def _set_config_task(port):
            packet: BasePacket = await port.get()
            data = await packet.consume()
            self.set_config(port.name, data)
        tasks = []
        for port_name, port in self.ports.config.items():
            if self.port_specs.config[port_name].is_optional:
                if port.put_awaiting.get():
                    await _set_config_task(port)
            else:
                tasks.append(asyncio.create_task(_set_config_task(port)))
        await asyncio.gather(*tasks)
    
    def set_config(self, name:str, value:Any):
        if name not in self.port_specs.config.keys():
            raise ValueError(f"Config port {name} is not a valid config port for component {self.__class__.__name__}.")
        self.config._set(name, value)
        
    async def await_signal(self, name:str):
        packet: BasePacket = await self.ports.signal[name].get()
        await packet.consume()
        
    async def send_message(self, name:str, wait_until_sent=False):
        if wait_until_sent: await self.ports.message[name].put(Packet.get_empty())
        else: self.task_manager.create_task(self.ports.message[name].put(Packet.get_empty()))
    
    @classmethod
    def _create_component_class(cls,
                                component_name=None,
                                class_attrs={},
                                init_args=[],
                                init_kwargs={}) -> Type[BaseComponent]:
        if not cls.is_factory:
            raise ValueError(f"{cls.__name__} is not a component factory.")
        if component_name is None:
            if cls.__name__.endswith("Factory"):
                component_name = cls.__name__[:-len("Factory")]
            else:
                component_name = cls.__name__
        comp_class_attrs = {
            '__init__': lambda self: cls.__init__(self, *init_args, **init_kwargs),
            'parent_factory' : cls,
            **class_attrs,
            'is_factory' : False,
        }
        return type(component_name, (cls,), comp_class_attrs)


    @classmethod
    def create_component(cls, component_name=None) -> Type[BaseComponent]:
        """Creates a new instance of the component class, with the given arguments.
        Overload to modify the behaviour (for example, to allow modification of `port_spec`)
        """
        raise NotImplementedError()
    
    @classmethod
    def set_module(cls, module_import_path=None):
        if module_import_path is None:
            module_import_path = get_caller_module(level=2)
        
        cls.__module__ = module_import_path
