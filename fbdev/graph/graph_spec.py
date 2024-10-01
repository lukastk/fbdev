"""TODO fill in description"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/01_graph/00_graph_spec.ipynb.

# %% ../../nbs/api/01_graph/00_graph_spec.ipynb 4
from __future__ import annotations
from types import MappingProxyType
from typing import Type, Optional, Union, Dict, List
from fastcore.basics import patch_to
from IPython.display import Markdown

import fbdev
from .._utils import is_valid_name
from ..comp.port import PortType, PortSpec, PortSpecCollection, PortID
from ..comp.base_component import BaseComponent

# %% auto 0
__all__ = ['EdgeSpec', 'NodeSpec', 'GraphSpec']

# %% ../../nbs/api/01_graph/00_graph_spec.ipynb 6
class EdgeSpec:
    def __init__(self, *,
                 _id:str,
                 _maxsize:int,
                 _parent_graph:GraphSpec):
        self._id:str = _id
        if _maxsize == 0: raise ValueError("Edge maxsize cannot be 0.")
        self.maxsize = _maxsize
        self._parent_graph:GraphSpec = _parent_graph
        self._tail_node_id:str|None = None
        self._tail_node_port_id:PortID|None = None
        self._head_node_id:str|None = None
        self._head_node_port_id:PortID|None = None
        
    @property
    def id(self) -> str: return self._id
    @property
    def rich_id(self) -> str:
        return f"Edge[{self._id}, maxsize={self.maxsize if self.is_maxsize_finite else '∞'}]"
    
    @property
    def tail(self) -> NodeSpec|GraphSpec|None:
        if self._parent_graph is None: raise ValueError("Edge does not have a parent graph.")
        elif self._tail_node_id is not None: 
            return self._parent_graph.get_node_by_id(self._tail_node_id)
        else: return None
    @property
    def tail_port(self) -> NodePortSpec|None:
        return self.tail.ports[self._tail_node_port_id]
    @property
    def head(self) -> NodeSpec|GraphSpec|None:
        if self._parent_graph is None: raise ValueError("Edge does not have a parent graph.")
        elif self._head_node_id is not None: 
            return self._parent_graph.get_node_by_id(self._head_node_id)
        else: return None
    @property
    def head_port(self) -> NodePortSpec|None:
        return self.head.ports[self._head_node_port_id]
    
    @property
    def tail_is_graph(self) -> bool: return isinstance(self.tail, GraphSpec)
    @property
    def head_is_graph(self) -> bool: return isinstance(self.head, GraphSpec)
    
    @property
    def is_maxsize_finite(self) -> bool:
        return self.maxsize is not None
    
    def __repr__(self) -> str:
        _head_conn = "_" if self._head_node_id is None else f"{self._head_node_id}:{self.head_port.id_str}"
        _tail_conn = "_" if self._tail_node_id is None else f"{self._tail_node_id }:{self.tail_port.id_str}"
        if not self.is_maxsize_finite:
            _edge_spec_label = f"EdgeSpec[{self.id}]"
        else:
            _edge_spec_label = f"EdgeSpec[{self.id}, maxsize={self.maxsize}]"
        return f"{_edge_spec_label}: {_tail_conn} >> {_head_conn}"
    
    def __rshift__(self, other:NodePortSpec|NodeSpec):
        if type(other) == NodePortSpec or type(other) == NodeSpec:
            other << self
            return other
        else:
            raise TypeError(f"Argument `other` must be a NodePortSpec or NodeSpec. Got '{type(other)}'.")
    
    def __lshift__(self, other:NodePortSpec|NodeSpec):
        if type(other) == NodePortSpec or type(other) == NodeSpec:
            other >> self
            return other
        else:
            raise TypeError(f"Argument `other` must be a NodePortSpec or NodeSpec. Got '{type(other)}'.")

# %% ../../nbs/api/01_graph/00_graph_spec.ipynb 8
class NodePortSpec(PortSpec):
    """PortSpecs in a NodeSpec and GraphSpec will be converted NodePortSpecs. This is to allow the `>>` and `<<` operator overloading
    for less verbose graph creation."""
    def __init__(self, *,
                 _port_spec:PortSpec,
                 _parent_node:Union[NodeSpec, GraphSpec]):
        if _port_spec.has_default:
            super().__init__(
                _port_spec.port_type, 
                _port_spec.name,
                _port_spec.dtype,
                _port_spec.data_validator,
                _port_spec.is_optional,
                _port_spec.default,
            )
        else:
            super().__init__(
                _port_spec.port_type, 
                _port_spec.name,
                _port_spec.dtype,
                _port_spec.data_validator,
                _port_spec.is_optional,
            )
        self._parent_node: Union[NodeSpec, GraphSpec] = _parent_node
        
    @property
    def _is_graph_port(self) -> bool:
        return type(self._parent_node) == GraphSpec
    
    @property
    def _graph(self):
        if self._is_graph_port: return self._parent_node
        else: return self._parent_node._parent_graph
        
    @property
    def _parent_id(self):
        if self._is_graph_port: return GraphSpec.GRAPH_ID
        else: return self._parent_node.id
        
    @property
    def _connects_to_head(self) -> bool:
        if self._is_graph_port: return not self.is_input_port
        else: return self.is_input_port
    @property
    def _connects_to_tail(self) -> bool:
        return not self._connects_to_head

    def connect_to(self, other:NodePortSpec|EdgeSpec):
        if type(other) == NodePortSpec:
            if self._graph != other._graph: raise ValueError(f"Nodes must be connected to nodes in the same graph.")
            edge = self._graph.add_edge()
            self._graph.connect_port_to_edge(self, edge)
            self._graph.connect_port_to_edge(other, edge)
        elif type(other) == EdgeSpec:
            self._graph.connect_port_to_edge(self, other)
        else: raise TypeError(f"Argument `other` must be a NodePortSpec or EdgeSpec. Got '{type(other)}'.")
        
    def __str__(self) -> str:
        _parent_id = self._parent_node.id if type(self._parent_node) == NodeSpec else GraphSpec.GRAPH_ID
        return f"{_parent_id}:{self.port_type.label}.{self.name}"
        
    def __rshift__(self, other:NodePortSpec|EdgeSpec):
        if not self._connects_to_tail: raise ValueError(f"Wrong direction of connection for input port.")
        self.connect_to(other)
        return other
    
    def __lshift__(self, other):
        if not self._connects_to_head: raise ValueError(f"Wrong direction of connection for output port.")
        self.connect_to(other)
        return other
    
    

# %% ../../nbs/api/01_graph/00_graph_spec.ipynb 10
class NodeSpec:
    def __init__(self, 
                 component_type:Type[BaseComponent],
                 parent_graph:GraphSpec=None,
                 id:str=None):
        self._id = id
        self._component_type = component_type
        self._parent_graph = parent_graph
        self._edge_connections: Dict[PortID, str] = {}
        
    @property
    def id(self) -> str: return self._id
    @property
    def rich_id(self) -> str:
        if self.id is None: _id = GraphSpec.GRAPH_ID
        elif self.id==self.component_name: _id = ""
        elif self.id.startswith(self.component_name): _id = "..." + self.id[len(self.component_name):]
        else: _id = self.id
        return f"{self.component_name}[{_id}]"
    
    @property
    def edge_connections(self) -> MappingProxyType[PortID, EdgeSpec]:
        edges = {port_id : self._parent_graph.edges[edge_id] for port_id, edge_id in self._edge_connections.items()}
        return MappingProxyType(edges)
    
    @property
    def component_type(self) -> Type[BaseComponent]: return self._component_type
    @property
    def component_name(self) -> str: return self._component_type.__name__
    
    @property
    def contains_graph(self) -> bool:
        if isinstance(self._component_type, fbdev.graph.GraphComponentFactory):
            return self._component_type.expose_graph
        else: return False
    
    @property
    def ports(self) -> PortSpecCollection:
        _port_spec_collections = PortSpecCollection(
            *[NodePortSpec(_port_spec=port_spec, _parent_node=self) for port_spec in self._component_type.port_specs.iter_ports()]
        )
        _port_spec_collections.make_readonly()
        return _port_spec_collections
    
    @property
    def contains_graph(self) -> bool:
        if issubclass(self._component_type, fbdev.graph.GraphComponentFactory):
            return self._component_type.expose_graph
        else: return False
    @property
    def subgraph(self) -> GraphSpec:
        if not self.contains_graph: raise ValueError(f"Node '{self.rich_id}' is not a subgraph.")
        return self.component_type.graph
    
    def __rshift__(self, other:NodePortSpec|EdgeSpec|NodeSpec):
        if len(self.ports.output) != 1: raise ValueError(f"Cannot use `>>` operator on node '{self.rich_id}' with more than one output port.")
        port_spec = list(self.ports.output.values())[0]
        if type(other) == NodePortSpec or type(other) == EdgeSpec:
            port_spec >> other
        elif type(other) == NodeSpec:
            if len(other.ports.input) != 1: raise ValueError(f"Cannot use `>>` operator on node '{other.rich_id}' with more than one input port.")
            inp_port_spec = list(other.ports.input.values())[0]
            port_spec >> inp_port_spec
        return other
    
    def __lshift__(self, other:NodePortSpec|EdgeSpec|NodeSpec):
        if len(self.ports.input) != 1: raise ValueError(f"Cannot use `<<` operator on node '{self.rich_id}' with more than one input port.")
        port_spec = list(self.ports.input.values())[0]
        other >> port_spec
        return other

# %% ../../nbs/api/01_graph/00_graph_spec.ipynb 12
class GraphSpec:
    GRAPH_ID = 'GRAPH'
    
    def __init__(self, port_spec_collection:PortSpecCollection):
        self._readonly:bool = False
        self._nodes: Dict[str, NodeSpec] = {}
        self._edges: Dict[str, EdgeSpec] = {}
        self._port_specs = port_spec_collection.copy()
        self._edge_connections: Dict[PortID, str] = {} # These are for internal edges. That is, connections between the graph ports and its child edges.
    
    @property
    def ports(self) -> PortSpecCollection:
        _ports = [NodePortSpec(_port_spec=port_spec, _parent_node=self) for port_spec in self._port_specs.iter_ports()]
        _port_spec_collection = PortSpecCollection(*_ports)
        _port_spec_collection.make_readonly()
        return _port_spec_collection
    
    @property
    def nodes(self) -> MappingProxyType[str, NodeSpec]: return MappingProxyType(self._nodes)
    @property
    def edges(self) -> MappingProxyType[str, EdgeSpec]: return MappingProxyType(self._edges)
    
    def add_graph_port(self, port_spec:PortSpec) -> NodePortSpec:
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        self._port_specs.add_port(port_spec)
        return self.ports[port_spec.id]
        
    def remove_graph_port(self, port_spec:PortSpec):
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        self._port_specs.remove_port(port_spec)
        
    def update_graph_ports(self, port_spec_collection:PortSpecCollection):
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        self._port_specs.update(port_spec_collection)
    
    def add_and_connect_unconnected_child_ports(self,
                                                exclude_port_types:List[PortType]=[PortType.MESSAGE, PortType.SIGNAL],
                                                prefix_with_node_id:bool=True):
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        for node in self.nodes.values():
            unconnected_ports = [port_id for port_id in node.ports if (port_id not in node.edge_connections) and (port_id[0] not in exclude_port_types)]
            for port_id in unconnected_ports:
                port_type, port_name = port_id
                port_name = f"{node.id}.{port_name}" if prefix_with_node_id else port_name
                graph_port = self.add_graph_port(PortSpec(port_type, port_name))
                graph_port.connect_to(node.ports[port_id])
    
    def get_node_by_id(self, node_id:str) -> NodeSpec:
        if node_id == GraphSpec.GRAPH_ID: return self
        else: return self._nodes[node_id]
    
    def add_node(self, component_type:Type[BaseComponent], id:Optional[str]=None) -> NodeSpec:
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        if id is None:
            num_comps = len([node for node in self._nodes.values() if node.component_type == component_type])
            id = component_type.__name__ + str(num_comps) if num_comps else component_type.__name__
        if id in self._nodes: raise ValueError(f"Node with id {id} already exists")
        if type(id) != str: raise TypeError(f"Node id must be a string, got {type(id)}")
        if id == GraphSpec.GRAPH_ID: raise ValueError(f"Node id '{id}' is reserved for the graph itself.")
        if not is_valid_name(id): raise ValueError(f"'{id}' is not a valid Node id.")
        node = NodeSpec(component_type=component_type, parent_graph=self, id=id)
        self._nodes[str(id)] = node
        return node
    
    def add_edge(self, maxsize:Optional[int]=None, id:Optional[str]=None) -> EdgeSpec:
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        if id is None:
            id = f'edge{str(len(self._edges))}'
        if id in self._edges: raise ValueError(f"Node with id {id} already exists")
        if type(id) != str: raise TypeError(f"Node id must be a string, got {type(id)}")
        if not is_valid_name(id): raise ValueError(f"'{id}' is not a valid Edge id.")
        edge = EdgeSpec(_id=id, _maxsize=maxsize, _parent_graph=self)
        self._edges[str(id)] = edge
        return edge
    
    def connect_port_to_edge(self, port_spec:NodePortSpec|str, edge:EdgeSpec|str):
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        node = self.__get_node(port_spec._parent_node)
        edge = self.__get_edge(edge)
        
        # Input ports of the graph always connect directly to input ports of its child nodes
        # and vice versa for output ports.
        if isinstance(node, GraphSpec): is_tail_connection = port_spec.is_input_port
        else: is_tail_connection = port_spec.is_output_port
        
        if is_tail_connection and edge._tail_node_id is not None:
            raise ValueError(f"Edge '{edge.id}' already has a tail connection.")
        elif (not is_tail_connection) and edge._head_node_id is not None:
            raise ValueError(f"Edge '{edge.id}' already has a head connection.")
        
        node._edge_connections[(port_spec.port_type, port_spec.name)] = edge.id
        node_id = node.id if isinstance(node, NodeSpec) else self.GRAPH_ID
        if is_tail_connection:
            edge._tail_node_id = node_id
            edge._tail_node_port_id = (port_spec.port_type, port_spec.name)
        else:
            edge._head_node_id = node_id
            edge._head_node_port_id = (port_spec.port_type, port_spec.name)
        
    def disconnect_port_from_edge(self, port_spec:NodePortSpec|str, edge:EdgeSpec|str):
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        node = self.__get_node(port_spec._parent_node)
        edge = self.__get_edge(edge)
        
        is_tail_connection = port_spec.is_output_port
        if is_tail_connection and edge._tail_id is None:
            raise ValueError(f"Edge '{edge.id}' does not have a tail connection.")
        elif (not is_tail_connection) and edge._head_id is None:
            raise ValueError(f"Edge '{edge.id}' does not have a head connection.")
        
        del node._edge_connections[(port_spec.port_type, port_spec.name)]
        if is_tail_connection:
            edge._tail_id = None
            edge._tail_node_port_id = None
        else:
            edge._head_id = None
            edge._head_node_port_id = None
    
    def remove_node(self, node:str|NodeSpec):
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        node = self.__get_node(node)
        for (port_type, port_name), edge_id in node._edge_connections.items():
            self.disconnect_node_and_edge(node, port_type, port_name, edge_id)
        del self._nodes[node.id]
        
    def remove_edge(self, edge:str|EdgeSpec):
        if self._readonly: raise RuntimeError("GraphSpec is readonly.")
        edge = self.__get_edge(edge)
        if edge._tail_node_id is not None:
            self.__remove_edge_helper(edge._tail_node_id)
        if edge._head_node_id is not None:
            self.__remove_edge_helper(edge._head_node_id)
        
    def __remove_edge_helper(self, edge:EdgeSpec, node_id:str):
        node = self.get_node_by_id(node_id)
        for (port_type, port_name), edge_id in node._edge_connections.items():
            if edge_id == edge.id:
                found_match = True
                break
        if found_match:
            self.disconnect_node_and_edge(node, port_type, port_name, edge_id)
        else:
            raise ValueError(f"Edge '{edge.id}' is not connected to node '{node.rich_id}'.")
    
    def __get_node(self, node:str|NodeSpec|GraphSpec) -> NodeSpec:
        if type(node) == NodeSpec:
            if node not in self._nodes.values(): raise ValueError(f"Node '{node.id}' does not exist in graph.")
        elif type(node) == GraphSpec:
            pass
        elif type(node) == str:
            node = self.get_node_by_id(node)
        else:
            raise TypeError(f"Argument `node` of incorrect type. Got '{type(node)}'.")
        return node
    
    def __get_edge(self, edge:str|EdgeSpec) -> EdgeSpec:
        if type(edge) != EdgeSpec:
            if type(edge) == str:
                edge = self._edges[edge]
            else: raise TypeError(f"Argument `edge` must be a string or EdgeSpec. Got '{type(edge)}'.")
        else:
            if edge not in self._edges.values(): raise ValueError(f"Edge '{edge.id}' does not exist in graph.")
        return edge

    def make_readonly(self): self._readonly = True
    
    def copy(self) -> GraphSpec:
        graph = GraphSpec(self._port_specs)
        for node in self._nodes.values():
            graph.add_node(node.component_type, id=node.id)
        for edge in self._edges.values():
            graph.add_edge(edge.maxsize, id=edge.id)
        for node in self._nodes.values():
            for port_id, edge in node.edge_connections.items():
                _node_port = graph.get_node_by_id(node.id).ports[port_id]
                _edge = graph.edges[edge.id]
                graph.connect_port_to_edge(_node_port, _edge)
        for port_id, edge_id in self._edge_connections.items():
            graph.connect_port_to_edge(graph.ports[port_id], edge_id)
        return graph

# %% ../../nbs/api/01_graph/00_graph_spec.ipynb 14
@patch_to(GraphSpec)
def to_mermaid(self,
               orientation:str='',
               hide_unconnected_ports:bool=False,
               hide_port_types:List[PortType]=[]) -> str:
    from fbdev.graph._utils.graph_spec_to_mermaid import graph_to_mermaid
    return graph_to_mermaid(self, orientation, hide_unconnected_ports, hide_port_types)

# %% ../../nbs/api/01_graph/00_graph_spec.ipynb 16
@patch_to(GraphSpec)
def display_mermaid(self,
                    orientation:str='',
                    hide_unconnected_ports:bool=False,
                    hide_port_types:List[PortType]=[]) -> str:
    return Markdown(f"```mermaid\n{self.to_mermaid(orientation, hide_unconnected_ports, hide_port_types)}\n```")
