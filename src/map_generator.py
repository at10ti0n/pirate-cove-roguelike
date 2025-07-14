import random
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from tile import Tile, TileInfo, BiomeType, determine_biome, get_default_glyph_for_biome
from macro_map import MacroWorldMap, MacroCell


@dataclass
class ChunkCoords:
    macro_x: int
    macro_y: int
    chunk_x: int = 0
    chunk_y: int = 0


class MapGenerator:
    def __init__(self, macro_map: MacroWorldMap, chunk_size: int = 32):
        self.macro_map = macro_map
        self.chunk_size = chunk_size
        self.chunks: Dict[Tuple[int, int, int, int], Dict[Tuple[int, int], TileInfo]] = {}
        
        # Noise parameters for micro-generation
        self.elevation_scales = [0.1, 0.2, 0.4]
        self.elevation_amplitudes = [0.6, 0.3, 0.1]
        self.moisture_scale = 0.15
        self.resource_density = 0.1
    
    def generate_chunk(self, coords: ChunkCoords, seed_offset: int = 0) -> Dict[Tuple[int, int], TileInfo]:
        """Generate a micro chunk based on macro cell data"""
        chunk_key = (coords.macro_x, coords.macro_y, coords.chunk_x, coords.chunk_y)
        
        if chunk_key in self.chunks:
            return self.chunks[chunk_key]
        
        # Get macro cell data
        macro_cell = self.macro_map.get_cell(coords.macro_x, coords.macro_y)
        if not macro_cell:
            # Generate ocean chunk for missing macro cells
            macro_cell = MacroCell(x=coords.macro_x, y=coords.macro_y, elevation=-0.5)
        
        # Get neighboring macro cells for blending
        neighbors = self._get_macro_neighbors(coords.macro_x, coords.macro_y)
        
        # Set up random state for deterministic generation
        chunk_seed = (self.macro_map.seed + 
                     coords.macro_x * 1000 + 
                     coords.macro_y * 1000000 + 
                     coords.chunk_x * 17 + 
                     coords.chunk_y * 23 + 
                     seed_offset)
        rng = random.Random(chunk_seed)
        np.random.seed(chunk_seed % (2**32))
        
        tiles = {}
        
        print(f"Generating chunk at macro ({coords.macro_x}, {coords.macro_y}) "
              f"chunk ({coords.chunk_x}, {coords.chunk_y})")
        
        # Generate each tile in the chunk
        for local_y in range(self.chunk_size):
            for local_x in range(self.chunk_size):
                tile = self._generate_tile(
                    coords, local_x, local_y, macro_cell, neighbors, rng
                )
                tiles[(local_x, local_y)] = tile
        
        # Apply hydraulic erosion
        self._apply_erosion(tiles, coords, rng)
        
        # Generate rivers if macro cell has rivers
        if macro_cell.has_river:
            self._generate_rivers(tiles, coords, macro_cell, rng)
        
        # Place resources
        self._place_resources(tiles, coords, rng)
        
        # Cache and return
        self.chunks[chunk_key] = tiles
        return tiles
    
    def _get_macro_neighbors(self, macro_x: int, macro_y: int) -> Dict[str, MacroCell]:
        """Get neighboring macro cells for blending"""
        neighbors = {}
        directions = {
            'north': (0, -1),
            'south': (0, 1),
            'east': (1, 0),
            'west': (-1, 0),
            'northeast': (1, -1),
            'northwest': (-1, -1),
            'southeast': (1, 1),
            'southwest': (-1, 1)
        }
        
        for direction, (dx, dy) in directions.items():
            neighbor = self.macro_map.get_cell(macro_x + dx, macro_y + dy)
            if neighbor:
                neighbors[direction] = neighbor
            else:
                # Create default ocean neighbor
                neighbors[direction] = MacroCell(
                    x=macro_x + dx, 
                    y=macro_y + dy, 
                    elevation=-0.5
                )
        
        return neighbors
    
    def _generate_tile(self, coords: ChunkCoords, local_x: int, local_y: int, 
                      macro_cell: MacroCell, neighbors: Dict[str, MacroCell], 
                      rng: random.Random) -> TileInfo:
        """Generate a single tile"""
        # Calculate world position
        world_x = coords.macro_x * self.chunk_size + local_x
        world_y = coords.macro_y * self.chunk_size + local_y
        
        # Calculate blend factors for neighboring macro cells
        blend_x = local_x / self.chunk_size
        blend_y = local_y / self.chunk_size
        
        # Blend macro cell properties
        height = self._blend_property(
            macro_cell, neighbors, blend_x, blend_y, 'elevation'
        )
        moisture = self._blend_property(
            macro_cell, neighbors, blend_x, blend_y, 'moisture'
        )
        temperature = self._blend_property(
            macro_cell, neighbors, blend_x, blend_y, 'temperature'
        )
        
        # Add micro-scale noise
        height += self._generate_elevation_noise(world_x, world_y, coords)
        moisture += self._generate_moisture_noise(world_x, world_y) * 0.2
        
        # Clamp values
        height = max(-1.0, min(1.0, height))
        moisture = max(0.0, min(1.0, moisture))
        temperature = max(0.0, min(1.0, temperature))
        
        # Determine biome
        biome = determine_biome(height, moisture, temperature)
        
        # Get appropriate glyph for biome
        glyph = get_default_glyph_for_biome(biome)
        
        # Create foundation PRD Tile namedtuple
        tile = Tile(
            glyph=glyph,
            biome=biome,
            height=height,
            moisture=moisture
        )
        
        # Create TileInfo wrapper with extended data
        tile_info = TileInfo(
            x=world_x,
            y=world_y,
            tile=tile,
            temperature=temperature,
            passable=not (biome in [BiomeType.OCEAN, BiomeType.RIVER, BiomeType.LAKE])
        )
        
        return tile_info
    
    def _blend_property(self, center: MacroCell, neighbors: Dict[str, MacroCell], 
                       blend_x: float, blend_y: float, property_name: str) -> float:
        """Blend a property value across macro cell boundaries"""
        center_value = getattr(center, property_name)
        
        # Simple bilinear interpolation with neighbors
        if blend_x < 0.1 and blend_y < 0.1:
            # Northwest corner
            if 'northwest' in neighbors:
                return (center_value + getattr(neighbors['northwest'], property_name)) * 0.5
        elif blend_x > 0.9 and blend_y < 0.1:
            # Northeast corner
            if 'northeast' in neighbors:
                return (center_value + getattr(neighbors['northeast'], property_name)) * 0.5
        elif blend_x < 0.1 and blend_y > 0.9:
            # Southwest corner
            if 'southwest' in neighbors:
                return (center_value + getattr(neighbors['southwest'], property_name)) * 0.5
        elif blend_x > 0.9 and blend_y > 0.9:
            # Southeast corner
            if 'southeast' in neighbors:
                return (center_value + getattr(neighbors['southeast'], property_name)) * 0.5
        elif blend_x < 0.1:
            # West edge
            if 'west' in neighbors:
                return (center_value + getattr(neighbors['west'], property_name)) * 0.5
        elif blend_x > 0.9:
            # East edge
            if 'east' in neighbors:
                return (center_value + getattr(neighbors['east'], property_name)) * 0.5
        elif blend_y < 0.1:
            # North edge
            if 'north' in neighbors:
                return (center_value + getattr(neighbors['north'], property_name)) * 0.5
        elif blend_y > 0.9:
            # South edge
            if 'south' in neighbors:
                return (center_value + getattr(neighbors['south'], property_name)) * 0.5
        
        return center_value
    
    def _generate_elevation_noise(self, world_x: int, world_y: int, coords: ChunkCoords) -> float:
        """Generate elevation noise using multiple octaves"""
        noise = 0.0
        
        for scale, amplitude in zip(self.elevation_scales, self.elevation_amplitudes):
            # Simple sine-based noise (replace with proper noise library later)
            x_noise = world_x * scale
            y_noise = world_y * scale
            
            noise_value = (np.sin(x_noise * 2 * np.pi) * np.cos(y_noise * 2 * np.pi) + 
                          np.sin(x_noise * 4 * np.pi + 1.5) * np.cos(y_noise * 4 * np.pi + 1.5) * 0.5)
            
            noise += noise_value * amplitude
        
        return noise * 0.1  # Scale down the noise
    
    def _generate_moisture_noise(self, world_x: int, world_y: int) -> float:
        """Generate moisture noise"""
        x_noise = world_x * self.moisture_scale
        y_noise = world_y * self.moisture_scale
        
        return (np.sin(x_noise * 2 * np.pi + 2.1) + np.cos(y_noise * 2 * np.pi + 3.7)) * 0.25
    
    def _apply_erosion(self, tiles: Dict[Tuple[int, int], TileInfo], coords: ChunkCoords, rng: random.Random):
        """Apply simple hydraulic erosion to the chunk"""
        # Simple erosion: slightly lower elevation near water
        for (x, y), tile_info in tiles.items():
            if tile_info.is_water():
                continue
            
            # Check for nearby water
            water_neighbors = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    
                    neighbor_pos = (x + dx, y + dy)
                    if neighbor_pos in tiles and tiles[neighbor_pos].is_water():
                        water_neighbors += 1
            
            if water_neighbors > 0:
                erosion_factor = water_neighbors / 8.0 * 0.05
                # Create new tile with adjusted values
                old_tile = tile_info.tile
                new_height = max(-1.0, old_tile.height - erosion_factor)
                new_moisture = min(1.0, old_tile.moisture + erosion_factor * 0.5)
                
                # Update tile data
                new_tile = Tile(
                    glyph=old_tile.glyph,
                    biome=old_tile.biome,
                    height=new_height,
                    moisture=new_moisture
                )
                tile_info.tile = new_tile
    
    def _generate_rivers(self, tiles: Dict[Tuple[int, int], TileInfo], coords: ChunkCoords, 
                        macro_cell: MacroCell, rng: random.Random):
        """Generate rivers in the chunk based on macro river data"""
        if not macro_cell.has_river:
            return
        
        # Simple river generation: create a winding path across the chunk
        river_start = None
        river_end = None
        
        # Determine river entry and exit points based on macro data
        if 'north' in macro_cell.river_entry_sides:
            river_start = (self.chunk_size // 2 + rng.randint(-5, 5), 0)
        elif 'south' in macro_cell.river_entry_sides:
            river_start = (self.chunk_size // 2 + rng.randint(-5, 5), self.chunk_size - 1)
        elif 'west' in macro_cell.river_entry_sides:
            river_start = (0, self.chunk_size // 2 + rng.randint(-5, 5))
        elif 'east' in macro_cell.river_entry_sides:
            river_start = (self.chunk_size - 1, self.chunk_size // 2 + rng.randint(-5, 5))
        
        if not river_start:
            # If no entry side specified, start from a high elevation point
            high_points = [(pos, tile_info) for pos, tile_info in tiles.items() 
                          if tile_info.tile.height > 0.3 and tile_info.is_land()]
            if high_points:
                river_start = max(high_points, key=lambda x: x[1].tile.height)[0]
        
        if river_start:
            self._trace_chunk_river(tiles, river_start, rng)
    
    def _trace_chunk_river(self, tiles: Dict[Tuple[int, int], TileInfo], 
                          start: Tuple[int, int], rng: random.Random):
        """Trace a river path through the chunk"""
        current_pos = start
        visited = set()
        river_width = 1
        
        for _ in range(100):  # Max river length
            if current_pos in visited or current_pos not in tiles:
                break
            
            visited.add(current_pos)
            
            # Convert tile to river
            tile_info = tiles[current_pos]
            old_tile = tile_info.tile
            
            # Create new river tile
            river_tile = Tile(
                glyph='~',
                biome=BiomeType.RIVER,
                height=min(old_tile.height, 0.05),  # Rivers are slightly above sea level
                moisture=1.0
            )
            
            tile_info.tile = river_tile
            tile_info.passable = False
            
            # Widen river occasionally
            if rng.random() < 0.3:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        
                        neighbor_pos = (current_pos[0] + dx, current_pos[1] + dy)
                        if neighbor_pos in tiles and rng.random() < 0.5:
                            neighbor_tile_info = tiles[neighbor_pos]
                            if neighbor_tile_info.tile.biome != BiomeType.RIVER:
                                old_neighbor = neighbor_tile_info.tile
                                new_neighbor = Tile(
                                    glyph='~',
                                    biome=BiomeType.RIVER,
                                    height=min(old_neighbor.height, 0.05),
                                    moisture=1.0
                                )
                                neighbor_tile_info.tile = new_neighbor
                                neighbor_tile_info.passable = False
            
            # Find next position (move towards lower elevation)
            neighbors = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 1] if dx == 0 else [-1, 0, 1]:
                    next_pos = (current_pos[0] + dx, current_pos[1] + dy)
                    if (next_pos in tiles and 
                        next_pos not in visited and
                        tiles[next_pos].tile.height <= tile_info.tile.height):
                        neighbors.append(next_pos)
            
            if not neighbors:
                break
            
            # Choose next position (prefer moving towards water or lower elevation)
            current_pos = min(neighbors, key=lambda pos: tiles[pos].tile.height)
    
    def _place_resources(self, tiles: Dict[Tuple[int, int], TileInfo], 
                        coords: ChunkCoords, rng: random.Random):
        """Place resources in the chunk based on tile properties"""
        for tile_info in tiles.values():
            if not tile_info.is_land():
                continue
            
            # Determine resource type based on biome and properties
            resource_type = None
            base_quantity = 0
            
            # Create a temporary TileInfo wrapper for compatibility with existing methods
            temp_tile_wrapper = TileInfo(tile_info.x, tile_info.y, tile_info.tile)
            
            if temp_tile_wrapper.can_mine():
                mining_richness = temp_tile_wrapper.get_mining_richness()
                if rng.random() < 0.1 * mining_richness:
                    if tile_info.tile.biome == BiomeType.MOUNTAINS:
                        resource_choices = ['iron_ore', 'copper_ore', 'silver_ore']
                        if rng.random() < 0.05:
                            resource_choices.append('gold_ore')
                    else:  # Hills
                        resource_choices = ['stone', 'clay', 'iron_ore']
                    
                    resource_type = rng.choice(resource_choices)
                    base_quantity = rng.randint(50, 200)
            
            elif tile_info.tile.biome == BiomeType.FOREST:
                if rng.random() < 0.2:
                    resource_type = 'wood'
                    base_quantity = rng.randint(20, 80)
            
            elif tile_info.tile.biome == BiomeType.BEACH:
                if rng.random() < 0.05:
                    resource_type = 'salt'
                    base_quantity = rng.randint(10, 40)
            
            if resource_type:
                # Adjust quantity based on tile richness
                if temp_tile_wrapper.can_mine():
                    quantity = int(base_quantity * temp_tile_wrapper.get_mining_richness())
                else:
                    quantity = base_quantity
                
                tile_info.set_resource(resource_type, quantity)
    
    def get_chunk(self, coords: ChunkCoords) -> Optional[Dict[Tuple[int, int], TileInfo]]:
        """Get a cached chunk"""
        chunk_key = (coords.macro_x, coords.macro_y, coords.chunk_x, coords.chunk_y)
        return self.chunks.get(chunk_key)
    
    def get_tile(self, world_x: int, world_y: int) -> Optional[TileInfo]:
        """Get a tile at world coordinates"""
        # Calculate chunk coordinates
        macro_x = world_x // self.chunk_size
        macro_y = world_y // self.chunk_size
        local_x = world_x % self.chunk_size
        local_y = world_y % self.chunk_size
        
        coords = ChunkCoords(macro_x, macro_y, 0, 0)
        chunk = self.get_chunk(coords)
        
        if not chunk:
            chunk = self.generate_chunk(coords)
        
        return chunk.get((local_x, local_y))