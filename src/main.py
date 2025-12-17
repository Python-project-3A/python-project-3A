import argparse
import sys
import time

from src.cli.cli import CLIVisualizer
from src.engine.battlefield import Battlefield
from src.engine.simulation import Simulation
from src.general.braindead import GeneralBraindead
from src.general.daft import GeneralDaft
from src.general.GeneralSmart import GeneralSmart
from src.scenarios.scenario_loader import ScenarioLoader
from src.engine.input_provider import ConsoleInputProvider
from src.engine.save_load import save_game, load_game, get_save_dir


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
    run_parser.add_argument("general0", type=str, choices=["braindead", "daft", "generalsmart"], help="General for player 0")
    run_parser.add_argument("general1", type=str, choices=["braindead", "daft", "generalsmart"], help="General for player 1")
    run_parser.add_argument("-t", "--terminal", action="store_true", help="Use terminal view instead of 2.5D (currently only terminal available)")
    run_parser.add_argument("--speed", type=float, default=0.1, help="Tick duration in seconds")

    # --- COMMAND: load ---
    load_parser = subparsers.add_parser("load", help="Load a saved game")
    load_parser.add_argument("savefile", type=str, help="Save file path")

    # --- COMMAND: tourney ---
    tourney_parser = subparsers.add_parser("tourney", help="Run tournament")
    tourney_parser.add_argument("-G", "--generals", nargs="+", choices=["braindead", "daft", "generalsmart"], help="Generals to include in tournament")
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
    elif general_type == "GeneralSmart" or general_type == "generalsmart":
        return GeneralSmart(player_id)
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


def run_tournament(args):
    """
    Exécute N simulations ultra-rapides et sort des stats.
    Gère l'interruption par Ctrl+C pour afficher les résultats partiels.
    """
    # print("=" * 60)
    # print("=== LOADING SCENARIO ===")
    # print("=" * 60)

    scenario_name = args.scenarios[0]
    gen_type_1 = args.generals[0]
    gen_type_2 = args.generals[1]  # si il y a un seul général on le met aussi en général 2
    rounds = args.N
    wins = {0: 0, 1: 0, "draw": 0}

    # 1. Load Data
    try:
        scenario_data = ScenarioLoader.load_scenario(scenario_name)
    except FileNotFoundError:
        print("Scenario not found.")
        return

    print("=" * 60)
    print(f"\n STARTING TOURNAMENT: {rounds} Rounds")
    print(f" {gen_type_1.upper()} (General 0) vs {gen_type_2.upper()} (General 1)")
    print(f"\n Scenario: {scenario_data['name']}")
    print(f" {scenario_data.get('description', '')}")
    print(f"\n Map: {scenario_data['map']['width']}x{scenario_data['map']['height']}")
    print(f"\n Ctrl+C pour interrompre le tournoi et voir les résultats partiels.")
    print("=" * 60)

    try:
        scenario_data = ScenarioLoader.load_scenario(scenario_name)
    except FileNotFoundError:
        print("Scenario not found.")
        return

    start_time = time.time()
    played_rounds = 0

    # --- BLOC TRY / EXCEPT POUR CAPTURER L'INTERRUPTION ---
    try:
        for i in range(rounds):
            # Barre de progression
            if i % 10 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()

            # Setup Battlefield
            bf = Battlefield(scenario_data["map"]["width"], scenario_data["map"]["height"])

            current_g0_type = gen_type_1
            current_g1_type = gen_type_2
            bf.generals = [create_general(current_g0_type, 0), create_general(current_g1_type, 1)]

            # Spawn
            overrides = {0: current_g0_type, 1: current_g1_type}
            ScenarioLoader.spawn_scenario(scenario_data, bf, overrides)

            # Simulation Headless
            sim = Simulation(bf.game_map, bf.generals, bf)
            sim.run(None, visualizer=None, target_tps=0)

            # Résultat
            survivors = {}
            for u in bf.get_all_units():
                if u.is_alive():
                    survivors[u.owner] = True

            winner = -1
            if 0 in survivors and 1 not in survivors:
                winner = 0
            elif 1 in survivors and 0 not in survivors:
                winner = 1
            else:
                winner = "draw"

            if winner == "draw":
                wins["draw"] += 1
            else:
                wins[winner] += 1

            played_rounds += 1

    except KeyboardInterrupt:
        print("\n\n INTERRUPTION UTILISATEUR (Ctrl+C)")
        print(" Finalisation des résultats partiels...")

    # --- AFFICHAGE DES RÉSULTATS ---
    total_time = time.time() - start_time

    if played_rounds == 0:  # Sécurité pour éviter la division par zéro si on arrête instantanément
        print("\n Aucun match n'a été terminé.")
        return

    print(f"\n{'=' * 60}")
    print(f"RESULTS ({played_rounds} rounds played in {total_time:.2f}s)")
    print(f"{'=' * 60}")
    win_rate_0 = wins[0] / played_rounds * 100
    win_rate_1 = wins[1] / played_rounds * 100
    print(f"General 1 ({gen_type_1}): {wins[0]} wins ({win_rate_0:.1f}%)")
    print(f"General 2 ({gen_type_2}): {wins[1]} wins ({win_rate_1:.1f}%)")
    print(f"Draws: {wins['draw']} ({((wins['draw'] / played_rounds) * 100):.1f}%)")
    print(f"{'=' * 60}")

    # Analyse de Biais
    if gen_type_1 == gen_type_2:
        diff = abs(win_rate_0 - win_rate_1)
        print(f"Vérification d'équité : L'écart est de {diff:.0f}%.")
        if diff > 10.0:  # 10% d'écart
            print(f" WARNING: Significant biais detecte (>10%) ! Le jeu favorise un camp.")
        else:
            print(f" Le jeu semble équilibré.")


def command_load(args):
    """Charge une sauvegarde et lance la simulation."""
    try:
        # La fonction load_game retourne un nouvel objet Simulation
        simulation = load_game(args.savefile)
    except FileNotFoundError:
        print(f"Error: Save file '{args.savefile}.json' not found in {get_save_dir()}.")
        return
    except Exception as e:
        print(f"Error loading game: {e}")
        return

    # Setup View (même logique que run_battle)
    width, height = simulation.battlefield.width, simulation.battlefield.height
    visualizer = CLIVisualizer(width, height)  # Le chargement impose la vue Terminale (pour l'instant)
    target_tps = 30  # Taux de rafraîchissement visuel standard

    print("\n Loading battle...\n")

    with ConsoleInputProvider() as inp:
        simulation.run(inp, visualizer=visualizer, target_tps=target_tps)

    # 7. Results
    simulation.battlefield.print_battle_result()


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
    full_output = bf.print_battle_result()
    sys.stdout.write(full_output)
    sys.stdout.flush()


def main():
    args = parse_args()

    if args.command == "list":
        command_list()

    elif args.command == "run":
        run_battle(args)

    elif args.command == "load":
        command_load(args)

    elif args.command == "tourney":
        run_tournament(args)

    else:
        print(" No command specified. Use --help for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
