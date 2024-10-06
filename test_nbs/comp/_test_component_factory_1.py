from typing import Type, Any
from fbdev.comp import BaseComponent

class MyComponentFactory(BaseComponent):    
    is_factory = True

    @classmethod
    def create_component(cls) -> Type[BaseComponent]:
        return cls._create_component_class(class_attrs={})
        
comp_with_module_set = MyComponentFactory.create_component()
comp_with_module_set.set_module()
comp_without_module_set = MyComponentFactory.create_component()