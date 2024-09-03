# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/03_graph.ipynb.

# %% auto 0
__all__ = ['EdgeSpec', 'NodeSpec', 'Graph', 'ReadonlyGraph']

# %% ../nbs/api/03_graph.ipynb 3
from dataclasses import dataclass, replace
from typing import Type, Optional, Union, Any
from collections.abc import Hashable
from types import MappingProxyType
from enum import Enum
import copy

import fbdev
from .utils import AttrContainer
from .port import PortType, PortSpec, PortTypeSpec, PortSpecCollection
from .component import BaseComponent

# %% ../nbs/api/03_graph.ipynb 6
@dataclass(frozen=True)
class EdgeSpec:
    pass

# %% ../nbs/api/03_graph.ipynb 7
class EdgeSpec:
    def __init__(self,
                 maxsize:int=None):
        self._id = None
        self.maxsize = maxsize
        
    @property
    def id(self): return self._id
    
    def copy(self):
        copy = copy.copy(self)
        return copy

# %% ../nbs/api/03_graph.ipynb 9
class NodeSpec:
    def __init__(self, component_type:Type[BaseComponent]):
        self._id = None
        self._component_type = component_type
        
    @property
    def id(self): return self._id
    @property
    def component_type(self): return self._component_type
    @property
    def port_specs(self): return self._component_type.port_specs
    
    def copy(self):
        copy = copy.copy(self)
        copy._component_type = self._component_type
        return copy

# %% ../nbs/api/03_graph.ipynb 12
class Graph:
    GRAPH_ID=0
    
    def __init__(self, port_spec_collection:PortSpecCollection):
        self._port_specs = port_spec_collection
        self._edges = {}
        self._nodes = {}
        self._head_connections = {}
        self._tail_connections = {}
        self._edge_to_head_connections = {}
        self._edge_to_tail_connections = {}
        
    @property
    def component_type(self): raise RuntimeError("Graphs do not have a component type.")
    @property
    def port_specs(self): return self._port_specs
    @property
    def internal_port_connections(self): return self._internal_port_connections
    @property
    def nodes(self): return MappingProxyType(self._nodes)
    @property
    def edges(self): return MappingProxyType(self._edges)
    @property
    def head_connections(self): return MappingProxyType(self._head_connections)
    @property
    def tail_connections(self): return MappingProxyType(self._tail_connections)
    @property
    def graph_head_connections(self):
        return MappingProxyType({k[1:]:v for k,v in self.head_connections.items() if k[0] == self.GRAPH_ID})
    @property
    def graph_tail_connections(self):
        return MappingProxyType({k[1:]:v for k,v in self.tail_connections.items() if k[0] == self.GRAPH_ID})
    @property
    def edge_to_head_connections(self): return MappingProxyType(self._edge_to_head_connections)
    @property
    def edge_to_tail_connections(self): return MappingProxyType(self._edge_to_tail_connections)
        
    def add_node(self, node, id=None):
        if id == self.GRAPH_ID: raise RuntimeError("Node id '0' is reserved for the graph itself.")
        if id:
            node._id = id
        else:
            num_twins = sum(1 for _node in self.nodes.values() if _node.component_type == node.component_type)
            if num_twins > 0:
                node._id = f"{node.component_type.__name__}_{num_twins}"
            else:
                node._id = node.component_type.__name__
        if node.id in self.nodes: raise RuntimeError(f"Node '{node.id}' already exists.")
        self._nodes[node.id] = node
        return node.id
        
    def add_edge(self, edge: EdgeSpec, id=None):
        edge._id = id or len(self.edges)
        if edge.id in self.edges: raise RuntimeError(f"Edge '{edge.id}' already exists.")
        self._edges[edge.id] = edge
        return edge.id
        
    def remove_node(self, node_id):
        if node_id not in self.nodes: raise RuntimeError(f"Node {node_id} is not in this graph.")
        node = self.nodes[node_id]
        for port_type, port_name in node.port_specs.get_port_names():
            if (node_id, port_type, port_name) in self._head_connections or (node_id, port_type, port_name) in self._tail_connections:
                self.disconnect_edge_from_node(node_id, port_type, port_name)
        del self.nodes[node_id]
        
    def remove_edge(self, edge_id):
        if edge_id not in self.edges: raise RuntimeError(f"Edge {edge_id} is not in this graph.")
        if edge_id in self._edge_to_head_connections:
            self.disconnect_edge_from_node(*self._edge_to_head_connections[edge_id])
        if edge_id in self._edge_to_tail_connections:
            self.disconnect_edge_from_node(*self._edge_to_tail_connections[edge_id])
        del self.edges[edge_id]
        
    def connect_edge_to_node(self, node_id:Hashable, port_type: Union[PortType, str], port_name: str, edge_id:Hashable):
        node_is_graph = node_id == self.GRAPH_ID
        node = self if node_is_graph else self.nodes[node_id]
        edge = self.edges[edge_id]
        if type(port_type) == str: port_type = PortType.get(port_type)
        is_head_connection = port_type.is_input_port if not node_is_graph else not port_type.is_input_port
        if (port_type, port_name) not in node.port_specs:
            if not node_is_graph:
                raise RuntimeError(f"Port {port_type.label}.{port_name} does not exist in {node.component_type.__name__}.")
            else:
                raise RuntimeError(f"Port {port_type.label}.{port_name} does not exist in graph port specs.")
        connections = self._head_connections if is_head_connection else self._tail_connections
        edge_to_connections = self._edge_to_head_connections if is_head_connection else self._edge_to_tail_connections
        if (node_id,port_type,port_name) in connections:
            raise RuntimeError(f"Edge {connections[(node_id,port_type,port_name)]} already connected to port {port_type.label}.{port_name} of Node {node_id}.")
        if edge_id in edge_to_connections:
            raise RuntimeError(f"Edge {edge_to_connections[edge_id]} already connected to port {port_type.label}.{port_name} of Node {node_id}.")
        connections[(node_id,port_type,port_name)] = edge_id
        edge_to_connections[edge_id] = (node_id,port_type,port_name)

    def disconnect_edge_from_node(self, node_id:Hashable, port_type: Union[PortType, str], port_name: str):
        node_is_graph = node_id == self.GRAPH_ID
        node = self if node_is_graph else self.nodes[node_id]
        if type(port_type) == str: port_type = PortType.get(port_type)
        is_head_connection = port_type.is_input_port if not node_is_graph else not port_type.is_input_port
        if not (port_type.label, port_name) in node.port_specs:
            if not node_is_graph:
                raise RuntimeError(f"Port {port_type.label}.{port_name} does not exist in {node.component_type.__name__}.")
            else:
                raise RuntimeError(f"Port {port_type.label}.{port_name} does not exist in graph port specs.")
        connections = self._head_connections if is_head_connection else self._tail_connections
        edge_to_connections = self._edge_to_head_connections if is_head_connection else self._edge_to_tail_connections
        if (node_id,port_type,port_name) not in connections:
            raise RuntimeError(f"Port {port_type.label}.{port_name} of Node {node_id} is not connected to an edge.")
        edge_id = connections[(node_id,port_type,port_name)]
        del connections[(node_id,port_type,port_name)]
        del edge_to_connections[edge_id]
        
    def connect_edge_to_graph_port(self, port_type: PortType, port_name: str, edge_id:Hashable):
        self.connect_edge_to_node(0, port_type, port_name, edge_id)
        
    def disconnect_edge_from_graph_port(self, port_type: PortType, port_name: str):
        self.disconnect_edge_from_graph_port(0, port_type, port_name)
            
    def copy(self):
        g = super().copy()
        g._port_specs = self._port_specs.copy()
        for node in self.nodes.values(): g.add_node(node.copy(), id=node.id)
        for edge in self.edges.values(): g.add_edge(edge.copy(), id=edge.id)
        g._head_connections = self._head_connections.copy()
        g._tail_connections = self._tail_connections.copy()
        return g
    
    def to_mermaid(self):
        mermaid = ["graph TD"]
        
        # Add nodes
        for node_id, node in self.nodes.items():
            mermaid.append(f"    {node_id}[{node.component_type.__name__}]")
        
        # Add edges
        for edge_id, edge in self.edges.items():
            head_conn = self._edge_to_head_connections.get(edge_id)
            tail_conn = self._edge_to_tail_connections.get(edge_id)
            if head_conn and tail_conn:
                head_node, head_port_type, head_port_name = head_conn
                tail_node, tail_port_type, tail_port_name = tail_conn
                mermaid.append(f"    {tail_node} -- {tail_port_type.label}.{tail_port_name} --> {head_node}")
        
        return "\n".join(mermaid)
    
    def is_DAG(self):
        visited = set()
        rec_stack = set()
        
        def is_cyclic(node_id:int):
            # Mark the current node as visited and add it to the recursion stack
            visited.add(node_id)
            rec_stack.add(node_id)
            
            if node_id == self.GRAPH_ID:
                port_specs = self.port_specs
            else:
                port_specs = self.nodes[node_id].port_specs
            
            for port_type, port_name in port_specs.get_port_names():
                if (node_id, port_type, port_name) in self._tail_connections:
                    edge_id = self.tail_connections[(node_id, port_type, port_name)]
                    if edge_id in self._edge_to_head_connections:
                        target_node_id, _, _ = self._edge_to_head_connections[edge_id]
                        if target_node_id not in visited:
                            if is_cyclic(target_node_id):
                                return True
                        elif target_node_id in rec_stack and target_node_id != self.GRAPH_ID: # Graph does not count
                            return True
                    
            rec_stack.remove(node_id)
            return False
        
        node_ids = list(self.nodes.keys())
        node_ids += [v[0] for v in self.tail_connections.keys()]
        node_ids += [v[0] for v in self.head_connections.keys()]
        node_ids = set(node_ids)

        for node_id in node_ids:
            if node_id not in visited:
                if is_cyclic(node_id):
                    return False
        return True

# %% ../nbs/api/03_graph.ipynb 14
class ReadonlyGraph:
    def __init__(self, graph: Graph):
        self._graph = graph
        
    @property
    def nodes(self): return self._graph.nodes
    @property
    def edges(self): return self._graph.edges
    @property
    def head_connections(self): return self._graph.head_connections
    @property
    def tail_connections(self): return self._graph.tail_connections
    @property
    def edge_to_head_connections(self): return self._graph.edge_to_head_connections
    @property
    def edge_to_tail_connections(self): return self._graph.edge_to_tail_connections
    @property
    def graph_head_connections(self): return self._graph.graph_head_connections
    @property
    def graph_tail_connections(self): return self._graph.graph_tail_connections
    
    def copy(self) -> Graph: return self._graph.copy()
