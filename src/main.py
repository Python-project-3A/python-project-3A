import argparse
import sys

from src.cli.cli import CLIVisualizer
from src.engine.battlefield import Battlefield
from src.engine.simulation import Simulation
from src.general.braindead import GeneralBraindead
from src.general.daft import GeneralDaft
from src.scenarios.scenario_loader import ScenarioLoader
from src.engine.input_provider import ConsoleInputProvider


def parse_args():
    parser = argparse.ArgumentParser(
        description="AoE-like RTS simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main run small_battle daft braindead
  python -m src.main run knights_vs_pikemen smart daft -t
  python -m src.main list
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # --- COMMAND: list ---
    subparsers.add_parser("list", help="List available scenarios")

    # --- COMMAND: run ---
    run_parser = subparsers.add_parser("run", help="Run a battle scenario")
    run_parser.add_argument("scenario", type=str, help="Scenario name (without .json)")
    run_parser.add_argument("general0", type=str, choices=["braindead", "daft"], help="General for player 0")
    run_parser.add_argument("general1", type=str, choices=["braindead", "daft"], help="General for player 1")
    run_parser.add_argument("-t", "--terminal", action="store_true", help="Use terminal view instead of 2.5D (currently only terminal available)")
    run_parser.add_argument("--speed", type=float, default=0.1, help="Tick duration in seconds")

    # --- COMMAND: load (TODO) ---
    load_parser = subparsers.add_parser("load", help="Load a saved game (TODO)")
    load_parser.add_argument("savefile", type=str, help="Save file path")

    # --- COMMAND: tourney (TODO) ---
    tourney_parser = subparsers.add_parser("tourney", help="Run tournament (TODO)")
    tourney_parser.add_argument("-G", "--generals", nargs="+", choices=["braindead", "daft"], help="Generals to include in tournament")
    tourney_parser.add_argument("-S", "--scenarios", nargs="+", help="Scenarios to use")
    tourney_parser.add_argument("-N", type=int, default=10, help="Number of rounds per matchup")
    tourney_parser.add_argument("--no-alternate", action="store_true", help="Don't alternate player positions")

    return parser.parse_args()


def create_general(general_type: str, player_id: int):
    """Factory to create generals"""
    if general_type == "braindead":
        return GeneralBraindead(player_id)
    elif general_type == "daft":
        return GeneralDaft(player_id)
    else:
        raise ValueError(f"Unknown general type: {general_type}")


def command_list():
    """List all available scenarios"""
    scenarios = ScenarioLoader.list_available_scenarios()

    print("\n" + "=" * 60)
    print("AVAILABLE SCENARIOS")
    print("=" * 60)

    if not scenarios:
        print("No scenarios found in data/scenarios/")
        return

    for scenario_name in scenarios:
        try:
            data = ScenarioLoader.load_scenario(scenario_name)
            print(f"\n {scenario_name}")
            print(f"   {data.get('description', 'No description')}")
            print(f"   Map: {data['map']['width']}x{data['map']['height']}")

            for army in data["armies"]:
                total_units = sum(g["count"] for g in army["units"])
                unit_types = ", ".join(f"{g['count']} {g['type']}" for g in army["units"])
                print(f"   Player {army['player_id']}: {unit_types} (Total: {total_units})")
        except Exception as e:
            print(f"\n  {scenario_name}: Error loading - {e}")

    print("\n" + "=" * 60 + "\n")


def command_run(args):
    """Run a battle scenario"""
    print("=" * 60)
    print("=== LOADING SCENARIO ===")
    print("=" * 60)

    # Load scenario
    try:
        scenario_data = ScenarioLoader.load_scenario(args.scenario)
    except FileNotFoundError as e:
        print(f"\n Error: {e}\n")
        return

    print(f"\n Scenario: {scenario_data['name']}")
    print(f" {scenario_data.get('description', '')}")
    print(f" Map: {scenario_data['map']['width']}x{scenario_data['map']['height']}")

    # Create battlefield
    bf = Battlefield(width=scenario_data["map"]["width"], height=scenario_data["map"]["height"])

    # Create generals
    general_0 = create_general(args.general0, player_id=0)
    general_1 = create_general(args.general1, player_id=1)
    bf.generals = [general_0, general_1]

    print(f"\n  Battle: {general_0.name} VS {general_1.name}\n")

    # Spawn scenario with general overrides
    general_overrides = {0: args.general0, 1: args.general1}
    ScenarioLoader.spawn_scenario(scenario_data, bf, general_overrides)

    # Count spawned units
    units_0 = len(bf.units_by_owner(0))
    units_1 = len(bf.units_by_owner(1))
    print(f" Spawned {units_0} units for Player 0")
    print(f" Spawned {units_1} units for Player 1")

    # Create visualizer
    visualizer = None
    if args.terminal:
        visualizer = CLIVisualizer(bf.width, bf.height)

    # Create and run simulation
    sim = Simulation(game_map=bf.game_map, generals=bf.generals, battlefield=bf)

    print("\n🎬 Starting battle...\n")
    # Le 'with' garantit que le terminal Linux sera réparé même en cas de crash
    with ConsoleInputProvider() as input_sys:
        # On injecte le système d'input dans la simulation
        if visualizer:
            sim.run(input_provider=input_sys, visualizer=visualizer, target_tps=30)
        else:
            sim.run(input_provider=input_sys, visualizer=visualizer, target_tps=0)  # target_tps=0 => vitesse maximale

    # Print results
    print_battle_result(bf)


def print_battle_result(battlefield):
    """Print battle results"""
    print("\n" + "=" * 60)
    print("=== BATTLE RESULT ===")
    print("=" * 60)

    survivors_by_owner = {}
    for unit in battlefield.get_all_units():
        if unit.is_alive():
            if unit.owner not in survivors_by_owner:
                survivors_by_owner[unit.owner] = []
            survivors_by_owner[unit.owner].append(unit)

    for owner_id in [0, 1]:
        general = battlefield.generals[owner_id]
        survivors = survivors_by_owner.get(owner_id, [])

        print(f"\n️  {general.name} (Player {owner_id}):")
        print(f"   Survivors: {len(survivors)} units")

        if survivors:
            total_hp = sum(u.hp for u in survivors)
            avg_hp = total_hp / len(survivors)
            print(f"   Total HP: {total_hp:.1f}")
            print(f"   Avg HP: {avg_hp:.1f}")

    print("\n" + "-" * 60)
    if len(survivors_by_owner) == 0:
        print("  DRAW - All units eliminated!")
    elif len(survivors_by_owner) == 1:
        winner_id = list(survivors_by_owner.keys())[0]
        winner_general = battlefield.generals[winner_id]
        print(f" VICTORY for {winner_general.name} (Player {winner_id})!")
    else:
        counts = {owner: len(units) for owner, units in survivors_by_owner.items()}
        winner_id = max(counts, key=counts.get)
        winner_general = battlefield.generals[winner_id]
        print(f" TACTICAL VICTORY for {winner_general.name} (Player {winner_id})!")

    print("=" * 60 + "\n")


def main():
    args = parse_args()

    if args.command == "list":
        command_list()

    elif args.command == "run":
        command_run(args)

    elif args.command == "load":
        print("  'load' command not yet implemented")

    elif args.command == "tourney":
        print("  'tourney' command not yet implemented")

    else:
        print(" No command specified. Use --help for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
