from typing import List, Dict, Any
from dataclasses import dataclass
import time
import json


@dataclass
class GameCommand:
    """Represents a single game command for replay"""
    timestamp: float
    command_type: str
    data: Dict[str, Any]


class SaveManager:
    """Stub implementation for command logging and replay system
    
    Foundation PRD: Defines record_command(cmd) and replay_commands(cmd_list) stubs
    for later persistence. API in place; calling does not crash and logs commands in memory.
    """
    
    def __init__(self):
        self.command_log: List[GameCommand] = []
        self.session_start = time.time()
        self.enabled = True
    
    def record_command(self, command_type: str, data: Dict[str, Any] = None) -> bool:
        """Record a command to the in-memory log
        
        Args:
            command_type: Type of command (e.g., "move", "toggle_mode", "quit")
            data: Additional command data
            
        Returns:
            bool: True if command was recorded successfully
        """
        if not self.enabled:
            return False
        
        try:
            command = GameCommand(
                timestamp=time.time() - self.session_start,
                command_type=command_type,
                data=data or {}
            )
            self.command_log.append(command)
            return True
        except Exception as e:
            print(f"Warning: Failed to record command: {e}")
            return False
    
    def replay_commands(self, cmd_list: List[GameCommand]) -> bool:
        """Replay a list of commands (stub implementation)
        
        Args:
            cmd_list: List of commands to replay
            
        Returns:
            bool: True if replay was successful
        """
        if not cmd_list:
            return True
        
        try:
            print(f"Replaying {len(cmd_list)} commands...")
            for i, cmd in enumerate(cmd_list):
                print(f"  {i+1}: {cmd.command_type} at {cmd.timestamp:.2f}s")
                # In full implementation, this would actually execute the commands
                # For now, just log them
            
            print("Replay completed (stub implementation)")
            return True
        except Exception as e:
            print(f"Error during command replay: {e}")
            return False
    
    def get_command_log(self) -> List[GameCommand]:
        """Get a copy of the current command log"""
        return self.command_log.copy()
    
    def clear_log(self):
        """Clear the command log"""
        self.command_log.clear()
        self.session_start = time.time()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about the current session"""
        if not self.command_log:
            return {
                "total_commands": 0,
                "session_duration": 0.0,
                "commands_by_type": {}
            }
        
        # Count commands by type
        commands_by_type = {}
        for cmd in self.command_log:
            cmd_type = cmd.command_type
            commands_by_type[cmd_type] = commands_by_type.get(cmd_type, 0) + 1
        
        session_duration = time.time() - self.session_start
        
        return {
            "total_commands": len(self.command_log),
            "session_duration": session_duration,
            "commands_by_type": commands_by_type,
            "last_command_time": self.command_log[-1].timestamp if self.command_log else 0
        }
    
    def export_to_json(self) -> str:
        """Export command log to JSON format (for future persistence)"""
        try:
            export_data = {
                "session_start": self.session_start,
                "commands": [
                    {
                        "timestamp": cmd.timestamp,
                        "command_type": cmd.command_type,
                        "data": cmd.data
                    }
                    for cmd in self.command_log
                ]
            }
            return json.dumps(export_data, indent=2)
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return "{}"
    
    def import_from_json(self, json_data: str) -> bool:
        """Import command log from JSON format (for future persistence)"""
        try:
            data = json.loads(json_data)
            self.session_start = data.get("session_start", time.time())
            
            commands = []
            for cmd_data in data.get("commands", []):
                command = GameCommand(
                    timestamp=cmd_data["timestamp"],
                    command_type=cmd_data["command_type"],
                    data=cmd_data.get("data", {})
                )
                commands.append(command)
            
            self.command_log = commands
            return True
        except Exception as e:
            print(f"Error importing from JSON: {e}")
            return False
    
    def enable_logging(self):
        """Enable command logging"""
        self.enabled = True
    
    def disable_logging(self):
        """Disable command logging"""
        self.enabled = False
    
    def is_logging_enabled(self) -> bool:
        """Check if command logging is enabled"""
        return self.enabled


def test_save_manager():
    """Test the SaveManager stub implementation"""
    print("SaveManager Test")
    print("================")
    
    manager = SaveManager()
    
    # Test recording commands
    print("Recording test commands...")
    manager.record_command("move", {"direction": "north", "x": 5, "y": 10})
    manager.record_command("toggle_mode", {"from": "micro", "to": "macro"})
    manager.record_command("move", {"direction": "east", "x": 6, "y": 10})
    manager.record_command("quit", {})
    
    # Test getting stats
    stats = manager.get_session_stats()
    print(f"Session stats: {stats}")
    
    # Test getting command log
    log = manager.get_command_log()
    print(f"Recorded {len(log)} commands")
    
    # Test replay
    manager.replay_commands(log)
    
    # Test JSON export/import
    json_data = manager.export_to_json()
    print(f"Exported JSON: {len(json_data)} characters")
    
    # Test import
    new_manager = SaveManager()
    success = new_manager.import_from_json(json_data)
    print(f"Import successful: {success}")
    
    imported_log = new_manager.get_command_log()
    print(f"Imported {len(imported_log)} commands")
    
    print("\nTest completed.")


if __name__ == "__main__":
    test_save_manager()