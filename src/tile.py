from collections import namedtuple
from enum import Enum
from typing import Dict, Any, Optional


class BiomeType(Enum):
    OCEAN = "ocean"
    BEACH = "beach"
    GRASSLAND = "grassland"
    FOREST = "forest"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    SWAMP = "swamp"
    DESERT = "desert"
    JUNGLE = "jungle"
    TUNDRA = "tundra"
    RIVER = "river"
    LAKE = "lake"


class ClimateType(Enum):
    TROPICAL = "tropical"
    TEMPERATE = "temperate"
    ARID = "arid"
    COLD = "cold"
    ARCTIC = "arctic"


# Foundation PRD specification: Tile = namedtuple("Tile", ["glyph","biome","height","moisture"])
Tile = namedtuple("Tile", ["glyph", "biome", "height", "moisture"])


class TileInfo:
    """Extended tile information for internal use"""
    def __init__(self, x: int, y: int, tile: Tile, 
                 temperature: float = 0.5, passable: bool = True,
                 resource_type: Optional[str] = None, resource_quantity: int = 0):
        self.x = x
        self.y = y
        self.tile = tile
        self.temperature = temperature
        self.passable = passable
        self.resource_type = resource_type
        self.resource_quantity = resource_quantity
        self.attributes: Dict[str, Any] = {}
    
    def is_water(self) -> bool:
        """Check if this tile is water"""
        return self.tile.biome in [BiomeType.OCEAN, BiomeType.RIVER, BiomeType.LAKE]
    
    def is_land(self) -> bool:
        """Check if this tile is land"""
        return not self.is_water() and self.tile.height >= 0.0
    
    def can_farm(self) -> bool:
        """Check if this tile is suitable for farming"""
        return (self.is_land() and 
                self.tile.biome in [BiomeType.GRASSLAND, BiomeType.FOREST, BiomeType.SWAMP] and
                self.tile.moisture > 0.3 and 
                self.tile.height < 0.8)
    
    def can_mine(self) -> bool:
        """Check if this tile is suitable for mining"""
        return (self.is_land() and 
                self.tile.biome in [BiomeType.HILLS, BiomeType.MOUNTAINS] and
                self.tile.height > 0.4)
    
    def can_build(self) -> bool:
        """Check if this tile is suitable for building"""
        return (self.is_land() and 
                self.passable and 
                self.tile.biome not in [BiomeType.SWAMP] and
                self.tile.height < 0.7)  # Mountains too high for building
    
    def get_fertility(self) -> float:
        """Get farming fertility based on biome, moisture, and elevation"""
        if not self.can_farm():
            return 0.0
        
        base_fertility = {
            BiomeType.GRASSLAND: 0.8,
            BiomeType.FOREST: 0.6,
            BiomeType.SWAMP: 1.0,
        }.get(self.tile.biome, 0.0)
        
        # Adjust for moisture and elevation
        moisture_bonus = min(1.0, self.tile.moisture * 1.5)
        elevation_penalty = max(0.0, 1.0 - (self.tile.height * 2))
        
        return base_fertility * moisture_bonus * elevation_penalty
    
    def get_mining_richness(self) -> float:
        """Get mining richness based on biome and elevation"""
        if not self.can_mine():
            return 0.0
        
        base_richness = {
            BiomeType.HILLS: 0.6,
            BiomeType.MOUNTAINS: 1.0,
        }.get(self.tile.biome, 0.0)
        
        # Higher elevation = richer veins
        elevation_bonus = min(2.0, self.tile.height * 2)
        
        return base_richness * elevation_bonus
    
    def set_resource(self, resource_type: str, quantity: int):
        """Set resource on this tile"""
        self.resource_type = resource_type
        self.resource_quantity = quantity
    
    def harvest_resource(self, amount: int) -> int:
        """Harvest resource from this tile, returns actual amount harvested"""
        if not self.resource_type or self.resource_quantity <= 0:
            return 0
        
        harvested = min(amount, self.resource_quantity)
        self.resource_quantity -= harvested
        
        if self.resource_quantity <= 0:
            self.resource_type = None
            self.resource_quantity = 0
        
        return harvested


def get_default_glyph_for_biome(biome: BiomeType) -> str:
    """Get default glyph for biome"""
    biome_glyphs = {
        BiomeType.OCEAN: '~',
        BiomeType.BEACH: '.',
        BiomeType.GRASSLAND: '.',
        BiomeType.FOREST: '♠',
        BiomeType.HILLS: '^',
        BiomeType.MOUNTAINS: '▲',
        BiomeType.SWAMP: '≈',
        BiomeType.DESERT: '~',
        BiomeType.JUNGLE: '♠',
        BiomeType.TUNDRA: '.',
        BiomeType.RIVER: '~',
        BiomeType.LAKE: '~',
    }
    return biome_glyphs.get(biome, '.')


def get_default_color_for_biome(biome: BiomeType) -> int:
    """Get default ANSI color for biome"""
    biome_colors = {
        BiomeType.OCEAN: 34,      # Blue
        BiomeType.BEACH: 33,      # Yellow
        BiomeType.GRASSLAND: 32,  # Green
        BiomeType.FOREST: 32,     # Green
        BiomeType.HILLS: 33,      # Yellow
        BiomeType.MOUNTAINS: 37,  # White
        BiomeType.SWAMP: 36,      # Cyan
        BiomeType.DESERT: 33,     # Yellow
        BiomeType.JUNGLE: 92,     # Bright Green
        BiomeType.TUNDRA: 97,     # Bright White
        BiomeType.RIVER: 96,      # Bright Cyan
        BiomeType.LAKE: 34,       # Blue
    }
    return biome_colors.get(biome, 37)


def determine_biome(height: float, moisture: float, temperature: float) -> BiomeType:
    """Determine biome based on height (elevation), moisture, and temperature"""
    # Water biomes
    if height < 0.0:
        return BiomeType.OCEAN
    elif height < 0.1:
        return BiomeType.BEACH
    
    # Land biomes based on temperature and moisture
    if temperature < 0.2:  # Cold
        if moisture > 0.7:
            return BiomeType.TUNDRA
        else:
            return BiomeType.TUNDRA
    
    elif temperature < 0.4:  # Cool
        if moisture > 0.6:
            return BiomeType.FOREST
        elif moisture > 0.3:
            return BiomeType.GRASSLAND
        else:
            return BiomeType.HILLS
    
    elif temperature < 0.7:  # Temperate
        if height > 0.7:
            return BiomeType.MOUNTAINS
        elif height > 0.5:
            return BiomeType.HILLS
        elif moisture > 0.7:
            return BiomeType.FOREST
        elif moisture > 0.6:
            return BiomeType.SWAMP
        elif moisture > 0.3:
            return BiomeType.GRASSLAND
        else:
            return BiomeType.DESERT
    
    else:  # Hot
        if height > 0.6:
            return BiomeType.MOUNTAINS
        elif moisture > 0.8:
            return BiomeType.JUNGLE
        elif moisture > 0.6:
            return BiomeType.SWAMP
        elif moisture > 0.2:
            return BiomeType.GRASSLAND
        else:
            return BiomeType.DESERT