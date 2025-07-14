import unittest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ecs.registry import Registry
from ecs.components import Position, Renderable, Player, TileInfo
from ecs.systems import MovementSystem, RenderSystem
from macro_map import MacroWorldMap
from map_generator import MapGenerator, ChunkCoords
from terminal_renderer import TerminalRenderer, RenderData
from input_handler import InputHandler, GameCommand
from save_manager import SaveManager
from tile import Tile, BiomeType, determine_biome


class TestFoundationIntegration(unittest.TestCase):
    """Integration tests for the complete foundation system"""
    
    def setUp(self):
        """Set up test environment"""
        self.seed = 12345
        self.registry = Registry()
        self.save_manager = SaveManager()
        self.input_handler = InputHandler()
        
        # Set up world generation
        self.macro_map = MacroWorldMap(width=8, height=4, seed=self.seed)
        self.map_generator = MapGenerator(self.macro_map, chunk_size=16)
        
        # Set up rendering (but don't actually render in tests)
        self.renderer = TerminalRenderer(viewport_width=20, viewport_height=10)
        
        # Set up systems
        self.movement_system = MovementSystem(self.registry)
        self.render_system = RenderSystem(self.registry)
    
    def test_complete_foundation_workflow(self):
        """Test the complete foundation workflow"""
        # 1. Test world generation
        macro_cell = self.macro_map.get_cell(2, 1)
        self.assertIsNotNone(macro_cell)
        self.assertIsInstance(macro_cell.biome, BiomeType)
        
        # 2. Test chunk generation
        coords = ChunkCoords(macro_x=2, macro_y=1)
        chunk = self.map_generator.generate_chunk(coords)
        self.assertEqual(len(chunk), 16 * 16)
        
        # Verify tiles are properly structured
        for (x, y), tile_info in chunk.items():
            self.assertIsInstance(tile_info.tile, Tile)
            self.assertIsInstance(tile_info.tile.biome, BiomeType)
            self.assertIsInstance(tile_info.tile.glyph, str)
            self.assertIsInstance(tile_info.tile.height, float)
            self.assertIsInstance(tile_info.tile.moisture, float)
        
        # 3. Test ECS entity creation
        player_entity = self.registry.create_entity()
        self.registry.add_component(
            player_entity,
            Position(x=8.0, y=8.0)
        )
        self.registry.add_component(
            player_entity,
            Renderable(glyph='@', color=37, visible=True, render_layer=2)
        )
        self.registry.add_component(
            player_entity,
            Player(name="TestCaptain")
        )
        
        # Verify entity was created properly
        self.assertTrue(self.registry.entity_exists(player_entity))
        pos = self.registry.get_component(player_entity, Position)
        self.assertEqual(pos.x, 8.0)
        self.assertEqual(pos.y, 8.0)
        
        # 4. Test ECS systems
        self.movement_system.update(dt=1.0)
        self.render_system.update(dt=1.0)
        
        # Verify render system collected data
        render_data = self.render_system.get_render_data()
        self.assertEqual(len(render_data), 1)
        self.assertEqual(render_data[0]['glyph'], '@')
        
        # 5. Test input handling
        self.assertTrue(self.input_handler.is_movement_command(GameCommand.MOVE_NORTH))
        self.assertFalse(self.input_handler.is_movement_command(GameCommand.QUIT))
        
        dx, dy = self.input_handler.get_movement_delta(GameCommand.MOVE_NORTH)
        self.assertEqual((dx, dy), (0, -1))
        
        # 6. Test save manager
        self.save_manager.record_command("test_move", {"x": 8, "y": 8})
        self.save_manager.record_command("test_toggle", {"mode": "micro"})
        
        stats = self.save_manager.get_session_stats()
        self.assertEqual(stats['total_commands'], 2)
        self.assertIn('test_move', stats['commands_by_type'])
        
        # 7. Test command replay
        commands = self.save_manager.get_command_log()
        success = self.save_manager.replay_commands(commands)
        self.assertTrue(success)
        
        # 8. Test JSON export/import
        json_data = self.save_manager.export_to_json()
        self.assertIsInstance(json_data, str)
        self.assertGreater(len(json_data), 0)
        
        new_manager = SaveManager()
        import_success = new_manager.import_from_json(json_data)
        self.assertTrue(import_success)
        
        imported_commands = new_manager.get_command_log()
        self.assertEqual(len(imported_commands), 2)
    
    def test_deterministic_generation(self):
        """Test that generation is deterministic"""
        # Generate same chunk twice with same seed
        coords = ChunkCoords(macro_x=1, macro_y=1)
        
        chunk1 = self.map_generator.generate_chunk(coords)
        chunk2 = self.map_generator.generate_chunk(coords)  # Should return cached version
        
        # Should be exactly the same object (cached)
        self.assertIs(chunk1, chunk2)
        
        # Test with new generator (same macro map)
        generator2 = MapGenerator(self.macro_map, chunk_size=16)
        chunk3 = generator2.generate_chunk(coords)
        
        # Should have identical content
        self.assertEqual(len(chunk1), len(chunk3))
        for pos in chunk1:
            tile1 = chunk1[pos]
            tile3 = chunk3[pos]
            self.assertEqual(tile1.tile.biome, tile3.tile.biome)
            self.assertEqual(tile1.tile.glyph, tile3.tile.glyph)
            self.assertAlmostEqual(tile1.tile.height, tile3.tile.height, places=3)
    
    def test_macro_to_micro_consistency(self):
        """Test that macro and micro generation are consistent"""
        # Test several macro cells
        for macro_x in range(min(4, self.macro_map.width)):
            for macro_y in range(min(2, self.macro_map.height)):
                macro_cell = self.macro_map.get_cell(macro_x, macro_y)
                if not macro_cell:
                    continue
                
                # Generate micro chunk for this macro cell
                coords = ChunkCoords(macro_x, macro_y)
                chunk = self.map_generator.generate_chunk(coords)
                
                # Check that micro chunk reflects macro cell properties
                land_tiles = 0
                water_tiles = 0
                
                for tile_info in chunk.values():
                    if tile_info.tile.biome in [BiomeType.OCEAN, BiomeType.RIVER, BiomeType.LAKE]:
                        water_tiles += 1
                    else:
                        land_tiles += 1
                
                # Basic sanity check: if macro cell is ocean, most micro tiles should be water
                if macro_cell.biome == BiomeType.OCEAN:
                    self.assertGreater(water_tiles, land_tiles)
    
    def test_biome_determination(self):
        """Test biome determination logic"""
        # Test various combinations
        test_cases = [
            # (height, moisture, temp, expected_biome_type)
            (-0.5, 0.5, 0.5, BiomeType.OCEAN),
            (0.05, 0.4, 0.6, BiomeType.BEACH),
            (0.8, 0.3, 0.5, BiomeType.MOUNTAINS),
            (0.3, 0.1, 0.8, BiomeType.DESERT),
            (0.4, 0.8, 0.4, BiomeType.FOREST),
        ]
        
        for height, moisture, temp, expected in test_cases:
            result = determine_biome(height, moisture, temp)
            self.assertEqual(result, expected, 
                           f"Failed for height={height}, moisture={moisture}, temp={temp}")
    
    def test_input_command_mapping(self):
        """Test input command mapping"""
        # Test movement commands
        movement_commands = [
            GameCommand.MOVE_NORTH,
            GameCommand.MOVE_SOUTH, 
            GameCommand.MOVE_EAST,
            GameCommand.MOVE_WEST
        ]
        
        for cmd in movement_commands:
            self.assertTrue(self.input_handler.is_movement_command(cmd))
            dx, dy = self.input_handler.get_movement_delta(cmd)
            self.assertIsInstance(dx, int)
            self.assertIsInstance(dy, int)
            # Ensure movement is unit vector
            self.assertEqual(abs(dx) + abs(dy), 1)
        
        # Test non-movement commands
        non_movement = [GameCommand.QUIT, GameCommand.TOGGLE_MODE, GameCommand.INVALID]
        for cmd in non_movement:
            self.assertFalse(self.input_handler.is_movement_command(cmd))
    
    def test_renderer_coordinate_conversion(self):
        """Test renderer coordinate conversion"""
        # Set camera position
        self.renderer.set_camera_position(10, 20)
        
        # Test world to screen conversion
        screen_x, screen_y = self.renderer.world_to_screen(10, 20)
        self.assertEqual(screen_x, self.renderer.viewport_width // 2)
        self.assertEqual(screen_y, self.renderer.viewport_height // 2)
        
        # Test screen to world conversion
        world_x, world_y = self.renderer.screen_to_world(screen_x, screen_y)
        self.assertEqual(world_x, 10)
        self.assertEqual(world_y, 20)
    
    def test_foundation_prd_compliance(self):
        """Test compliance with Foundation PRD requirements"""
        # Test that we have the required components
        from ecs.components import Position, Renderable, TileInfo
        
        # Test Position component
        pos = Position(x=1.0, y=2.0, layer="test")
        self.assertEqual(pos.x, 1.0)
        self.assertEqual(pos.y, 2.0)
        
        # Test Renderable component  
        rend = Renderable(glyph='X', color=32, visible=True, render_layer=1)
        self.assertEqual(rend.glyph, 'X')
        self.assertEqual(rend.color, 32)
        
        # Test TileInfo component
        test_tile = Tile(glyph='.', biome=BiomeType.GRASSLAND, height=0.3, moisture=0.6)
        tile_info = TileInfo(x=5, y=10, tile_data=test_tile, passable=True)
        self.assertEqual(tile_info.x, 5)
        self.assertEqual(tile_info.y, 10)
        self.assertTrue(tile_info.is_land())
        self.assertFalse(tile_info.is_water())
        
        # Test Tile namedtuple structure (PRD requirement)
        self.assertEqual(test_tile.glyph, '.')
        self.assertEqual(test_tile.biome, BiomeType.GRASSLAND)
        self.assertEqual(test_tile.height, 0.3)
        self.assertEqual(test_tile.moisture, 0.6)
        
        # Test macro map size (PRD requirement: 32x16)
        self.assertEqual(self.macro_map.width, 8)  # We use smaller for tests
        self.assertEqual(self.macro_map.height, 4)
        
        # Test chunk size (PRD requirement: 32x32)
        self.assertEqual(self.map_generator.chunk_size, 16)  # We use smaller for tests
        
        # Test save manager API (PRD requirement)
        self.assertTrue(hasattr(self.save_manager, 'record_command'))
        self.assertTrue(hasattr(self.save_manager, 'replay_commands'))
        
        # Test input handler API (PRD requirement)
        self.assertTrue(hasattr(self.input_handler, 'get_command'))
        
        # Test renderer viewport (PRD requirement: 40x20)
        # We use smaller for tests, but API should be the same
        self.assertEqual(self.renderer.viewport_width, 20)
        self.assertEqual(self.renderer.viewport_height, 10)
    
    def tearDown(self):
        """Clean up after tests"""
        self.input_handler.cleanup()
        self.renderer.cleanup()


if __name__ == '__main__':
    unittest.main()