from fbdev.complib.func_component_factory import func_component

@func_component()
def FooComponent(inp):
    print("Message from parent:", inp)
    return "Hey parent!"
