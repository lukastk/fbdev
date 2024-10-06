# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../test_nbs/concurrent/remote/test_ProxyNode_1.ipynb.

# %% auto 0
__all__ = ['test']

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_1.ipynb 2
import os
from fbdev.dev_utils import is_in_repl

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_1.ipynb 3
if not is_in_repl():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_1.ipynb 4
from fbdev.dev_utils import is_in_repl
from fbdev.graph.net import NodeSpec
from fbdev.concurrent.remote import ProxyNode

from _test_ProxyNode_1 import GraphComponent

# %% ../../../test_nbs/concurrent/remote/test_ProxyNode_1.ipynb 5
async def test():
    node_spec = NodeSpec(GraphComponent)
    node = ProxyNode(node_spec)
    
    await node.task_manager.exec_coros( node.start(), )
    await node.task_manager.exec_coros( node.ports.input.inp.put_value('message from parent process') )
    data = await node.task_manager.exec_coros( node.ports.output.out.get_and_consume() )
    print(data)
    await node.task_manager.exec_coros( node.stop() )
