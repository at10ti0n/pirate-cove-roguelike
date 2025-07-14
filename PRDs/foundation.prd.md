Foundation Phase PRD (Weeks 1–4)

⸻

1. Objectives

Establish the core infrastructure and minimal playable loop for the pirate-themed ASCII roguelike by delivering:
	1.	ECS Backbone: a working Entity–Component–System registry with basic component types and query API.
	2.	World Generation: macro overworld grid + micro-chunk generator producing deterministic terrain tiles.
	3.	ASCII Rendering: terminal renderer capable of drawing layered CP437 glyphs with ANSI colors and fog-of-war.
	4.	Input Handling: keyboard (WASD/arrows) abstraction and basic movement controls between micro chunks and macro map.
	5.	Save/Load Skeleton: stubbed command-log framework for future deterministic replay.

⸻

2. Scope
	•	In Scope
	•	Implement and test ecs/registry.py and core data components.
	•	Build macro_map.py and map_generator.py logic to create a small static world (e.g., 32×16 macro, 32×32 micro).
	•	Create terminal_renderer.py to draw a micro-chunk viewport (40×20) with colored glyphs.
	•	Develop input_handler.py to capture movement keys and switch between micro and macro modes.
	•	Wire everything in main.py to allow:
	•	Macro view: move cursor over macro grid.
	•	Micro view: load/generate a micro chunk at cursor, move player “@” around, and cross chunk borders.
	•	Build save_manager.py stub (API only; actual persistence later).
	•	Out of Scope
	•	AI behaviors, economy, jobs, resource systems.
	•	Combat, crafting, farming, mining.
	•	Polished UI or performance tuning beyond basic responsiveness.

⸻

3. Deliverables

Module	Description	Acceptance Criteria
ecs/registry.py	Registry class with create_entity(), add_component(), query(), destroy_entity().	Unit tests: can create entities, attach/remove components, and query by component types.
ecs/components.py	Core data components: Position, Renderable, Velocity, TileInfo.	Components defined as @dataclass; importable without errors.
macro_map.py	Generates a small macro grid: elevation & moisture via PerlinNoise, biome assignment.	Console dump: prints macro map of glyphs (~, . , ^, etc.) matching biome types.
map_generator.py	Creates a deterministic 32×32 micro chunk blending macro context; returns Tile grid & exits.	generate_map() returns 2D Tile array; test ensures same seed ⇒ same tile glyphs/biomes.
tile.py	Defines Tile = namedtuple("Tile", ["glyph","biome","height","moisture"]).	Tile objects hold correct data; basic instantiation test.
terminal_renderer.py	Renders a 40×20 window of a Tile[][] plus a player @, with ANSI colors and a HUD.	Manual: run micro loop, see colored ASCII map, player glyph at center, HUD shows coords.
input_handler.py	Captures WASD/arrow keys and m/q; emits high-level commands (move_north, toggle_mode).	Pressing keys moves the player or switches modes; no raw escape characters leak to screen.
main.py	Integrates registry, map gen, renderer, input; supports micro/macro modes and chunk transitions.	Can move on macro grid and load adjacent micro chunks; moving off-edge loads new chunk.
save_manager.py	Defines record_command(cmd) and replay_commands(cmd_list) stubs for later persistence.	API in place; calling does not crash and logs commands in memory.


⸻

4. Timeline & Milestones

Week	Tasks
Week 1	

	•	Set up project repository, virtual env, dependencies (numpy, perlin-noise).
	•	Implement ecs/registry.py and basic ecs/components.py. Write unit tests for registry.
|
| Week 2 |
	•	Build macro_map.py: Perlin-based elevation & moisture, biome thresholds.
	•	Write a CLI demo to print macro map to console.
|
| Week 3 |
	•	Develop map_generator.py: micro-chunk FBM elevation + biome assignment + deterministic glyph selection.
	•	Unit tests to confirm seed determinism and correct Tile outputs.
|
| Week 4 |
	•	Create terminal_renderer.py and input_handler.py.
	•	Integrate in main.py: toggle macro/micro, player movement, chunk loading.
	•	Stub save_manager.py to record commands.
	•	Manual QA: walk around map, cross chunk boundaries, confirm HUD.

⸻

5. Testing & QA
	•	Unit Tests (/tests):
	•	ECS: entity creation, component add/remove, queries.
	•	MapGen: same seed ⇒ identical Tile grids; correct biome distribution sanity.
	•	Tile: instantiation & attribute ranges.
	•	Integration Tests:
	•	Launch main.py, simulate input script (e.g. ["d","d","s","a","m","w"]), verify no errors.
	•	Manual QA:
	•	Verify ANSI colors in various terminals (Linux, macOS).
	•	Ensure input response is lag-free (<50 ms).

⸻

6. Risks & Mitigations

Risk	Mitigation
PerlinNoise inconsistency (different versions)	Pin perlin-noise version; if needed, vendor minimal noise implementation.
Terminal compatibility	Test on multiple shells; fall back to plain ASCII if ANSI unsupported.
ECS performance	Keep registry simple; optimize only if query times degrade in tests.


⸻

7. Success Criteria

By end of Week 4, a developer can:
	1.	Run python main.py --seed 42 to enter the game.
	2.	Move around a colored ASCII map in micro mode; HUD updates correctly.
	3.	Switch to macro mode, move the cursor, then reload a new micro chunk.
	4.	Observe consistent world regeneration: same seed always yields the same terrain.
	5.	Review unit-test coverage ≥ 80 % on foundation modules.

⸻

This PRD for the Foundation phase lays out clear deliverables, timelines, and acceptance criteria to establish the core gameplay loop and infrastructure. Let me know if you’d like any adjustments or deeper breakdowns!
