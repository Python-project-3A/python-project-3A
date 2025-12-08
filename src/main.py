import argparse
import sys
import random

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


def run_battle(args):
    """Run a battle scenario"""
    print("=" * 60)
    print("=== LOADING SCENARIO ===")
    print("=" * 60)
    # 1. Load Data
    try:
        scenario_data = ScenarioLoader.load_scenario(args.scenario)
    except FileNotFoundError:
        print(f"Scenario {args.scenario} not found.")
        return

    # 2. Setup Battlefield
    width, height = scenario_data["map"]["width"], scenario_data["map"]["height"]
    bf = Battlefield(width, height)

    # 3. Setup Generals & Units
    bf.generals = [create_general(args.general0, 0), create_general(args.general1, 1)]
    ScenarioLoader.spawn_scenario(scenario_data, bf, {0: args.general0, 1: args.general1})

    # 4. Setup View
    visualizer = CLIVisualizer(width, height) if args.terminal else None

    # 5. Run Simulation
    sim = Simulation(bf.game_map, bf.generals, bf)  # tick_duration is logic only now

    # Mode Chooser: Visual (30 TPS) vs Headless (Max Speed)
    target_tps = 30 if visualizer else 0

    # 6. Affichage des headers statiques
    print(f"\n Scenario: {scenario_data['name']}")
    print(f"\n {scenario_data.get('description', '')}")
    print(f" Map: {width}x{height}")
    print(f" Spawned {len(bf.units_by_owner(0))} units for Player 0")
    print(f" Spawned {len(bf.units_by_owner(1))} units for Player 1")
    print("\n Starting battle...\n")

    with ConsoleInputProvider() as inp:
        sim.run(inp, visualizer=visualizer, target_tps=target_tps)

    # 7. Results
    bf.print_battle_result()


def main():
    args = parse_args()

    if args.command == "list":
        command_list()

    elif args.command == "run":
        # command_run(args)
        run_battle(args)
    elif args.command == "load":
        print("  'load' command not yet implemented")

    elif args.command == "tourney":
        print("  'tourney' command not yet implemented")

    else:
        print(" No command specified. Use --help for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
