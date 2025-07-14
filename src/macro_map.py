import random
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum

from tile import BiomeType, ClimateType, determine_biome


class LandformType(Enum):
    OCEAN = "ocean"
    ISLAND = "island" 
    ARCHIPELAGO = "archipelago"
    CONTINENT = "continent"
    ATOLL = "atoll"
    PENINSULA = "peninsula"


@dataclass
class MacroCell:
    x: int
    y: int
    elevation: float = 0.0
    moisture: float = 0.5
    temperature: float = 0.5
    climate: ClimateType = ClimateType.TEMPERATE
    biome: BiomeType = BiomeType.OCEAN
    landform: LandformType = LandformType.OCEAN
    has_river: bool = False
    river_entry_sides: Set[str] = None
    river_source_pos: Optional[Tuple[float, float]] = None
    is_sea_border: bool = False
    population: int = 0
    wealth: float = 0.0
    
    def __post_init__(self):
        if self.river_entry_sides is None:
            self.river_entry_sides = set()


class MacroWorldMap:
    def __init__(self, width: int = 32, height: int = 16, seed: int = None):
        self.width = width
        self.height = height
        self.seed = seed or random.randint(0, 2**32 - 1)
        
        # Initialize random state
        self.rng = random.Random(self.seed)
        np.random.seed(self.seed)
        
        # Initialize grid
        self.cells: Dict[Tuple[int, int], MacroCell] = {}
        
        # Generation parameters
        self.sea_level = 0.0
        self.land_ratio = 0.3  # 30% land, 70% water
        self.island_clusters = 5  # Number of major island groups
        
        self._generate_world()
    
    def _generate_world(self):
        """Generate the macro world map"""
        print(f"Generating macro world (seed: {self.seed})...")
        
        # Step 1: Generate base elevation using multiple octaves of noise
        self._generate_elevation()
        
        # Step 2: Generate temperature based on latitude and elevation
        self._generate_temperature()
        
        # Step 3: Generate moisture patterns
        self._generate_moisture()
        
        # Step 4: Determine climates
        self._determine_climates()
        
        # Step 5: Determine biomes
        self._determine_biomes()
        
        # Step 6: Classify landforms
        self._classify_landforms()
        
        # Step 7: Generate river systems
        self._generate_rivers()
        
        # Step 8: Mark sea borders
        self._mark_sea_borders()
        
        # Step 9: Generate settlements
        self._generate_settlements()
        
        print(f"Generated {len(self.cells)} macro cells")
    
    def _generate_elevation(self):
        """Generate elevation using fractal noise"""
        # Create multiple noise layers for realistic terrain
        scales = [0.01, 0.02, 0.04, 0.08]  # Different frequencies
        amplitudes = [1.0, 0.5, 0.25, 0.125]  # Decreasing amplitudes
        
        for y in range(self.height):
            for x in range(self.width):
                elevation = 0.0
                
                # Combine multiple noise octaves
                for scale, amplitude in zip(scales, amplitudes):
                    # Simple noise using sine waves (replace with proper noise library later)
                    noise_x = x * scale
                    noise_y = y * scale
                    noise_value = (np.sin(noise_x * 2 * np.pi + self.seed) + 
                                 np.cos(noise_y * 2 * np.pi + self.seed)) * 0.5
                    elevation += noise_value * amplitude
                
                # Normalize and adjust to create islands
                elevation = (elevation + 1.0) * 0.5  # Normalize to 0-1
                
                # Create island effect by reducing elevation near edges
                center_x, center_y = self.width // 2, self.height // 2
                distance_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                max_distance = np.sqrt(center_x**2 + center_y**2)
                edge_factor = 1.0 - (distance_from_center / max_distance) ** 2
                
                elevation *= edge_factor
                
                # Adjust for desired land ratio
                elevation -= (0.5 - self.land_ratio)
                
                cell = MacroCell(x=x, y=y, elevation=elevation)
                self.cells[(x, y)] = cell
    
    def _generate_temperature(self):
        """Generate temperature based on latitude and elevation"""
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[(x, y)]
                
                # Base temperature based on latitude (distance from equator)
                latitude_factor = abs(y - self.height // 2) / (self.height // 2)
                base_temp = 1.0 - latitude_factor  # Hot at equator, cold at poles
                
                # Elevation cooling effect
                elevation_cooling = max(0, cell.elevation) * 0.3
                
                # Some random variation
                temp_noise = (self.rng.random() - 0.5) * 0.2
                
                cell.temperature = max(0.0, min(1.0, base_temp - elevation_cooling + temp_noise))
    
    def _generate_moisture(self):
        """Generate moisture patterns"""
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[(x, y)]
                
                # Base moisture with some noise
                base_moisture = 0.5 + (self.rng.random() - 0.5) * 0.4
                
                # Ocean proximity increases moisture
                ocean_proximity = self._get_ocean_proximity(x, y)
                moisture_bonus = ocean_proximity * 0.3
                
                # Elevation affects moisture (rain shadow effect)
                elevation_factor = max(0, 1.0 - cell.elevation)
                
                cell.moisture = max(0.0, min(1.0, base_moisture + moisture_bonus * elevation_factor))
    
    def _get_ocean_proximity(self, x: int, y: int) -> float:
        """Get proximity to ocean (0.0 = far, 1.0 = adjacent to ocean)"""
        max_check_distance = 5
        
        for distance in range(1, max_check_distance + 1):
            found_ocean = False
            
            # Check cells at this distance
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    if abs(dx) + abs(dy) != distance:
                        continue
                    
                    check_x, check_y = x + dx, y + dy
                    if (check_x, check_y) in self.cells:
                        check_cell = self.cells[(check_x, check_y)]
                        if check_cell.elevation < self.sea_level:
                            found_ocean = True
                            break
                
                if found_ocean:
                    break
            
            if found_ocean:
                return 1.0 - (distance / max_check_distance)
        
        return 0.0
    
    def _determine_climates(self):
        """Determine climate zones based on temperature and moisture"""
        for cell in self.cells.values():
            if cell.temperature > 0.7:
                climate = ClimateType.TROPICAL
            elif cell.temperature > 0.5:
                climate = ClimateType.TEMPERATE
            elif cell.temperature > 0.3:
                if cell.moisture < 0.3:
                    climate = ClimateType.ARID
                else:
                    climate = ClimateType.COLD
            else:
                climate = ClimateType.ARCTIC
            
            cell.climate = climate
    
    def _determine_biomes(self):
        """Determine biomes based on elevation, moisture, and temperature"""
        for cell in self.cells.values():
            cell.biome = determine_biome(cell.elevation, cell.moisture, cell.temperature)
    
    def print_map(self):
        """Console dump: prints macro map of glyphs matching biome types"""
        from tile import get_default_glyph_for_biome
        
        print(f"Macro Map ({self.width}x{self.height}):")
        print("=" * (self.width + 2))
        
        for y in range(self.height):
            row = "|"
            for x in range(self.width):
                cell = self.get_cell(x, y)
                if cell:
                    glyph = get_default_glyph_for_biome(cell.biome)
                    # Replace problematic characters for console output
                    if glyph in ['♠', '▲', '≈']:
                        glyph_map = {'♠': 'T', '▲': 'M', '≈': 'S'}
                        glyph = glyph_map.get(glyph, glyph)
                    row += glyph
                else:
                    row += " "
            row += "|"
            print(row)
        
        print("=" * (self.width + 2))
        print("Legend: ~ Ocean, . Land, ^ Hills, M Mountains, T Forest, S Swamp")
        print(f"Land cells: {len(self.get_land_cells())}, Water cells: {len(self.get_water_cells())}")
        print(f"Settlements: {len(self.get_settlements())}")
        print()
    
    def _classify_landforms(self):
        """Classify landforms based on surrounding terrain"""
        for cell in self.cells.values():
            if cell.elevation < self.sea_level:
                cell.landform = LandformType.OCEAN
            else:
                # Count neighboring land and water cells
                neighbors = self.get_neighbors(cell.x, cell.y)
                land_neighbors = sum(1 for n in neighbors if n.elevation >= self.sea_level)
                water_neighbors = len(neighbors) - land_neighbors
                
                if land_neighbors == 0:
                    cell.landform = LandformType.ATOLL
                elif water_neighbors >= 6:
                    cell.landform = LandformType.ISLAND
                elif water_neighbors >= 3:
                    cell.landform = LandformType.ARCHIPELAGO
                elif water_neighbors >= 1:
                    cell.landform = LandformType.PENINSULA
                else:
                    cell.landform = LandformType.CONTINENT
    
    def _generate_rivers(self):
        """Generate river systems flowing from high to low elevation"""
        river_sources = []
        
        # Find potential river sources (high elevation land cells)
        for cell in self.cells.values():
            if (cell.elevation > 0.6 and 
                cell.biome in [BiomeType.MOUNTAINS, BiomeType.HILLS] and
                cell.moisture > 0.4):
                river_sources.append(cell)
        
        # Generate rivers from sources
        for source in river_sources[:10]:  # Limit number of rivers
            self._trace_river(source)
    
    def _trace_river(self, source: MacroCell):
        """Trace a river from source to sea"""
        current = source
        visited = set()
        path_length = 0
        max_path_length = 50
        
        while path_length < max_path_length:
            if (current.x, current.y) in visited:
                break  # Avoid loops
            
            visited.add((current.x, current.y))
            current.has_river = True
            
            # Find the lowest neighboring cell
            neighbors = self.get_neighbors(current.x, current.y)
            lowest_neighbor = min(neighbors, key=lambda n: n.elevation, default=None)
            
            if (lowest_neighbor is None or 
                lowest_neighbor.elevation >= current.elevation or
                lowest_neighbor.elevation < self.sea_level):
                break  # Reached sea or dead end
            
            # Set river entry side for next cell
            dx = lowest_neighbor.x - current.x
            dy = lowest_neighbor.y - current.y
            
            if dx > 0:
                entry_side = "west"
            elif dx < 0:
                entry_side = "east"
            elif dy > 0:
                entry_side = "north"
            else:
                entry_side = "south"
            
            lowest_neighbor.river_entry_sides.add(entry_side)
            
            current = lowest_neighbor
            path_length += 1
    
    def _mark_sea_borders(self):
        """Mark cells that border the sea"""
        for cell in self.cells.values():
            if cell.elevation >= self.sea_level:
                neighbors = self.get_neighbors(cell.x, cell.y)
                if any(n.elevation < self.sea_level for n in neighbors):
                    cell.is_sea_border = True
    
    def _generate_settlements(self):
        """Generate settlements in suitable locations"""
        settlement_candidates = []
        
        for cell in self.cells.values():
            if (cell.elevation >= self.sea_level and
                cell.biome in [BiomeType.GRASSLAND, BiomeType.FOREST, BiomeType.BEACH] and
                (cell.is_sea_border or cell.has_river)):
                settlement_candidates.append(cell)
        
        # Select best candidates for settlements
        settlement_candidates.sort(key=lambda c: c.moisture + (0.5 if c.is_sea_border else 0), reverse=True)
        
        for i, cell in enumerate(settlement_candidates[:20]):  # Max 20 settlements
            base_population = self.rng.randint(100, 1000)
            population_bonus = 1.0 + (cell.moisture * 0.5)
            if cell.is_sea_border:
                population_bonus *= 1.5
            if cell.has_river:
                population_bonus *= 1.2
            
            cell.population = int(base_population * population_bonus)
            cell.wealth = cell.population * self.rng.uniform(0.5, 2.0)
    
    def get_cell(self, x: int, y: int) -> Optional[MacroCell]:
        """Get cell at coordinates"""
        return self.cells.get((x, y))
    
    def get_neighbors(self, x: int, y: int, distance: int = 1) -> List[MacroCell]:
        """Get neighboring cells within distance"""
        neighbors = []
        
        for dx in range(-distance, distance + 1):
            for dy in range(-distance, distance + 1):
                if dx == 0 and dy == 0:
                    continue
                
                neighbor_pos = (x + dx, y + dy)
                if neighbor_pos in self.cells:
                    neighbors.append(self.cells[neighbor_pos])
        
        return neighbors
    
    def get_land_cells(self) -> List[MacroCell]:
        """Get all land cells"""
        return [cell for cell in self.cells.values() if cell.elevation >= self.sea_level]
    
    def get_water_cells(self) -> List[MacroCell]:
        """Get all water cells"""
        return [cell for cell in self.cells.values() if cell.elevation < self.sea_level]
    
    def get_settlements(self) -> List[MacroCell]:
        """Get all cells with settlements"""
        return [cell for cell in self.cells.values() if cell.population > 0]