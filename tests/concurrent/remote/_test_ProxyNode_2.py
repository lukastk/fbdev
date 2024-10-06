from fbdev.complib.func_component_factory import func_component

@func_component()
def FooComponent1(inp):
    print('foo_component1 received:', inp)
    return 'message from foo_component1'

@func_component()
def FooComponent2(inp):
    print('foo_component2 received:', inp)
    return 'message from foo_component2'