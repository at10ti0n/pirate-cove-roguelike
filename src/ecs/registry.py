from typing import Dict, Type, Any, Set, List, Tuple, Iterable, Callable
from dataclasses import dataclass


@dataclass
class Event:
    pass


class EventBus:
    def __init__(self):
        self._handlers: Dict[Type, List[Callable]] = {}
    
    def subscribe(self, event_type: Type, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def emit(self, event: Event):
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)


class Registry:
    def __init__(self):
        self._next_id = 1
        self._entities: Set[int] = set()
        self._components: Dict[Type, Dict[int, Any]] = {}
        self.event_bus = EventBus()
    
    def create_entity(self) -> int:
        entity_id = self._next_id
        self._next_id += 1
        self._entities.add(entity_id)
        return entity_id
    
    def destroy_entity(self, entity_id: int):
        if entity_id not in self._entities:
            return
        
        # Remove all components for this entity
        for component_type in self._components:
            if entity_id in self._components[component_type]:
                del self._components[component_type][entity_id]
        
        self._entities.remove(entity_id)
    
    def add_component(self, entity_id: int, component: Any):
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} does not exist")
        
        component_type = type(component)
        if component_type not in self._components:
            self._components[component_type] = {}
        
        self._components[component_type][entity_id] = component
    
    def remove_component(self, entity_id: int, component_type: Type):
        if component_type in self._components and entity_id in self._components[component_type]:
            del self._components[component_type][entity_id]
    
    def get_component(self, entity_id: int, component_type: Type):
        if component_type in self._components and entity_id in self._components[component_type]:
            return self._components[component_type][entity_id]
        return None
    
    def has_component(self, entity_id: int, component_type: Type) -> bool:
        return (component_type in self._components and 
                entity_id in self._components[component_type])
    
    def query(self, *component_types: Type) -> Iterable[Tuple[int, List[Any]]]:
        if not component_types:
            return
        
        # Find entities that have all required components
        entities_with_all_components = set(self._entities)
        
        for component_type in component_types:
            if component_type not in self._components:
                return
            entities_with_all_components &= set(self._components[component_type].keys())
        
        # Return entity ID and list of components
        for entity_id in entities_with_all_components:
            components = []
            for component_type in component_types:
                components.append(self._components[component_type][entity_id])
            yield entity_id, components
    
    def get_entities_with_component(self, component_type: Type) -> List[int]:
        if component_type not in self._components:
            return []
        return list(self._components[component_type].keys())
    
    def entity_exists(self, entity_id: int) -> bool:
        return entity_id in self._entities