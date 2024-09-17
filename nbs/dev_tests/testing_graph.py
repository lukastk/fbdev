from typing import Type, Optional, Union, Any, Tuple, Dict
import asyncio

from fbdev.component import func_component, PortSpecCollection, PortTypeSpec, PortSpec, PortType
from fbdev.graph import Graph, NodeSpec, EdgeSpec
from fbdev.node import Node, GraphComponentFactory
from fbdev.runtime import BatchExecutor

#|export
@func_component()
def add_one(a:int) -> int:
    print("In add_one")
    return a+1

@func_component()
def copier(a:int) -> Tuple[int, int]:
    print("In copier")
    return a, a

@func_component()
def printer(a:int) -> None:
    print("In printer1:", a)
    
@func_component()
def sender(a:int):
    print("In sender")
    return a
    
g = Graph(PortSpecCollection(
    input=PortTypeSpec(graph_in=PortSpec(dtype=int)),
    output=PortTypeSpec(graph_out=PortSpec(dtype=int))
))

g.add_node(NodeSpec(add_one))
g.add_node(NodeSpec(copier))
g.add_node(NodeSpec(printer))
g.add_node(NodeSpec(sender))

g.add_edge(EdgeSpec())
g.add_edge(EdgeSpec())
g.add_edge(EdgeSpec())
g.add_edge(EdgeSpec())
g.add_edge(EdgeSpec())

g.connect_edge_to_graph_port(PortType.INPUT, 'graph_in', 0)
g.connect_edge_to_node('add_one', PortType.INPUT, 'a', 0)

g.connect_edge_to_node('add_one', PortType.OUTPUT, 'out', 1)
g.connect_edge_to_node('copier', PortType.INPUT, 'a', 1)

g.connect_edge_to_node('copier', PortType.OUTPUT, 'out0', 2)
g.connect_edge_to_node('printer', PortType.INPUT, 'a', 2)

g.connect_edge_to_node('copier', PortType.OUTPUT, 'out1', 3)
g.connect_edge_to_node('sender', PortType.INPUT, 'a', 3)

g.connect_edge_to_node('sender', PortType.OUTPUT, 'out', 4)
g.connect_edge_to_graph_port(PortType.OUTPUT, 'graph_out', 4)