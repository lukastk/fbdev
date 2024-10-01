"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/03_complib/01_func_component_factory.ipynb.

# %% auto 0
__all__ = ['FunctionComponentFactory', 'func_component']

# %% ../../nbs/api/03_complib/01_func_component_factory.ipynb 4
import asyncio
import inspect
import typing
from typing import Callable, Any

import fbdev
from ..comp.packet import Packet
from ..comp.port import PortType, PortSpec, PortSpecCollection
from ..comp.base_component import BaseComponent
from . import ExecComponent

# %% ../../nbs/api/03_complib/01_func_component_factory.ipynb 7
class FunctionComponentFactory(ExecComponent):
    is_factory = True
    _func: Callable = None
        
    @classmethod
    def get_component(cls, func, component_name=None, component_options={}):
        if component_name is None: component_name = func.__name__
        
        port_specs = []
        
        # Input and config ports
        signature = inspect.signature(func)
        for param in signature.parameters.values():
            port_name = param.name
            if isinstance(param.annotation, PortSpec):
                port_spec = param.annotations
                if port_spec.name is None:
                    port_spec._name = port_name
                if port_name != port_spec.name:
                    raise ValueError(f"Mismatch in argument and port name ('{port_name}' and '{port_spec.name}' respectively).")
                if param.default != inspect.Parameter.empty:
                    raise ValueError(f"Cannot specify default value in PortSpec {port_name}, and also a default value in the function argument.")
            else:
                port_dtype = param.annotation if param.annotation != inspect.Parameter.empty else None
                if param.default != inspect.Parameter.empty:
                    port_spec = PortSpec(PortType.CONFIG, port_name, dtype=port_dtype, default=param.default)
                else:
                    port_spec = PortSpec(PortType.INPUT, port_name, dtype=port_dtype)
            if port_spec.is_output_port: raise ValueError(f"Port spec '{port_spec}' is an output port.")
            port_specs.append(port_spec)
        
        # Output ports
        if type(signature.return_annotation) == tuple:
            if not all(isinstance(e, PortSpec) for e in signature.return_annotation):
                raise ValueError("Poorly formatted return annotation. If the return annotation is of type tuple, then all its elements must be PortSpecs.")
            if any(port_spec.is_input_port for port_spec in signature.return_annotation):
                raise ValueError("Provided input PortSpec in return annotation.")
            port_specs += list(signature.return_annotation)
        elif typing.get_origin(signature.return_annotation) == tuple:
            dtypes = [dtype for dtype in typing.get_args(signature.return_annotation) if dtype != Any]
            port_specs += [
                PortSpec(PortType.OUTPUT, f'out{i}', dtype=t) for i,t in enumerate(dtypes)
            ]
        elif signature.return_annotation == inspect.Parameter.empty:
            port_specs.append(PortSpec(PortType.OUTPUT, 'out'))
        elif signature.return_annotation == None:
            pass # No output ports
        else:
            dtype = signature.return_annotation if signature.return_annotation != Any else None
            port_specs.append(PortSpec(PortType.OUTPUT, 'out', dtype=dtype))
        
        return cls._create_component_class(
            component_name=component_name,
            class_attrs={
                'port_specs' : PortSpecCollection(*port_specs),
                '_func' : func,
                **component_options,
            },
        )
    
    async def _execute(self):
        kwargs = {}
        for port in self.ports.input.values():
            packet = await port.get()
            packet_payload = await packet.consume()
            kwargs[port.name] = packet_payload
        for config_name, config_value in self.ports.config.items():
            kwargs[config_name] = config_value
        
        if inspect.iscoroutinefunction(self.__class__._func):
            output = await self.__class__._func(**kwargs)
        else:
            output = self.__class__._func(**kwargs)

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

# %% ../../nbs/api/03_complib/01_func_component_factory.ipynb 8
def func_component(name=None, **component_options):
    def decorator(func):
        return FunctionComponentFactory.get_component(func, name, component_options)
    return decorator
