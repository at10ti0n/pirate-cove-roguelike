import sys
import os
from enum import Enum
from typing import Optional


class GameCommand(Enum):
    """High-level game commands emitted by input handler"""
    MOVE_NORTH = "move_north"
    MOVE_SOUTH = "move_south"
    MOVE_EAST = "move_east"
    MOVE_WEST = "move_west"
    TOGGLE_MODE = "toggle_mode"
    QUIT = "quit"
    INVALID = "invalid"


class InputHandler:
    """Handles keyboard input and converts to high-level game commands"""
    
    def __init__(self):
        self.platform = self._detect_platform()
        self.terminal_setup = False
        self._setup_terminal()
        
        # Key mappings
        self.key_map = {
            # WASD movement
            'w': GameCommand.MOVE_NORTH,
            'W': GameCommand.MOVE_NORTH,
            'a': GameCommand.MOVE_WEST,
            'A': GameCommand.MOVE_WEST,
            's': GameCommand.MOVE_SOUTH,
            'S': GameCommand.MOVE_SOUTH,
            'd': GameCommand.MOVE_EAST,
            'D': GameCommand.MOVE_EAST,
            
            # Special commands
            'm': GameCommand.TOGGLE_MODE,
            'M': GameCommand.TOGGLE_MODE,
            'q': GameCommand.QUIT,
            'Q': GameCommand.QUIT,
            
            # Arrow keys (will be handled separately due to escape sequences)
        }
        
        # Arrow key escape sequences
        self.arrow_sequences = {
            '\x1b[A': GameCommand.MOVE_NORTH,  # Up arrow
            '\x1b[B': GameCommand.MOVE_SOUTH,  # Down arrow
            '\x1b[C': GameCommand.MOVE_EAST,   # Right arrow
            '\x1b[D': GameCommand.MOVE_WEST,   # Left arrow
        }
    
    def _detect_platform(self) -> str:
        """Detect the current platform for input handling"""
        if os.name == 'nt':
            return 'windows'
        elif sys.platform in ['linux', 'darwin']:
            return 'unix'
        else:
            return 'fallback'
    
    def _setup_terminal(self):
        """Setup terminal for raw input if supported"""
        if self.platform == 'unix':
            try:
                import termios
                import tty
                # Test if we can actually use termios (some environments don't support it)
                if sys.stdin.isatty():
                    self.termios = termios
                    self.tty = tty
                    self.terminal_setup = True
                else:
                    print("Warning: Not running in a TTY, falling back to line input")
                    self.platform = 'fallback'
            except (ImportError, OSError):
                print("Warning: termios not available, falling back to line input")
                self.platform = 'fallback'
        
        elif self.platform == 'windows':
            try:
                import msvcrt
                self.msvcrt = msvcrt
                self.terminal_setup = True
            except ImportError:
                print("Warning: msvcrt not available, falling back to line input")
                self.platform = 'fallback'
    
    def get_command(self) -> GameCommand:
        """Get the next command from user input"""
        try:
            if self.platform == 'unix':
                return self._get_command_unix()
            elif self.platform == 'windows':
                return self._get_command_windows()
            else:
                return self._get_command_fallback()
        except KeyboardInterrupt:
            return GameCommand.QUIT
        except Exception as e:
            print(f"Input error: {e}")
            return GameCommand.INVALID
    
    def _get_command_unix(self) -> GameCommand:
        """Get command using Unix/Linux termios"""
        try:
            fd = sys.stdin.fileno()
            old_settings = self.termios.tcgetattr(fd)
            
            try:
                self.tty.setraw(sys.stdin.fileno())
                char = sys.stdin.read(1)
                
                # Handle escape sequences (arrow keys)
                if char == '\x1b':
                    # Read the next two characters for arrow keys
                    try:
                        seq = char + sys.stdin.read(2)
                        if seq in self.arrow_sequences:
                            return self.arrow_sequences[seq]
                    except:
                        pass
                    return GameCommand.INVALID
                
                # Handle regular characters
                if char in self.key_map:
                    return self.key_map[char]
                
                # Handle Ctrl+C
                if ord(char) == 3:  # Ctrl+C
                    return GameCommand.QUIT
                
                return GameCommand.INVALID
                
            finally:
                self.termios.tcsetattr(fd, self.termios.TCSADRAIN, old_settings)
                
        except (OSError, self.termios.error) as e:
            # Fall back to line input if termios fails
            print(f"Terminal error: {e}, falling back to line input")
            self.platform = 'fallback'
            return self._get_command_fallback()
    
    def _get_command_windows(self) -> GameCommand:
        """Get command using Windows msvcrt"""
        char = self.msvcrt.getch()
        
        # Handle special keys (arrow keys return 224 followed by direction code)
        if char == b'\xe0':  # Special key prefix
            char = self.msvcrt.getch()
            arrow_map = {
                b'H': GameCommand.MOVE_NORTH,  # Up arrow
                b'P': GameCommand.MOVE_SOUTH,  # Down arrow
                b'M': GameCommand.MOVE_EAST,   # Right arrow
                b'K': GameCommand.MOVE_WEST,   # Left arrow
            }
            return arrow_map.get(char, GameCommand.INVALID)
        
        # Handle regular characters
        try:
            char_str = char.decode('utf-8')
            if char_str in self.key_map:
                return self.key_map[char_str]
        except UnicodeDecodeError:
            pass
        
        return GameCommand.INVALID
    
    def _get_command_fallback(self) -> GameCommand:
        """Fallback command input using standard input"""
        print("Enter command (w/a/s/d to move, m to toggle mode, q to quit): ", end='', flush=True)
        try:
            line = input().strip().lower()
            if line in self.key_map:
                return self.key_map[line]
            
            # Handle arrow key names
            arrow_names = {
                'up': GameCommand.MOVE_NORTH,
                'down': GameCommand.MOVE_SOUTH,
                'left': GameCommand.MOVE_WEST,
                'right': GameCommand.MOVE_EAST,
                'north': GameCommand.MOVE_NORTH,
                'south': GameCommand.MOVE_SOUTH,
                'east': GameCommand.MOVE_EAST,
                'west': GameCommand.MOVE_WEST,
            }
            
            if line in arrow_names:
                return arrow_names[line]
            
            return GameCommand.INVALID
            
        except EOFError:
            return GameCommand.QUIT
    
    def cleanup(self):
        """Clean up terminal state"""
        # Terminal cleanup is handled automatically in Unix version
        # Windows doesn't need special cleanup
        pass
    
    def is_movement_command(self, command: GameCommand) -> bool:
        """Check if command is a movement command"""
        return command in [
            GameCommand.MOVE_NORTH,
            GameCommand.MOVE_SOUTH,
            GameCommand.MOVE_EAST,
            GameCommand.MOVE_WEST
        ]
    
    def get_movement_delta(self, command: GameCommand) -> tuple[int, int]:
        """Get the dx, dy movement delta for a movement command"""
        movement_deltas = {
            GameCommand.MOVE_NORTH: (0, -1),
            GameCommand.MOVE_SOUTH: (0, 1),
            GameCommand.MOVE_EAST: (1, 0),
            GameCommand.MOVE_WEST: (-1, 0),
        }
        return movement_deltas.get(command, (0, 0))
    
    def print_help(self):
        """Print help information about available commands"""
        help_text = """
Input Controls:
  Movement: W/A/S/D or Arrow Keys
    W/↑ : Move North
    A/← : Move West  
    S/↓ : Move South
    D/→ : Move East
  
  Special Commands:
    M : Toggle between Macro/Micro mode
    Q : Quit game
    
Mode Behavior:
  Micro Mode: Move player character around local area
  Macro Mode: Move cursor on world map to select area
        """
        print(help_text)


def test_input_handler():
    """Simple test function for the input handler"""
    handler = InputHandler()
    
    print("Input Handler Test")
    print("==================")
    handler.print_help()
    print("\nPress keys to test (Q to quit):")
    
    try:
        while True:
            command = handler.get_command()
            print(f"Command: {command.value}")
            
            if command == GameCommand.QUIT:
                break
            elif command == GameCommand.INVALID:
                print("Invalid key pressed")
            elif handler.is_movement_command(command):
                dx, dy = handler.get_movement_delta(command)
                print(f"Movement delta: ({dx}, {dy})")
            elif command == GameCommand.TOGGLE_MODE:
                print("Mode toggle requested")
    
    finally:
        handler.cleanup()
        print("\nTest completed.")


if __name__ == "__main__":
    test_input_handler()