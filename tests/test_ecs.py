import unittest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ecs.registry import Registry, EventBus, Event
from ecs.components import Position, Renderable, Velocity, TileInfo
from ecs.systems import MovementSystem, RenderSystem


class TestEvent(Event):
    def __init__(self, message: str):
        self.message = message


class TestECSRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
    
    def test_create_entity(self):
        entity_id = self.registry.create_entity()
        self.assertIsInstance(entity_id, int)
        self.assertTrue(self.registry.entity_exists(entity_id))
    
    def test_add_component(self):
        entity_id = self.registry.create_entity()
        position = Position(x=10, y=20)
        
        self.registry.add_component(entity_id, position)
        retrieved = self.registry.get_component(entity_id, Position)
        
        self.assertEqual(retrieved.x, 10)
        self.assertEqual(retrieved.y, 20)
    
    def test_remove_component(self):
        entity_id = self.registry.create_entity()
        position = Position(x=10, y=20)
        
        self.registry.add_component(entity_id, position)
        self.assertTrue(self.registry.has_component(entity_id, Position))
        
        self.registry.remove_component(entity_id, Position)
        self.assertFalse(self.registry.has_component(entity_id, Position))
    
    def test_query_single_component(self):
        entity1 = self.registry.create_entity()
        entity2 = self.registry.create_entity()
        
        self.registry.add_component(entity1, Position(x=1, y=1))
        self.registry.add_component(entity2, Position(x=2, y=2))
        
        results = list(self.registry.query(Position))
        self.assertEqual(len(results), 2)
        
        entity_ids = [entity_id for entity_id, _ in results]
        self.assertIn(entity1, entity_ids)
        self.assertIn(entity2, entity_ids)
    
    def test_query_multiple_components(self):
        entity1 = self.registry.create_entity()
        entity2 = self.registry.create_entity()
        entity3 = self.registry.create_entity()
        
        # Entity 1: Position + Renderable
        self.registry.add_component(entity1, Position(x=1, y=1))
        self.registry.add_component(entity1, Renderable(glyph='@'))
        
        # Entity 2: Position only
        self.registry.add_component(entity2, Position(x=2, y=2))
        
        # Entity 3: Position + Renderable + Velocity
        self.registry.add_component(entity3, Position(x=3, y=3))
        self.registry.add_component(entity3, Renderable(glyph='X'))
        self.registry.add_component(entity3, Velocity(dx=1, dy=1))
        
        # Query for Position + Renderable
        results = list(self.registry.query(Position, Renderable))
        self.assertEqual(len(results), 2)  # Only entity1 and entity3
        
        entity_ids = [entity_id for entity_id, _ in results]
        self.assertIn(entity1, entity_ids)
        self.assertIn(entity3, entity_ids)
        self.assertNotIn(entity2, entity_ids)
    
    def test_destroy_entity(self):
        entity_id = self.registry.create_entity()
        self.registry.add_component(entity_id, Position(x=1, y=1))
        self.registry.add_component(entity_id, Renderable(glyph='@'))
        
        self.assertTrue(self.registry.entity_exists(entity_id))
        self.assertTrue(self.registry.has_component(entity_id, Position))
        
        self.registry.destroy_entity(entity_id)
        
        self.assertFalse(self.registry.entity_exists(entity_id))
        self.assertFalse(self.registry.has_component(entity_id, Position))
        self.assertFalse(self.registry.has_component(entity_id, Renderable))


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.events_received = []
    
    def event_handler(self, event):
        self.events_received.append(event)
    
    def test_subscribe_and_emit(self):
        self.event_bus.subscribe(TestEvent, self.event_handler)
        
        event = TestEvent("test message")
        self.event_bus.emit(event)
        
        self.assertEqual(len(self.events_received), 1)
        self.assertEqual(self.events_received[0].message, "test message")
    
    def test_multiple_handlers(self):
        events_received_2 = []
        
        def handler_2(event):
            events_received_2.append(event)
        
        self.event_bus.subscribe(TestEvent, self.event_handler)
        self.event_bus.subscribe(TestEvent, handler_2)
        
        event = TestEvent("test message")
        self.event_bus.emit(event)
        
        self.assertEqual(len(self.events_received), 1)
        self.assertEqual(len(events_received_2), 1)


class TestComponents(unittest.TestCase):
    def test_position_component(self):
        pos = Position(x=10.5, y=20.3, layer="test")
        
        self.assertEqual(pos.x, 10.5)
        self.assertEqual(pos.y, 20.3)
        self.assertEqual(pos.layer, "test")
    
    def test_renderable_component(self):
        rend = Renderable(glyph='@', color=32, visible=True, render_layer=2)
        
        self.assertEqual(rend.glyph, '@')
        self.assertEqual(rend.color, 32)
        self.assertTrue(rend.visible)
        self.assertEqual(rend.render_layer, 2)
    
    def test_tile_info_component(self):
        from tile import Tile, BiomeType
        
        test_tile = Tile(glyph='.', biome=BiomeType.GRASSLAND, height=0.3, moisture=0.6)
        tile_info = TileInfo(x=5, y=10, tile_data=test_tile, passable=True)
        
        self.assertEqual(tile_info.x, 5)
        self.assertEqual(tile_info.y, 10)
        self.assertTrue(tile_info.passable)
        self.assertTrue(tile_info.is_land())
        self.assertFalse(tile_info.is_water())


class TestSystems(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
        self.movement_system = MovementSystem(self.registry)
        self.render_system = RenderSystem(self.registry)
        # Remove health system since it's not in foundation scope
    
    def test_movement_system(self):
        entity = self.registry.create_entity()
        self.registry.add_component(entity, Position(x=0, y=0))
        self.registry.add_component(entity, Velocity(dx=1, dy=2))
        
        self.movement_system.update(dt=1.0)
        
        position = self.registry.get_component(entity, Position)
        self.assertEqual(position.x, 1.0)
        self.assertEqual(position.y, 2.0)
    
    def test_render_system(self):
        entity1 = self.registry.create_entity()
        self.registry.add_component(entity1, Position(x=5, y=10))
        self.registry.add_component(entity1, Renderable(glyph='@', color=32))
        
        entity2 = self.registry.create_entity()
        self.registry.add_component(entity2, Position(x=3, y=7))
        self.registry.add_component(entity2, Renderable(glyph='X', visible=False))
        
        self.render_system.update(dt=0.1)
        render_data = self.render_system.get_render_data()
        
        # Only visible entities should be in render data
        self.assertEqual(len(render_data), 1)
        self.assertEqual(render_data[0]['glyph'], '@')
        self.assertEqual(render_data[0]['x'], 5)
        self.assertEqual(render_data[0]['y'], 10)


if __name__ == '__main__':
    unittest.main()