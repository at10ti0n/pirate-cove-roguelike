import os
import sys
import shutil
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
    def __init__(self, viewport_width: int = None, viewport_height: int = None):
        # Detect terminal size if not provided
        if viewport_width is None or viewport_height is None:
            term_size = self._get_terminal_size()
            if viewport_width is None:
                viewport_width = term_size[0]
            if viewport_height is None:
                viewport_height = term_size[1]
        
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
        
        # Print initialization info
        print(f"Terminal Renderer initialized: {self.viewport_width}x{self.viewport_height} viewport")
    
    def resize_if_needed(self):
        """Check if terminal has been resized and update accordingly"""
        try:
            new_width, new_height = self._get_terminal_size()
            if (new_width != self.viewport_width or new_height != self.viewport_height):
                self.viewport_width = new_width
                self.viewport_height = new_height
                self.total_height = new_height + self.hud_height
                self._clear_screen()
                print(f"Terminal resized to: {self.viewport_width}x{self.viewport_height}")
                return True
        except Exception:
            pass
        return False
    
    def _get_terminal_size(self) -> Tuple[int, int]:
        """Get current terminal size, with fallback to defaults"""
        try:
            size = shutil.get_terminal_size()
            # Reserve space for HUD (5 lines) and some padding
            usable_height = max(10, size.lines - 7)  # Minimum 10 lines, leave 7 for HUD and padding
            usable_width = max(40, size.columns - 2)  # Minimum 40 chars, leave 2 for borders
            return usable_width, usable_height
        except Exception:
            # Fallback to original size if detection fails
            return 40, 20
    
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
        
        # Clear screen using actual viewport width
        for y in range(self.total_height):
            self._move_cursor(0, y)
            print(' ' * self.viewport_width, flush=True)
        
        # Calculate scaling and centering
        scale_x, scale_y, offset_x, offset_y = self._calculate_macro_scaling(macro_map)
        
        # Render macro map title
        self._move_cursor(0, 0)
        title = f'Macro Map View ({macro_map.width}x{macro_map.height}) - Scale: {scale_x}x{scale_y}'
        print(title, flush=True)
        
        # Render the scaled macro map
        for screen_y in range(offset_y, min(self.viewport_height - 2, offset_y + macro_map.height * scale_y)):
            self._move_cursor(0, screen_y + 1)
            row = " " * offset_x  # Left padding
            visual_width = offset_x  # Track actual visual width (without ANSI codes)
            
            for world_x in range(macro_map.width):
                # Check if we have room for this cell's scaled width
                if visual_width + scale_x > self.viewport_width:
                    break
                    
                world_y = (screen_y - offset_y) // scale_y
                if 0 <= world_y < macro_map.height:
                    cell = macro_map.get_cell(world_x, world_y)
                    if cell:
                        glyph = self._get_macro_glyph(cell)
                        
                        # Highlight cursor position
                        if world_x == cursor_x and world_y == cursor_y:
                            glyph_display = f'\033[7m{glyph}\033[0m'  # Reverse video
                        else:
                            color = get_default_color_for_biome(cell.biome)
                            glyph_display = f'\033[{color}m{glyph}\033[0m'
                        
                        # Add scaling (repeat glyph if scale > 1)
                        for sx in range(scale_x):
                            row += glyph_display
                        visual_width += scale_x
                    else:
                        # Empty cell
                        row += ' ' * scale_x
                        visual_width += scale_x
            
            print(row, flush=True)
        
        # Render macro HUD
        self.render_macro_hud(macro_map, cursor_x, cursor_y)
    
    def _calculate_macro_scaling(self, macro_map):
        """Calculate scaling and centering for macro map"""
        # Calculate maximum scale that fits in viewport
        max_scale_x = max(1, (self.viewport_width - 4) // macro_map.width)
        max_scale_y = max(1, (self.viewport_height - 4) // macro_map.height)
        
        # Use the smaller scale to maintain aspect ratio
        scale = min(max_scale_x, max_scale_y)
        scale_x = scale_y = scale
        
        # Calculate centering offsets
        total_width = macro_map.width * scale_x
        total_height = macro_map.height * scale_y
        offset_x = max(0, (self.viewport_width - total_width) // 2)
        offset_y = max(0, (self.viewport_height - total_height - 2) // 2)  # -2 for title
        
        return scale_x, scale_y, offset_x, offset_y
    
    def _get_macro_glyph(self, cell):
        """Get the appropriate glyph for a macro cell"""
        if cell.biome == BiomeType.OCEAN:
            return '~'
        elif cell.biome == BiomeType.BEACH:
            return '.'
        elif cell.biome == BiomeType.HILLS:
            return '^'
        elif cell.biome == BiomeType.MOUNTAINS:
            return 'M'
        elif cell.biome == BiomeType.FOREST:
            return 'T'
        elif cell.biome == BiomeType.SWAMP:
            return 'S'
        elif cell.biome == BiomeType.DESERT:
            return '~'
        elif cell.biome == BiomeType.TUNDRA:
            return '.'
        elif cell.biome == BiomeType.TAIGA:
            return 'T'
        else:
            return '.'
    
    def render_macro_hud(self, macro_map, cursor_x: int, cursor_y: int):
        """Render the macro mode HUD"""
        # Render macro HUD
        hud_start_y = self.viewport_height
        self._move_cursor(0, hud_start_y)
        print('=' * self.viewport_width, flush=True)
        
        self._move_cursor(0, hud_start_y + 1)
        print(f'Cursor: ({cursor_x}, {cursor_y})', flush=True)
        
        self._move_cursor(0, hud_start_y + 2)
        selected_cell = macro_map.get_cell(cursor_x, cursor_y)
        if selected_cell:
            cell_info = f'Cell: {selected_cell.biome.value.title()}'
            if hasattr(selected_cell, 'elevation'):
                cell_info += f' (E:{selected_cell.elevation:.2f})'
            print(cell_info, flush=True)
        
        self._move_cursor(0, hud_start_y + 3)
        print('Mode: macro | WASD: Move Cursor | M: Enter Micro | Q: Quit', flush=True)