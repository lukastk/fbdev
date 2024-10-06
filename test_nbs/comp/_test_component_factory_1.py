from typing import Type, Any
from fbdev.comp import BaseComponent

class MyComponentFactory(BaseComponent):    
    is_factory = True

    @classmethod
    def create_component(cls, my_attr, set_module_name) -> Type[BaseComponent]:
        return cls._create_component_class(class_attrs={
            'my_attr' : my_attr
        }, set_module_name=set_module_name)
    
    async def _post_start(self):
        print(self.my_attr)
        
comp_with_module_set = MyComponentFactory.create_component('hello world', True)
comp_without_module_set = MyComponentFactory.create_component('hello world', False)