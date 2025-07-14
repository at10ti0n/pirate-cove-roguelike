from dataclasses import dataclass
from typing import Any


# Foundation PRD Components: Position, Renderable, Velocity, TileInfo

@dataclass
class Position:
    x: float
    y: float
    layer: str = "ground"


@dataclass
class Renderable:
    glyph: str
    color: int = 37  # White ANSI color
    visible: bool = True
    render_layer: int = 0  # 0=terrain, 1=objects, 2=characters, 3=effects


@dataclass
class Velocity:
    dx: float = 0.0
    dy: float = 0.0


@dataclass
class TileInfo:
    """Component to hold tile information for entities"""
    x: int
    y: int
    tile_data: Any  # Reference to the actual Tile namedtuple
    passable: bool = True
    
    def is_water(self) -> bool:
        """Check if this tile is water-based"""
        from tile import BiomeType
        return self.tile_data.biome in [BiomeType.OCEAN, BiomeType.RIVER, BiomeType.LAKE]
    
    def is_land(self) -> bool:
        """Check if this tile is land"""
        return not self.is_water() and self.tile_data.height >= 0.0


# Foundation Phase Player Component - simplified
@dataclass
class Player:
    name: str = "Captain"