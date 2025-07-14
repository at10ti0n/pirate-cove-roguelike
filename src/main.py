#!/usr/bin/env python3
"""
Pirate Cove Roguelike - Foundation Phase
Main game loop integrating ECS, map generation, rendering, and input handling
"""

import sys
import os
import argparse
import time
from typing import Optional, Dict, Tuple, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import foundation modules
from ecs.registry import Registry
from ecs.components import Position, Renderable, Player, TileInfo
from ecs.systems import MovementSystem, RenderSystem
from macro_map import MacroWorldMap
from map_generator import MapGenerator, ChunkCoords
from terminal_renderer import TerminalRenderer, RenderData
from input_handler import InputHandler, GameCommand
from save_manager import SaveManager
from tile import TileInfo as TileInfoClass, BiomeType


class GameMode:
    MICRO = "micro"
    MACRO = "macro"


class Game:
    """Main game class for the Foundation Phase"""
    
    def __init__(self, seed: Optional[int] = None):
        # Initialize core systems
        self.registry = Registry()
        self.save_manager = SaveManager()
        self.input_handler = InputHandler()
        self.renderer = TerminalRenderer(viewport_width=40, viewport_height=20)
        
        # Initialize world
        self.seed = seed or int(time.time())
        self.macro_map = MacroWorldMap(width=32, height=16, seed=self.seed)
        self.map_generator = MapGenerator(self.macro_map, chunk_size=32)
        
        # Game state
        self.mode = GameMode.MICRO
        self.running = True
        
        # Macro mode state
        self.macro_cursor_x = 16  # Start in center of macro map
        self.macro_cursor_y = 8
        
        # Micro mode state
        self.current_chunk_coords = ChunkCoords(self.macro_cursor_x, self.macro_cursor_y)
        self.current_chunk = None
        self.player_entity = None
        self.player_x = 16  # Center of 32x32 chunk
        self.player_y = 16
        
        # Initialize systems
        self.movement_system = MovementSystem(self.registry)
        self.render_system = RenderSystem(self.registry)
        
        # Setup initial game state
        self._setup_game()
    
    def _setup_game(self):
        """Initialize the game world and player"""
        print(f"Initializing Pirate Cove Roguelike (seed: {self.seed})...")
        
        # Generate initial chunk
        self._load_chunk(self.current_chunk_coords)
        
        # Create player entity
        self.player_entity = self.registry.create_entity()
        self.registry.add_component(
            self.player_entity,
            Position(x=float(self.player_x), y=float(self.player_y))
        )
        self.registry.add_component(
            self.player_entity,
            Renderable(glyph='@', color=37, visible=True, render_layer=2)
        )
        self.registry.add_component(
            self.player_entity,
            Player(name="Captain")
        )
        
        # Set camera to player position
        self.renderer.set_camera_position(self.player_x, self.player_y)
        
        print(f"Game initialized. Starting in {self.mode} mode.")
    
    def _load_chunk(self, coords: ChunkCoords):
        """Load a micro chunk"""
        print(f"Loading chunk at macro ({coords.macro_x}, {coords.macro_y})")
        self.current_chunk = self.map_generator.generate_chunk(coords)
        self.current_chunk_coords = coords
    
    def run(self):
        """Main game loop"""
        try:
            self._show_welcome()
            
            while self.running:
                self._update()
                self._render()
                self._handle_input()
                
        except KeyboardInterrupt:
            print("\nGame interrupted by user.")
        except Exception as e:
            print(f"\nGame error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._cleanup()
    
    def _show_welcome(self):
        """Show welcome message"""
        self.renderer._clear_screen()
        print("=" * 50)
        print("  PIRATE COVE ROGUELIKE - FOUNDATION PHASE")
        print("=" * 50)
        print(f"Seed: {self.seed}")
        print(f"Macro Map: {self.macro_map.width}x{self.macro_map.height}")
        print(f"Chunk Size: {self.map_generator.chunk_size}x{self.map_generator.chunk_size}")
        print()
        self.input_handler.print_help()
        print()
        print("Press any key to start...")
        self.input_handler.get_command()
    
    def _update(self):
        """Update game systems"""
        if self.mode == GameMode.MICRO:
            # Update ECS systems
            self.movement_system.update(dt=1.0)
            self.render_system.update(dt=1.0)
    
    def _render(self):
        """Render the current game state"""
        if self.mode == GameMode.MICRO:
            self._render_micro_mode()
        else:
            self._render_macro_mode()
    
    def _render_micro_mode(self):
        """Render micro mode (local chunk view)"""
        # Get entities for rendering
        entities = []
        for entity_id, (position, renderable) in self.registry.query(Position, Renderable):
            if renderable.visible:
                entities.append(RenderData(
                    x=int(position.x),
                    y=int(position.y),
                    glyph=renderable.glyph,
                    color=renderable.color,
                    layer=renderable.render_layer
                ))
        
        # Get current tile info for HUD
        current_tile = None
        if self.current_chunk and (self.player_x, self.player_y) in self.current_chunk:
            current_tile = self.current_chunk[(self.player_x, self.player_y)]
        
        # Prepare HUD info
        hud_info = {
            'player_x': self.player_x,
            'player_y': self.player_y,
            'current_tile': current_tile,
            'mode': self.mode,
        }
        
        # Render frame
        self.renderer.render_frame(
            tiles=self.current_chunk or {},
            entities=entities,
            player_pos=(self.player_x, self.player_y),
            hud_info=hud_info
        )
    
    def _render_macro_mode(self):
        """Render macro mode (world map view)"""
        self.renderer.render_macro_map(
            self.macro_map,
            self.macro_cursor_x,
            self.macro_cursor_y
        )
    
    def _handle_input(self):
        """Handle user input"""
        command = self.input_handler.get_command()
        
        # Log command
        self.save_manager.record_command(command.value, {
            'mode': self.mode,
            'timestamp': time.time()
        })
        
        if command == GameCommand.QUIT:
            self.running = False
        
        elif command == GameCommand.TOGGLE_MODE:
            self._toggle_mode()
        
        elif self.input_handler.is_movement_command(command):
            self._handle_movement(command)
        
        elif command == GameCommand.INVALID:
            # Don't do anything for invalid commands
            pass
    
    def _toggle_mode(self):
        """Toggle between micro and macro modes"""
        if self.mode == GameMode.MICRO:
            self.mode = GameMode.MACRO
            # Set macro cursor to current chunk position
            self.macro_cursor_x = self.current_chunk_coords.macro_x
            self.macro_cursor_y = self.current_chunk_coords.macro_y
        else:
            self.mode = GameMode.MICRO
            # Load chunk at cursor position if different
            new_coords = ChunkCoords(self.macro_cursor_x, self.macro_cursor_y)
            if (new_coords.macro_x != self.current_chunk_coords.macro_x or 
                new_coords.macro_y != self.current_chunk_coords.macro_y):
                self._load_chunk(new_coords)
                # Reset player position to center of new chunk
                self.player_x = 16
                self.player_y = 16
                # Update player entity position
                if self.player_entity:
                    pos_component = self.registry.get_component(self.player_entity, Position)
                    if pos_component:
                        pos_component.x = float(self.player_x)
                        pos_component.y = float(self.player_y)
                # Update camera
                self.renderer.set_camera_position(self.player_x, self.player_y)
    
    def _handle_movement(self, command: GameCommand):
        """Handle movement commands"""
        dx, dy = self.input_handler.get_movement_delta(command)
        
        if self.mode == GameMode.MACRO:
            # Move cursor on macro map
            new_x = max(0, min(self.macro_map.width - 1, self.macro_cursor_x + dx))
            new_y = max(0, min(self.macro_map.height - 1, self.macro_cursor_y + dy))
            self.macro_cursor_x = new_x
            self.macro_cursor_y = new_y
        
        else:
            # Move player in micro mode
            new_x = self.player_x + dx
            new_y = self.player_y + dy
            
            # Check chunk boundaries
            chunk_size = self.map_generator.chunk_size
            
            if new_x < 0 or new_x >= chunk_size or new_y < 0 or new_y >= chunk_size:
                # Need to transition to adjacent chunk
                self._handle_chunk_transition(new_x, new_y)
            else:
                # Move within current chunk
                self._move_player(new_x, new_y)
    
    def _move_player(self, new_x: int, new_y: int):
        """Move player to new position within current chunk"""
        # Check if position is passable
        if self.current_chunk and (new_x, new_y) in self.current_chunk:
            tile_info = self.current_chunk[(new_x, new_y)]
            if tile_info.passable:
                self.player_x = new_x
                self.player_y = new_y
                
                # Update player entity
                if self.player_entity:
                    pos_component = self.registry.get_component(self.player_entity, Position)
                    if pos_component:
                        pos_component.x = float(new_x)
                        pos_component.y = float(new_y)
                
                # Update camera
                self.renderer.set_camera_position(self.player_x, self.player_y)
    
    def _handle_chunk_transition(self, new_x: int, new_y: int):
        """Handle moving off the edge of current chunk"""
        chunk_size = self.map_generator.chunk_size
        
        # Calculate which adjacent chunk to move to
        macro_dx = 0
        macro_dy = 0
        
        if new_x < 0:
            macro_dx = -1
            new_x = chunk_size - 1
        elif new_x >= chunk_size:
            macro_dx = 1
            new_x = 0
        
        if new_y < 0:
            macro_dy = -1
            new_y = chunk_size - 1
        elif new_y >= chunk_size:
            macro_dy = 1
            new_y = 0
        
        # Calculate new macro coordinates
        new_macro_x = self.current_chunk_coords.macro_x + macro_dx
        new_macro_y = self.current_chunk_coords.macro_y + macro_dy
        
        # Check if new chunk is within macro map bounds
        if (0 <= new_macro_x < self.macro_map.width and 
            0 <= new_macro_y < self.macro_map.height):
            
            # Load new chunk
            new_coords = ChunkCoords(new_macro_x, new_macro_y)
            self._load_chunk(new_coords)
            
            # Move player to new position
            self._move_player(new_x, new_y)
    
    def _cleanup(self):
        """Clean up resources"""
        print("\nCleaning up...")
        
        # Show session stats
        stats = self.save_manager.get_session_stats()
        print(f"Session lasted {stats['session_duration']:.1f} seconds")
        print(f"Total commands: {stats['total_commands']}")
        
        # Cleanup systems
        self.input_handler.cleanup()
        self.renderer.cleanup()
        
        print("Thanks for playing Pirate Cove Roguelike!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Pirate Cove Roguelike - Foundation Phase')
    parser.add_argument('--seed', type=int, help='Random seed for world generation')
    parser.add_argument('--demo', action='store_true', help='Run demo mode (show macro map)')
    
    args = parser.parse_args()
    
    if args.demo:
        # Demo mode: just show the macro map
        print("Demo Mode: Generating and displaying macro map...")
        macro_map = MacroWorldMap(width=32, height=16, seed=args.seed)
        macro_map.print_map()
        return
    
    # Run the game
    game = Game(seed=args.seed)
    game.run()


if __name__ == "__main__":
    main()