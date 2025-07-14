from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from dataclasses import dataclass
import time

if TYPE_CHECKING:
    from .registry import Registry

from .components import Position, Velocity, Renderable, TileInfo


class BaseSystem(ABC):
    def __init__(self, registry: 'Registry'):
        self.registry = registry
        self.enabled = True
    
    @abstractmethod
    def update(self, dt: float):
        pass
    
    def enable(self):
        self.enabled = True
    
    def disable(self):
        self.enabled = False


class MovementSystem(BaseSystem):
    def update(self, dt: float):
        if not self.enabled:
            return
        
        for entity_id, (position, velocity) in self.registry.query(Position, Velocity):
            old_x, old_y = position.x, position.y
            position.x += velocity.dx * dt
            position.y += velocity.dy * dt
            
            # Emit movement event if position changed
            if old_x != position.x or old_y != position.y:
                from .registry import Event
                
                @dataclass
                class EntityMoved(Event):
                    entity_id: int
                    old_position: tuple
                    new_position: tuple
                
                event = EntityMoved(
                    entity_id=entity_id,
                    old_position=(old_x, old_y),
                    new_position=(position.x, position.y)
                )
                self.registry.event_bus.emit(event)


class RenderSystem(BaseSystem):
    def __init__(self, registry: 'Registry'):
        super().__init__(registry)
        self.render_data = []
    
    def update(self, dt: float):
        if not self.enabled:
            return
        
        self.render_data.clear()
        
        # Collect all renderable entities with positions
        for entity_id, (position, renderable) in self.registry.query(Position, Renderable):
            if renderable.visible:
                self.render_data.append({
                    'entity_id': entity_id,
                    'x': int(position.x),
                    'y': int(position.y),
                    'layer': renderable.render_layer,
                    'glyph': renderable.glyph,
                    'color': renderable.color
                })
        
        # Sort by layer for proper rendering order
        self.render_data.sort(key=lambda item: item['layer'])
    
    def get_render_data(self):
        return self.render_data


# Foundation phase systems - simplified for basic functionality