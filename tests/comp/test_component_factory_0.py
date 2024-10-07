# AUTOGENERATED! DO NOT EDIT! File to edit: ../../test_nbs/comp/test_component_factory_0.ipynb.

# %% auto 0
__all__ = ['comp', 'comp_process', 'MyComponentFactory', 'test']

# %% ../../test_nbs/comp/test_component_factory_0.ipynb 1
import os
from fbdev.dev_utils import is_in_repl

# %% ../../test_nbs/comp/test_component_factory_0.ipynb 2
if not is_in_repl():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# %% ../../test_nbs/comp/test_component_factory_0.ipynb 3
from typing import Type, Any

from fbdev.comp import BaseComponent

# %% ../../test_nbs/comp/test_component_factory_0.ipynb 4
class MyComponentFactory(BaseComponent):    
    is_factory = True

    @classmethod
    def create_component(cls, my_attr) -> Type[BaseComponent]:
        return cls._create_component_class(class_attrs={
            'my_attr' : my_attr
        })
    
    async def _post_start(self):
        print(self.my_attr)
        
comp = MyComponentFactory.create_component('hello world')
print('Component:', comp.__name__)
comp_process = comp()
 
async def test():
    await comp_process.start()
    await comp_process.stop()