from fbdev.complib.func_component_factory import func_component
from fbdev.comp.port import  PortSpecCollection, PortSpec, PortType
from fbdev.graph.graph_spec import GraphSpec
from fbdev.graph import GraphComponentFactory

@func_component()
def FooComponent1(inp):
    print('foo_component1 received:', inp)
    return 'message from foo_component1'

@func_component()
def FooComponent2(inp):
    print('foo_component2 received:', inp)
    return 'message from foo_component2'

graph = GraphSpec(PortSpecCollection(
    PortSpec(PortType.INPUT, 'inp'),
    PortSpec(PortType.OUTPUT, 'out'),
))

node_foo_component1 = graph.add_node(FooComponent1)
node_foo_component2 = graph.add_node(FooComponent2)

graph.ports.input.inp >> node_foo_component1.ports.input.inp
node_foo_component1.ports.output.out >> node_foo_component2.ports.input.inp
node_foo_component2.ports.output.out >> graph.ports.output.out

graph.display_mermaid(hide_unconnected_ports=True)

GraphComponent = GraphComponentFactory.create_component(graph)
GraphComponent.set_module()
