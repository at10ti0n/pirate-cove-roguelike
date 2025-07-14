import unittest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tile import Tile, BiomeType, determine_biome
from macro_map import MacroWorldMap, MacroCell, LandformType, ClimateType
from map_generator import MapGenerator, ChunkCoords


class TestTile(unittest.TestCase):
    def test_tile_creation(self):
        # Test new Tile namedtuple structure
        tile = Tile(glyph='@', biome=BiomeType.GRASSLAND, height=0.5, moisture=0.6)
        
        self.assertEqual(tile.glyph, '@')
        self.assertEqual(tile.biome, BiomeType.GRASSLAND)
        self.assertEqual(tile.height, 0.5)
        self.assertEqual(tile.moisture, 0.6)
        
        # Test TileInfo wrapper
        from tile import TileInfo as TileInfoClass
        tile_info = TileInfoClass(x=5, y=10, tile=tile)
        
        self.assertEqual(tile_info.x, 5)
        self.assertEqual(tile_info.y, 10)
        self.assertTrue(tile_info.is_land())
        self.assertFalse(tile_info.is_water())
    
    def test_biome_determination(self):
        # Test ocean
        biome = determine_biome(height=-0.5, moisture=0.5, temperature=0.5)
        self.assertEqual(biome, BiomeType.OCEAN)
        
        # Test beach
        biome = determine_biome(height=0.05, moisture=0.5, temperature=0.5)
        self.assertEqual(biome, BiomeType.BEACH)
        
        # Test mountains
        biome = determine_biome(height=0.8, moisture=0.3, temperature=0.5)
        self.assertEqual(biome, BiomeType.MOUNTAINS)
        
        # Test desert
        biome = determine_biome(height=0.3, moisture=0.1, temperature=0.8)
        self.assertEqual(biome, BiomeType.DESERT)
        
        # Test forest
        biome = determine_biome(height=0.4, moisture=0.8, temperature=0.4)
        self.assertEqual(biome, BiomeType.FOREST)
    
    def test_tile_capabilities(self):
        from tile import TileInfo as TileInfoClass
        
        # Grassland should be farmable
        grassland_tile = Tile(glyph='.', biome=BiomeType.GRASSLAND, height=0.3, moisture=0.6)
        grassland_info = TileInfoClass(x=0, y=0, tile=grassland_tile)
        self.assertTrue(grassland_info.can_farm())
        self.assertFalse(grassland_info.can_mine())
        self.assertTrue(grassland_info.can_build())
        
        # Mountains should be minable
        mountain_tile = Tile(glyph='^', biome=BiomeType.MOUNTAINS, height=0.8, moisture=0.3)
        mountain_info = TileInfoClass(x=0, y=0, tile=mountain_tile)
        self.assertFalse(mountain_info.can_farm())
        self.assertTrue(mountain_info.can_mine())
        self.assertFalse(mountain_info.can_build())  # Too high
        
        # Ocean should not be suitable for anything
        ocean_tile = Tile(glyph='~', biome=BiomeType.OCEAN, height=-0.3, moisture=1.0)
        ocean_info = TileInfoClass(x=0, y=0, tile=ocean_tile)
        self.assertFalse(ocean_info.can_farm())
        self.assertFalse(ocean_info.can_mine())
        self.assertFalse(ocean_info.can_build())
    
    def test_resource_system(self):
        from tile import TileInfo as TileInfoClass
        
        tile_data = Tile(glyph='.', biome=BiomeType.GRASSLAND, height=0.3, moisture=0.6)
        tile_info = TileInfoClass(x=0, y=0, tile=tile_data)
        
        # Initially no resources
        self.assertIsNone(tile_info.resource_type)
        self.assertEqual(tile_info.resource_quantity, 0)
        
        # Set resource
        tile_info.set_resource('wood', 50)
        self.assertEqual(tile_info.resource_type, 'wood')
        self.assertEqual(tile_info.resource_quantity, 50)
        
        # Harvest some
        harvested = tile_info.harvest_resource(20)
        self.assertEqual(harvested, 20)
        self.assertEqual(tile_info.resource_quantity, 30)
        
        # Try to harvest more than available
        harvested = tile_info.harvest_resource(50)
        self.assertEqual(harvested, 30)
        self.assertIsNone(tile_info.resource_type)
        self.assertEqual(tile_info.resource_quantity, 0)


class TestMacroMap(unittest.TestCase):
    def test_deterministic_generation(self):
        # Same seed should produce identical maps
        map1 = MacroWorldMap(width=20, height=20, seed=12345)
        map2 = MacroWorldMap(width=20, height=20, seed=12345)
        
        # Check that elevation patterns are identical
        for y in range(20):
            for x in range(20):
                cell1 = map1.get_cell(x, y)
                cell2 = map2.get_cell(x, y)
                
                self.assertIsNotNone(cell1)
                self.assertIsNotNone(cell2)
                self.assertAlmostEqual(cell1.elevation, cell2.elevation, places=5)
                self.assertEqual(cell1.biome, cell2.biome)
    
    def test_different_seeds_produce_different_maps(self):
        map1 = MacroWorldMap(width=20, height=20, seed=12345)
        map2 = MacroWorldMap(width=20, height=20, seed=54321)
        
        # Count differences in elevation
        differences = 0
        total_cells = 0
        
        for y in range(20):
            for x in range(20):
                cell1 = map1.get_cell(x, y)
                cell2 = map2.get_cell(x, y)
                
                if cell1 and cell2:
                    total_cells += 1
                    if abs(cell1.elevation - cell2.elevation) > 0.1:
                        differences += 1
        
        # At least 50% of cells should be significantly different
        difference_ratio = differences / total_cells
        self.assertGreater(difference_ratio, 0.5)
    
    def test_map_properties(self):
        macro_map = MacroWorldMap(width=30, height=30, seed=42)
        
        # Count land vs water
        land_cells = len(macro_map.get_land_cells())
        water_cells = len(macro_map.get_water_cells())
        total_cells = land_cells + water_cells
        
        # Should have some land and water
        self.assertGreater(land_cells, 0)
        self.assertGreater(water_cells, 0)
        
        # Land ratio should be reasonable (10% to 80%)
        land_ratio = land_cells / total_cells
        self.assertGreater(land_ratio, 0.1)
        self.assertLess(land_ratio, 0.8)
        
        # Should have some settlements
        settlements = macro_map.get_settlements()
        self.assertGreater(len(settlements), 0)
        self.assertLess(len(settlements), 25)  # Not too many
    
    def test_neighbor_system(self):
        macro_map = MacroWorldMap(width=10, height=10, seed=123)
        
        # Test center cell neighbors
        center_cell = macro_map.get_cell(5, 5)
        self.assertIsNotNone(center_cell)
        
        neighbors = macro_map.get_neighbors(5, 5)
        self.assertEqual(len(neighbors), 8)  # 8 adjacent neighbors
        
        # Test edge cell neighbors
        edge_neighbors = macro_map.get_neighbors(0, 0)
        self.assertEqual(len(edge_neighbors), 3)  # Only 3 neighbors for corner


class TestMapGenerator(unittest.TestCase):
    def setUp(self):
        self.macro_map = MacroWorldMap(width=5, height=5, seed=999)
        self.generator = MapGenerator(self.macro_map, chunk_size=16)
    
    def test_chunk_generation(self):
        coords = ChunkCoords(macro_x=2, macro_y=2, chunk_x=0, chunk_y=0)
        chunk = self.generator.generate_chunk(coords)
        
        # Should generate correct number of tiles
        self.assertEqual(len(chunk), 16 * 16)
        
        # All tiles should have valid coordinates
        for (x, y), tile_info in chunk.items():
            self.assertGreaterEqual(x, 0)
            self.assertLess(x, 16)
            self.assertGreaterEqual(y, 0)
            self.assertLess(y, 16)
            from tile import TileInfo as TileInfoClass
            self.assertIsInstance(tile_info, TileInfoClass)
            self.assertIsInstance(tile_info.tile, Tile)
    
    def test_deterministic_chunk_generation(self):
        coords = ChunkCoords(macro_x=1, macro_y=1, chunk_x=0, chunk_y=0)
        
        # Generate same chunk twice
        chunk1 = self.generator.generate_chunk(coords)
        chunk2 = self.generator.generate_chunk(coords)
        
        # Should be identical (from cache)
        self.assertIs(chunk1, chunk2)
        
        # Generate with new generator (same macro map)
        generator2 = MapGenerator(self.macro_map, chunk_size=16)
        chunk3 = generator2.generate_chunk(coords)
        
        # Should have identical tile properties
        for pos in chunk1:
            tile_info1 = chunk1[pos]
            tile_info3 = chunk3[pos]
            self.assertAlmostEqual(tile_info1.tile.height, tile_info3.tile.height, places=3)
            self.assertEqual(tile_info1.tile.biome, tile_info3.tile.biome)
    
    def test_biome_distribution(self):
        coords = ChunkCoords(macro_x=2, macro_y=2, chunk_x=0, chunk_y=0)
        chunk = self.generator.generate_chunk(coords)
        
        # Count biome types
        biome_counts = {}
        for tile_info in chunk.values():
            biome = tile_info.tile.biome
            biome_counts[biome] = biome_counts.get(biome, 0) + 1
        
        # Should have at least one biome type
        self.assertGreater(len(biome_counts), 0)
        
        # All tiles should have valid biomes
        for biome in biome_counts:
            self.assertIsInstance(biome, BiomeType)
    
    def test_resource_placement(self):
        # Generate chunk in a land-heavy area
        coords = ChunkCoords(macro_x=2, macro_y=2, chunk_x=0, chunk_y=0)
        chunk = self.generator.generate_chunk(coords)
        
        # Count tiles with resources
        resource_tiles = [tile_info for tile_info in chunk.values() if tile_info.resource_type]
        
        # Should have some resources but not too many
        resource_ratio = len(resource_tiles) / len(chunk)
        self.assertGreaterEqual(resource_ratio, 0.0)
        self.assertLessEqual(resource_ratio, 0.3)
        
        # Resources should be on appropriate terrain
        for tile_info in resource_tiles:
            if tile_info.resource_type in ['iron_ore', 'copper_ore', 'stone']:
                self.assertTrue(tile_info.can_mine() or tile_info.tile.biome in [BiomeType.HILLS, BiomeType.MOUNTAINS])
            elif tile_info.resource_type == 'wood':
                self.assertEqual(tile_info.tile.biome, BiomeType.FOREST)
    
    def test_world_coordinate_system(self):
        # Test getting tiles by world coordinates
        tile_info = self.generator.get_tile(0, 0)
        self.assertIsNotNone(tile_info)
        self.assertEqual(tile_info.x, 0)
        self.assertEqual(tile_info.y, 0)
        
        # Test tile from different chunk
        tile_info2 = self.generator.get_tile(20, 25)
        self.assertIsNotNone(tile_info2)
        self.assertEqual(tile_info2.x, 20)
        self.assertEqual(tile_info2.y, 25)


class TestIntegration(unittest.TestCase):
    def test_full_generation_pipeline(self):
        """Test the complete generation pipeline"""
        # Create macro map
        macro_map = MacroWorldMap(width=3, height=3, seed=777)
        
        # Verify macro map was created
        self.assertEqual(len(macro_map.cells), 9)
        
        # Create generator
        generator = MapGenerator(macro_map, chunk_size=8)
        
        # Generate multiple chunks
        chunks_generated = 0
        for macro_x in range(3):
            for macro_y in range(3):
                coords = ChunkCoords(macro_x, macro_y, 0, 0)
                chunk = generator.generate_chunk(coords)
                
                self.assertEqual(len(chunk), 64)  # 8x8 = 64 tiles
                chunks_generated += 1
        
        self.assertEqual(chunks_generated, 9)
        
        # Test accessing tiles across chunk boundaries
        tile1 = generator.get_tile(7, 7)   # End of first chunk
        tile2 = generator.get_tile(8, 8)   # Start of next chunk
        
        self.assertIsNotNone(tile1)
        self.assertIsNotNone(tile2)
        
        # Tiles should have coherent properties (neighboring biomes shouldn't be too different)
        # This is a basic sanity check for the blending system


if __name__ == '__main__':
    unittest.main()