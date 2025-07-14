import os
import sys
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from tile import BiomeType, get_default_color_for_biome
from ecs.components import Position, Renderable


@dataclass
class RenderData:
    x: int
    y: int
    glyph: str
    color: int
    layer: int = 0


class TerminalRenderer:
    def __init__(self, viewport_width: int = 40, viewport_height: int = 20):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.hud_height = 5
        self.total_height = viewport_height + self.hud_height
        
        # Camera position (center of viewport in world coordinates)
        self.camera_x = 0
        self.camera_y = 0
        
        # Color support detection
        self.color_support = self._detect_color_support()
        
        # Clear screen and setup
        self._clear_screen()
        self._hide_cursor()
    
    def _detect_color_support(self) -> bool:
        """Detect if terminal supports ANSI colors"""
        return (os.getenv('TERM', '').find('color') != -1 or 
                os.getenv('COLORTERM') is not None or
                sys.platform != 'win32')
    
    def _clear_screen(self):
        """Clear the terminal screen"""
        if os.name == 'nt':  # Windows
            os.system('cls')
        else:  # Unix/Linux/MacOS
            os.system('clear')
            
    def _hide_cursor(self):
        """Hide the terminal cursor"""
        if self.color_support:
            print('\033[?25l', end='', flush=True)
    
    def _show_cursor(self):
        """Show the terminal cursor"""
        if self.color_support:
            print('\033[?25h', end='', flush=True)
    
    def _move_cursor(self, x: int, y: int):
        """Move cursor to position"""
        if self.color_support:
            print(f'\033[{y+1};{x+1}H', end='', flush=True)
    
    def _set_color(self, color: int):
        """Set foreground color using ANSI codes"""
        if self.color_support:
            print(f'\033[{color}m', end='', flush=True)
    
    def _reset_color(self):
        """Reset color to default"""
        if self.color_support:
            print('\033[0m', end='', flush=True)
    
    def set_camera_position(self, world_x: float, world_y: float):
        """Set camera center position in world coordinates"""
        self.camera_x = int(world_x)
        self.camera_y = int(world_y)
    
    def world_to_screen(self, world_x: int, world_y: int) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates"""
        # Calculate camera top-left corner
        cam_left = self.camera_x - self.viewport_width // 2
        cam_top = self.camera_y - self.viewport_height // 2
        
        screen_x = world_x - cam_left
        screen_y = world_y - cam_top
        
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """Convert screen coordinates to world coordinates"""
        # Calculate camera top-left corner
        cam_left = self.camera_x - self.viewport_width // 2
        cam_top = self.camera_y - self.viewport_height // 2
        
        world_x = screen_x + cam_left
        world_y = screen_y + cam_top
        
        return world_x, world_y
    
    def render_frame(self, tiles: Dict[Tuple[int, int], Any], 
                    entities: List[RenderData], 
                    player_pos: Optional[Tuple[int, int]] = None,
                    hud_info: Dict[str, Any] = None):
        """Render a complete frame"""
        # Clear screen
        self._move_cursor(0, 0)
        
        # Render map viewport
        self._render_viewport(tiles, entities, player_pos)
        
        # Render HUD
        self._render_hud(hud_info or {})
        
        # Reset cursor position
        self._move_cursor(0, self.total_height)
        self._reset_color()
    
    def _render_viewport(self, tiles: Dict[Tuple[int, int], Any], 
                        entities: List[RenderData],
                        player_pos: Optional[Tuple[int, int]] = None):
        """Render the main viewport showing the game world"""
        # Calculate viewport bounds in world coordinates
        cam_left = self.camera_x - self.viewport_width // 2
        cam_top = self.camera_y - self.viewport_height // 2
        cam_right = cam_left + self.viewport_width
        cam_bottom = cam_top + self.viewport_height
        
        # Create screen buffer
        screen_buffer = {}
        color_buffer = {}
        
        # Fill with default tiles first
        for screen_y in range(self.viewport_height):
            for screen_x in range(self.viewport_width):
                world_x, world_y = self.screen_to_world(screen_x, screen_y)
                
                # Check if we have tile data for this position
                if (world_x, world_y) in tiles:
                    tile_info = tiles[(world_x, world_y)]
                    screen_buffer[(screen_x, screen_y)] = tile_info.tile.glyph
                    color_buffer[(screen_x, screen_y)] = get_default_color_for_biome(tile_info.tile.biome)
                else:
                    # Default to ocean for unmapped areas
                    screen_buffer[(screen_x, screen_y)] = '~'
                    color_buffer[(screen_x, screen_y)] = get_default_color_for_biome(BiomeType.OCEAN)
        
        # Render entities on top of tiles
        for entity in entities:
            screen_x, screen_y = self.world_to_screen(entity.x, entity.y)
            if (0 <= screen_x < self.viewport_width and 
                0 <= screen_y < self.viewport_height):
                screen_buffer[(screen_x, screen_y)] = entity.glyph
                color_buffer[(screen_x, screen_y)] = entity.color
        
        # Render player on top if specified
        if player_pos:
            player_screen_x, player_screen_y = self.world_to_screen(player_pos[0], player_pos[1])
            if (0 <= player_screen_x < self.viewport_width and 
                0 <= player_screen_y < self.viewport_height):
                screen_buffer[(player_screen_x, player_screen_y)] = '@'
                color_buffer[(player_screen_x, player_screen_y)] = 37  # White
        
        # Draw the screen buffer
        for screen_y in range(self.viewport_height):
            self._move_cursor(0, screen_y)
            row = ""
            current_color = None
            
            for screen_x in range(self.viewport_width):
                glyph = screen_buffer.get((screen_x, screen_y), ' ')
                color = color_buffer.get((screen_x, screen_y), 37)
                
                # Only change color if it's different from current
                if color != current_color:
                    if current_color is not None:
                        row += '\033[0m'  # Reset color
                    row += f'\033[{color}m'  # Set new color
                    current_color = color
                
                row += glyph
            
            row += '\033[0m'  # Reset color at end of line
            print(row, flush=True)
    
    def _render_hud(self, hud_info: Dict[str, Any]):
        """Render the HUD below the viewport"""
        hud_start_y = self.viewport_height
        
        # Clear HUD area first
        for y in range(self.hud_height):
            self._move_cursor(0, hud_start_y + y)
            print(' ' * 80, flush=True)  # Clear line
        
        # Render HUD content
        self._move_cursor(0, hud_start_y)
        print('=' * self.viewport_width, flush=True)
        
        # Player coordinates
        player_x = hud_info.get('player_x', 0)
        player_y = hud_info.get('player_y', 0)
        self._move_cursor(0, hud_start_y + 1)
        print(f'Position: ({player_x}, {player_y})', flush=True)
        
        # Current tile info
        current_tile = hud_info.get('current_tile')
        if current_tile:
            self._move_cursor(0, hud_start_y + 2)
            tile_data = current_tile.tile if hasattr(current_tile, 'tile') else current_tile
            biome_name = tile_data.biome.value.title() if hasattr(tile_data, 'biome') else 'Unknown'
            height = getattr(tile_data, 'height', 0.0)
            moisture = getattr(tile_data, 'moisture', 0.0)
            print(f'Tile: {biome_name} (H:{height:.2f} M:{moisture:.2f})', flush=True)
        
        # Camera position
        self._move_cursor(0, hud_start_y + 3)
        print(f'Camera: ({self.camera_x}, {self.camera_y})', flush=True)
        
        # Controls
        self._move_cursor(0, hud_start_y + 4)
        mode = hud_info.get('mode', 'micro')
        print(f'Mode: {mode} | WASD: Move | M: Toggle Mode | Q: Quit', flush=True)
    
    def cleanup(self):
        """Clean up terminal state"""
        self._show_cursor()
        self._reset_color()
        print('\n')
    
    def render_macro_map(self, macro_map, cursor_x: int, cursor_y: int):
        """Render the macro map view with cursor"""
        self._move_cursor(0, 0)
        
        # Clear screen
        for y in range(self.total_height):
            self._move_cursor(0, y)
            print(' ' * 80, flush=True)
        
        # Render macro map
        self._move_cursor(0, 0)
        print(f'Macro Map View ({macro_map.width}x{macro_map.height})', flush=True)
        
        for y in range(min(macro_map.height, self.viewport_height - 2)):
            self._move_cursor(0, y + 1)
            row = ""
            for x in range(min(macro_map.width, self.viewport_width)):
                cell = macro_map.get_cell(x, y)
                if cell:
                    glyph = '~' if cell.biome == BiomeType.OCEAN else '.'
                    if cell.biome in [BiomeType.HILLS, BiomeType.MOUNTAINS]:
                        glyph = '^' if cell.biome == BiomeType.HILLS else 'M'
                    elif cell.biome == BiomeType.FOREST:
                        glyph = 'T'
                    elif cell.biome == BiomeType.SWAMP:
                        glyph = 'S'
                    
                    # Highlight cursor position
                    if x == cursor_x and y == cursor_y:
                        row += f'\033[7m{glyph}\033[0m'  # Reverse video
                    else:
                        color = get_default_color_for_biome(cell.biome)
                        row += f'\033[{color}m{glyph}\033[0m'
                else:
                    row += ' '
            print(row, flush=True)
        
        # Render macro HUD
        hud_start_y = self.viewport_height
        self._move_cursor(0, hud_start_y)
        print('=' * self.viewport_width, flush=True)
        
        self._move_cursor(0, hud_start_y + 1)
        print(f'Cursor: ({cursor_x}, {cursor_y})', flush=True)
        
        self._move_cursor(0, hud_start_y + 2)
        selected_cell = macro_map.get_cell(cursor_x, cursor_y)
        if selected_cell:
            print(f'Cell: {selected_cell.biome.value.title()}', flush=True)
        
        self._move_cursor(0, hud_start_y + 3)
        print('Mode: macro | WASD: Move Cursor | M: Enter Micro | Q: Quit', flush=True)