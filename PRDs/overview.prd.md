Title

Pirate-Themed ASCII Roguelike with Radiant AI, Island Economy & Tiered Resource Systems

⸻

1. Overview

A terminal/web-based 2D top-down pirate roguelike rendered entirely in CP437-style ASCII. Players explore a procedurally generated archipelago at two scales—macro overworld and micro local chunks—while managing a ship and crew, forging dynamic relationships with Radiant AI–driven NPCs, and engaging in a living economy of farming, mining, crafting, and trade. A robust Entity–Component–System (ECS) backbone ensures modularity, performance, and emergent complexity.

⸻

2. Goals & Scope

2.1 Primary Objectives
	1.	World Generation
	•	Infinite or very large archipelago of macro cells with climates, biomes, landforms, and rivers.
	•	Each macro cell deterministically spawns micro chunks for detailed exploration.
	2.	Emergent AI
	•	NPC agents powered by a Radiant AI–inspired hybrid utility-and-behavior-tree system.
	3.	Resource Ecosystem
	•	Farming, mining, and crafting driven by tile attributes (elevation, moisture, climate, biome).
	4.	Economy & Trade
	•	Settlement markets, dynamic job postings, and NPC-run trade vessels.
	5.	Crew & Combat
	•	Tactical naval and melee combat with crew roles, morale events, and resource-driven repairs.

2.2 Out of Scope (MVP)
	•	Full graphical UI (text-only ASCII).
	•	Multiplayer synchronization.

⸻

3. File & Module Structure

/src
  main.py                   # Entry point: game loop, state transitions
  macro_map.py              # MacroWorldMap: macro grid, climate, biomes, rivers
  map_generator.py          # MapGenerator: micro-chunk noise, rivers, tiles
  tile.py                   # Tile struct (glyph, biome, elevation, moisture)
  terminal_renderer.py      # ASCII rendering engine with layers & fog-of-war
  input_handler.py          # Keyboard/touch abstraction

  ecs/
    registry.py             # ECS registry: entities, components, queries
    components.py           # Component definitions (Position, AIState, etc.)
    systems.py              # Core systems (Movement, Rendering, AI, Economy...)

  ai/
    radiant_ai.py           # Utility scoring + behavior tree execution
    goals.py                # Goal templates and instantiation

  crew.py                   # CrewMember & ShipComponent, CrewSystem
  economy.py                # MarketModel & EconomySystem
  job_system.py             # Dynamic job posting & assignment
  quest_system.py           # Procedural quest generation & tracking
  crafting_system.py        # Crafting recipes, workstations, CraftingSystem
  farming_system.py         # Plot generation, crop cycles, FarmingSystem
  mining_system.py          # Ore vein generation, mine jobs, MiningSystem
  save_manager.py           # Save/load manager (command-replay + compression)
requirements.txt            # numpy, scipy, perlin-noise, lz-string
/tests                      # Unit tests for mapgen, ECS, AI, and resource systems


⸻

4. Functional Requirements

4.1 Macro & Micro Map Generation
	•	MacroWorldMap (macro_map.py): grid of W×H macro cells with elevation, moisture, climate, biome, landform, sea borders, and river metadata (entry_sides, source_pos).
	•	MapGenerator (map_generator.py): produces w×h micro chunks blending local and neighboring macro data, applies FBM elevation + hydraulic erosion, moisture noise, biome assignment, and river carving with exit points.

4.2 ASCII Rendering & Input
	•	TerminalRenderer: four layers (terrain, objects, characters, effects), ANSI colors, fog-of-war, HUD with coordinates and tile info.
	•	InputHandler: keyboard (WASD/arrow keys, q to quit, m to toggle modes), touch zones for mobile/web.

4.3 Radiant AI–Inspired NPCs
	•	Traits & Needs: hunger, fatigue, morale, loyalty, skills, relationships.
	•	Goal System: generate goals from world state (settlement deficits, personal needs, events).
	•	Utility Scoring + Behavior Trees (ai/): score candidate goals and decompose into task sequences (WalkTo, ChopTree, HarvestCrop, MineOre, CraftItem, Trade, Rest).
	•	Schedules: daily routines (work, eat, socialize, rest).

4.4 Crew & Ship Management
	•	CrewMember Component: role (Sailor, Gunner, Carpenter, Cook), stats (STR, DEX, morale, loyalty), needs.
	•	ShipComponent: hull integrity, sails, cannons, cargo capacity.
	•	CrewSystem: assign crew to tasks (gunning, sailing, repairs), morale checks (mutiny risk), disease/injury events, skill progression.

4.5 Island Economy & Trade
	•	MarketModel (economy.py): per-settlement resource stocks, dynamic pricing by supply/demand with jitter.
	•	Trade Routes: NPC traders spawn ships with cargo, sail between ports.
	•	EconomySystem: updates markets hourly, spawns trade jobs, reacts to storm/pirate events.

4.6 Job & Quest System
	•	JobSystem (job_system.py): post jobs for resource deficits, construction, transport; assign to NPCs.
	•	QuestSystem (quest_system.py): procedural templates (treasure hunts, escort missions, combat), instantiate with world-specific parameters, track objectives and rewards.

4.7 Combat Systems
	•	NavalCombat: four-phase (Approach, Cannon, Boarding, Melee) on ASCII ship deck grid.
	•	MeleeCombat: turn-based grid combat, injuries, morale effects.
	•	CombatSystem: resolves rounds, applies damage, loot, events.

4.8 Save/Load System
	•	SaveManager (save_manager.py): record seed + timestamp + serialized command log, compress with LZString, store in localStorage or file.
	•	Load: decompress and replay commands to restore deterministic state.

4.9 Crafting, Farming & Mining Systems
	•	CraftingSystem (crafting_system.py): data-driven recipes (inputs, tools, workstations, outputs), spawn crafting jobs, consume inputs, produce items.
	•	FarmingSystem (farming_system.py): plot placement in eligible biomes (grassland, swamp, coastal), crop growth cycles by moisture/climate/elevation, watering and harvest jobs, yield scaling.
	•	MiningSystem (mining_system.py): ore vein placement in mountain/hill tiles by elevation/moisture, mine jobs requiring tools, vein depletion and rubble, integrate smelting via CraftingSystem.

⸻

5. Entity–Component–System Architecture

5.1 Registry & Entity Lifecycle

class Registry:
    def __init__(self):
        self._next_id = 1
        self._entities = set()
        self._components: Dict[Type, Dict[int, Any]] = {}
    def create_entity(self) -> int: ...
    def destroy_entity(self, eid: int): ...
    def add_component(self, eid: int, comp: Any): ...
    def remove_component(self, eid: int, comp_type: Type): ...
    def get_component(self, eid: int, comp_type: Type): ...
    def query(self, *comp_types: Type) -> Iterable[Tuple[int, List[Any]]]: ...

	•	Responsibilities: Manage entity IDs, component storage, queries, and optional event dispatch.

5.2 Components

Pure data classes—examples:

@dataclass
class Position: x: float; y: float; layer: str
@dataclass
class Renderable: glyph: str; color: int; visible: bool
@dataclass
class AIState: current_goal: Goal; memory: dict; personality: Personality
@dataclass
class Job: type: str; target: Any; progress: float; reward: dict
# ... CrewMember, ShipComponent, Market, ResourceNode, FarmPlot, MineNode, Health, etc.

5.3 Systems

Systems pull matching entities and operate on components:
	•	MovementSystem

for eid, (pos, vel) in reg.query(Position, Velocity):
    pos.x += vel.dx * dt; pos.y += vel.dy * dt
    event_bus.emit(EntityMoved(eid, pos))


	•	RenderSystem
Collect (layer, y, x, color, glyph) tuples, sort by layer, draw via terminal_renderer.
	•	AISystem
For each (AIState, Position, Inventory): evaluate new goals, decompose to Job components.
	•	JobAssignmentSystem
Match jobs to agents by proximity and skill.
	•	EconomySystem
Update Market components: prices ← base × (demand/supply) ± random jitter.
	•	CraftingSystem, FarmingSystem, MiningSystem
Advance progress on jobs, consume/produce resources, update ResourceNode, FarmPlot, MineNode.
	•	CombatSystem
Resolve active combat phases; apply Health changes and emit EntityDefeated.

5.4 Orchestration & Scheduling

Systems execute in fixed order each tick:
	1.	InputHandler
	2.	MovementSystem
	3.	AISystem
	4.	JobAssignmentSystem
	5.	EconomySystem
	6.	CraftingSystem
	7.	FarmingSystem
	8.	MiningSystem
	9.	CombatSystem
	10.	RenderSystem

Lower-frequency tasks (crop growth, market updates) check a timer.

5.5 Queries & Performance
	•	Component lookup optimized via dicts.
	•	For large worlds, consider archetype indexing or spatial partitioning for Movement and Rendering.
	•	Batch processing for rendering and economy updates.

5.6 Events & Decoupling

class EventBus:
    def subscribe(self, event_type, handler): ...
    def emit(self, event): ...

	•	Example: MovementSystem emits EntityMoved; FogOfWarSystem listens to reveal tiles.

5.7 Serialization & Save/Load
	1.	Serialize: write each component type’s (entity_id, data_dict) to file.
	2.	Deserialize: recreate entities in order, re-add components.
	3.	Replay: use command log to replay AI and player actions.

5.8 Extensibility
	•	Add Component: define data class, call registry.add_component().
	•	Add System: subclass BaseSystem, implement update(), register in main loop.
	•	Data-Driven: load recipes, jobs, goals, AI weights from JSON/YAML.

⸻

6. Non-Functional Requirements
	•	Performance:
	•	Chunk gen < 200 ms.
	•	ECS tick < 10 ms for typical island sizes.
	•	Rendering ≥ 60 FPS desktop, ≥ 30 FPS mobile.
	•	Determinism: seed + command log yields identical state.
	•	Extensibility: data-driven content, pluggable systems.
	•	Testability: comprehensive unit tests for mapgen, ECS, AI, resource systems.
	•	Documentation: docstrings for all public APIs; developer guide.

⸻

7. Data Flow
	1.	Startup: load macro map, initial micro chunk.
	2.	Resource Node Placement: Micro-gen tags tiles and spawns farm plots, ore veins.
	3.	Tick Loop:
	•	Systems run in orchestration order, modify components, emit events.
	4.	Render: draw viewport with fog-of-war.
	5.	Save: user triggers SaveManager → compress + store.
	6.	Load: decompress + replay commands.

⸻

8. Implementation Roadmap

Phase	Weeks	Deliverables
1. Foundation	1–4	ECS registry, macro/micro map gen, rendering, input handling
2. Core Systems	5–8	Movement, Radiant AI, economy, job system, settlement markets
3. Resource Layer	9–12	FarmingSystem, MiningSystem, CraftingSystem
4. Crew & Combat	13–16	Crew roles & events, naval & melee combat
5. Quests & Polish	17–20	Quest integration, fog-of-war, UI refinements, save/load
6. Beta & Release	21–24	Testing, performance tuning, documentation, demo scenario


⸻

9. Future Extensions
	•	Advanced Agriculture: terracing, irrigation networks
	•	Deep Mining: caves, rare gemstones
	•	Shipbuilding: custom hulls, sails, figureheads
	•	Multiplayer: persistent shared archipelago
	•	Graphical Tileset: optional Canvas/WebGL front-end

⸻

10. Appendix

10.1 requirements.txt

numpy
scipy
perlin-noise
lz-string

10.2 Testing Guidelines
	•	Map Generation: validate biome, elevation, moisture distributions.
	•	Resource Placement: ensure vein/crop density matches tile attributes.
	•	AI Behavior: confirm NPCs pursue correct jobs/goals.
	•	Economic Response: prices update with supply/demand shifts.
	•	Determinism: seed + log reproducibility.

⸻

This all-inclusive PRD defines every aspect—from world generation and resource systems to a deep ECS architecture—to guide development of a richly emergent ASCII-based pirate roguelike.
