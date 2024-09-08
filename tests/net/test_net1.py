# AUTOGENERATED! DO NOT EDIT! File to edit: ../../test_nbs/nets/test_net1.ipynb.

# %% auto 0
__all__ = ['g', 'add_one', 'copier', 'printer', 'sender', 'test_net1_execution', 'test_net1_addresses']

# %% ../../test_nbs/nets/test_net1.ipynb 1
import fbdev

# %% ../../test_nbs/nets/test_net1.ipynb 2
from typing import Type, Optional, Union, Any, Tuple, Dict
import asyncio

from fbdev.component import func_component, PortSpecCollection, PortTypeSpec, PortSpec, PortType
from fbdev.graph import Graph, NodeSpec, EdgeSpec
from fbdev.net import Net

# %% ../../test_nbs/nets/test_net1.ipynb 3
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
    input=PortTypeSpec(in1=PortSpec(dtype=int)),
    output=PortTypeSpec(out=PortSpec(dtype=int))
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

g.connect_edge_to_graph_port(PortType.INPUT, 'in1', 0)
g.connect_edge_to_node('add_one', PortType.INPUT, 'a', 0)

g.connect_edge_to_node('add_one', PortType.OUTPUT, 'out', 1)
g.connect_edge_to_node('copier', PortType.INPUT, 'a', 1)

g.connect_edge_to_node('copier', PortType.OUTPUT, 'out0', 2)
g.connect_edge_to_node('printer', PortType.INPUT, 'a', 2)

g.connect_edge_to_node('copier', PortType.OUTPUT, 'out1', 3)
g.connect_edge_to_node('sender', PortType.INPUT, 'a', 3)

g.connect_edge_to_node('sender', PortType.OUTPUT, 'out', 4)
g.connect_edge_to_graph_port(PortType.OUTPUT, 'out', 4)

# %% ../../test_nbs/nets/test_net1.ipynb 5
async def _test_net1_execution():
    output = await Net.async_execute_graph(g, 1)
    assert output['out'] is not None
   
def test_net1_execution():
    asyncio.run(_test_net1_execution())    

# %% ../../test_nbs/nets/test_net1.ipynb 7
async def _test_net1_addresses():
    net = Net.from_graph(g)
    net.initialise()
    net.run()
    await net.states.running.wait(True)

    assert net.address == 'Net(net)'
    assert net.component_process.address == 'Net(net)<CompositeComponent>'
    assert net.nodes['add_one'].address == 'Net(net).Node(add_one)'
    assert net.nodes['add_one'].component_process.address == 'Net(net).Node(add_one)<add_one>'
    
    await net.async_stop()
    
def test_net1_addresses():
    asyncio.run(_test_net1_addresses())