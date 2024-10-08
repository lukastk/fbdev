# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../test_nbs/concurrent/remote/test_ProxyNode_2.ipynb.

# %% auto 0
__all__ = ['graph', 'node_foo_component1', 'node_foo_component2', 'GraphComponent', 'test']

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_2.ipynb 2
import os
from fbdev.dev_utils import is_in_repl

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_2.ipynb 3
if not is_in_repl():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_2.ipynb 4
import asyncio

from fbdev.dev_utils import is_in_repl
from fbdev.graph.net import NodeSpec
from fbdev.concurrent.remote import ProxyNode
from fbdev.comp.port import  PortSpecCollection, PortSpec, PortType
from fbdev.graph.graph_spec import GraphSpec
from fbdev.graph import GraphComponentFactory
from fbdev.concurrent.remote import ProxyNode, Node

from _test_ProxyNode_1 import FooComponent1, FooComponent2

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_2.ipynb 5
graph = GraphSpec(PortSpecCollection(
    PortSpec(PortType.INPUT, 'inp'),
    PortSpec(PortType.OUTPUT, 'out'),
))

node_foo_component1 = graph.add_node(FooComponent1, node_type=ProxyNode)
node_foo_component2 = graph.add_node(FooComponent2)

graph.ports.input.inp >> node_foo_component1.ports.input.inp
node_foo_component1.ports.output.out >> node_foo_component2.ports.input.inp
node_foo_component2.ports.output.out >> graph.ports.output.out

graph.display_mermaid(hide_unconnected_ports=True)

GraphComponent = GraphComponentFactory.create_component(graph)
GraphComponent.set_module()

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_2.ipynb 6
async def test():
    node_spec = NodeSpec(GraphComponent)
    node = Node(node_spec)
    
    await node.task_manager.exec_coros( node.start(), )
    await asyncio.sleep(1)
    await node.task_manager.exec_coros( node.ports.input.inp.put_value('message from parent process') )
    data = await node.task_manager.exec_coros( node.ports.output.out.get_and_consume() )
    print(data)
    await node.task_manager.exec_coros( node.stop() )
