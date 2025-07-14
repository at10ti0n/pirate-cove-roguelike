# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a terminal/web-based 2D top-down pirate roguelike rendered entirely in CP437-style ASCII. The game features:

- Procedurally generated archipelago at macro (overworld) and micro (local chunks) scales
- Entity-Component-System (ECS) architecture for modularity and performance
- Radiant AI-inspired NPCs with utility scoring and behavior trees
- Living economy with farming, mining, crafting, and trade systems
- Ship and crew management with tactical naval combat
- Dynamic job posting and quest generation

## Architecture

### Core Structure
The codebase is organized around a robust ECS system with the following key modules:

- **ECS Core** (`ecs/`): Registry for entities/components, component definitions, core systems
- **AI System** (`ai/`): Radiant AI with utility scoring and behavior tree execution
- **Map Generation**: Macro world map and micro chunk generation with biomes, elevation, moisture
- **Resource Systems**: Farming, mining, and crafting with tile-based attributes
- **Economy**: Dynamic markets, trade routes, and NPC-driven commerce
- **Combat**: Naval (4-phase) and melee combat systems

### Key Systems Execution Order
Systems run in this fixed order each tick:
1. InputHandler → MovementSystem → AISystem → JobAssignmentSystem
2. EconomySystem → CraftingSystem → FarmingSystem → MiningSystem
3. CombatSystem → RenderSystem

### Data Flow
- Deterministic world generation from seed + command log
- Event bus for system decoupling (EntityMoved, EntityDefeated, etc.)
- Save/load via command replay with LZString compression

## Project Status

**Current State**: Project planning phase - only PRD documentation exists
- No source code has been implemented yet
- Architecture is fully specified in `/PRDs/overview.prd.md`
- Ready for implementation following the detailed technical specifications

## Development Commands

Since this is a Python project in planning phase, typical commands will be:

```bash
# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt

# Run the game (once main.py exists)
python src/main.py

# Run tests (once test suite exists)
python -m pytest tests/

# Code formatting and linting
python -m black src/
python -m flake8 src/
```

## Key Technical Decisions

- **Language**: Python with numpy, scipy, perlin-noise, lz-string dependencies
- **Rendering**: ASCII terminal with ANSI colors, 4-layer system (terrain, objects, characters, effects)
- **Performance Targets**: <200ms chunk generation, <10ms ECS tick, ≥60 FPS rendering
- **Determinism**: Seed + command log ensures reproducible game states
- **Save Format**: Compressed command replay for deterministic state restoration

## Implementation Phases

1. **Foundation** (Weeks 1-4): ECS registry, map generation, rendering, input
2. **Core Systems** (Weeks 5-8): Movement, AI, economy, job system
3. **Resource Layer** (Weeks 9-12): Farming, mining, crafting systems
4. **Crew & Combat** (Weeks 13-16): Crew management, naval/melee combat
5. **Quests & Polish** (Weeks 17-20): Quest system, fog-of-war, save/load
6. **Beta & Release** (Weeks 21-24): Testing, performance, documentation