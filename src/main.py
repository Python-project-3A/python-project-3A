import argparse
import sys
import time
import itertools
import matplotlib.pyplot as plt

from src.cli.cli import CLIVisualizer
from src.engine.battlefield import Battlefield
from src.engine.simulation import Simulation
from src.general.braindead import GeneralBraindead
from src.general.daft import GeneralDaft
from src.general.GeneralTactician import GeneralTactician
from src.general.GeneralSmart import GeneralSmart
from src.scenarios.scenario_loader import ScenarioLoader
from src.pygame.pygame_visualizer import PygameVisualizer
from src.pygame.pygame_input_provider import PygameInputProvider
from src.engine.input_provider import ConsoleInputProvider
from src.engine.save_load import save_game, load_game, get_save_dir
from src.engine.html_snapshot import HTMLSnapshot
from src.data.scenarios.lanchester import create_lanchester_scenario


def parse_args():
    parser = argparse.ArgumentParser(
        description="AoE-like RTS simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main run small_battle daft braindead
  python -m src.main run knights_vs_pikemen smart daft -t
  python -m src.main list
  python -m src.main plot Pikeman 10 50 5
  python -m src.main plot_time Pikeman 50
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # --- COMMAND: list ---
    subparsers.add_parser("list", help="List available scenarios")

    # --- COMMAND: run ---
    run_parser = subparsers.add_parser("run", help="Run a battle scenario")
    run_parser.add_argument("scenario", type=str, help="Scenario name (without .json)")
    run_parser.add_argument("general0", type=str, choices=["braindead", "daft", "generalsmart", "generaltactician"], help="General for player 0")
    run_parser.add_argument("general1", type=str, choices=["braindead", "daft", "generalsmart", "generaltactician"], help="General for player 1")

    viz_group = run_parser.add_mutually_exclusive_group()
    viz_group.add_argument("-gui", action="store_true", help="Use Pygame GUI visualizer.")
    viz_group.add_argument("-t", "--terminal", action="store_true", help="Use terminal visualizer (default if no visualizer is specified).")

    run_parser.add_argument("--speed", type=float, default=0.1, help="Tick duration in seconds")

    # --- COMMAND: load ---
    load_parser = subparsers.add_parser("load", help="Load a saved game")
    load_parser.add_argument("savefile", type=str, help="Save file path")

    load_viz_group = load_parser.add_mutually_exclusive_group()
    load_viz_group.add_argument("-gui", action="store_true", help="Use Pygame GUI visualizer.")
    load_viz_group.add_argument("-t", "--terminal", action="store_true", help="Use terminal visualizer (default if no visualizer is specified).")

    # --- COMMAND: tourney ---
    tourney_parser = subparsers.add_parser("tourney", help="Run tournament")
    tourney_parser.add_argument("-G", "--generals", nargs="+", choices=["braindead", "daft", "generalsmart", "generaltactician"], help="Generals to include in tournament")
    tourney_parser.add_argument("-S", "--scenarios", nargs="+", help="Scenarios to use")
    tourney_parser.add_argument("-N", type=int, default=10, help="Number of rounds per matchup")
    tourney_parser.add_argument("-na", action="store_true", help="Don't alternate player positions")

    # --- COMMAND: Lanchester ---
    plot_parser = subparsers.add_parser("plot", help="Plot Lanchester curves")
    plot_parser.add_argument("unit_type", type=str, help="Unit type (e.g., Knight)")
    plot_parser.add_argument("min_n", type=int, help="Start N")
    plot_parser.add_argument("max_n", type=int, help="End N")
    plot_parser.add_argument("step", type=int, help="Step size")

    # COMMAND: plot_time (Validation Temporelle)
    plot_time_parser = subparsers.add_parser("plot_time", help="Plot survivors over time (Single Battle)")
    plot_time_parser.add_argument("unit_type", type=str, help="Unit type")
    plot_time_parser.add_argument("n", type=int, default=50, help="Base army size N (Default 50)")

    return parser.parse_args()


def create_general(general_type: str, player_id: int):
    """Factory to create generals"""
    if general_type == "braindead":
        return GeneralBraindead(player_id)
    elif general_type == "daft":
        return GeneralDaft(player_id)
    elif general_type == "GeneralSmart" or general_type == "generalsmart":
        return GeneralSmart(player_id)
    elif general_type == "generaltactician" or general_type == "GeneralTactician":
        return GeneralTactician(player_id)
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

    scenarios_to_run = args.scenarios if args.scenarios else ["pikemen_vs_pikemen"]  # , "pikemen_vs_knights", "knights_vs_pikemen", "knights_vs_knights"
    available_generals = ["braindead", "daft", "generalsmart"]
    generals_to_run = sorted(list(set(args.generals if args.generals else available_generals)))
    rounds = args.N
    tournament_data = {}  # Structure de stockage des résultats / results[scenario][p0_name][p1_name] = {wins0, wins1, draws}

    print("=" * 60)
    print(f"\n STARTING TOURNAMENT: {rounds} Rounds")
    print(f"\n Scenario: {scenarios_to_run}")
    print(" \n Mode: Positions FIXES (Not Alternating)" if args.na else " Mode: Positions ALTERNATIVES (Alternating)")
    print(f"\n Rounds per match: {rounds} (Alternate: {not args.na})")
    print(f"\n Ctrl+C pour interrompre le tournoi et voir les résultats partiels.")
    print("=" * 60)

    try:
        # --- BOUCLE 1 : SCÉNARIOS ---
        start_time = time.time()
        for scen_name in scenarios_to_run:
            print(f"\n SCENARIO: {scen_name}")
            try:
                scen_data = ScenarioLoader.load_scenario(scen_name)
            except FileNotFoundError:
                print(f"\n Skipping {scen_name} (File not found)")
                continue

            tournament_data[scen_name] = {}

            # --- BOUCLE 2 & 3 : MATCHUPS (Gen A vs Gen B) ---
            # combinations_with_replacement permet d'avoir (A,B), (A,C) et (A,A) mais pas (B,A) car c'est redondant si on alterne les positions.
            matchups = list(itertools.combinations_with_replacement(generals_to_run, 2))

            for gen_1, gen_2 in matchups:
                match_id = f"{gen_1.upper()} vs {gen_2.upper()}"
                sys.stdout.write(f"  Match {match_id} : \n")
                sys.stdout.flush()

                if gen_1 not in tournament_data[scen_name]:
                    tournament_data[scen_name][gen_1] = {}
                tournament_data[scen_name][gen_1][gen_2] = {0: 0, 1: 0, "draw": 0}
                wins = tournament_data[scen_name][gen_1][gen_2]

                # --- EXECUTION DES N ROUNDS ---
                for i in range(rounds):
                    bf = Battlefield(scen_data["map"]["width"], scen_data["map"]["height"])

                    if i % 10 == 0:  # Feedback minimal
                        sys.stdout.write(".")
                        sys.stdout.flush()

                    # Alternance
                    swapped = False
                    if not args.na and i % 2 != 0:
                        swapped = True

                    p0_type = gen_2 if swapped else gen_1
                    p1_type = gen_1 if swapped else gen_2

                    bf.generals = [create_general(p0_type, 0), create_general(p1_type, 1)]
                    overrides = {0: p0_type, 1: p1_type}
                    ScenarioLoader.spawn_scenario(scen_data, bf, overrides)

                    sim = Simulation(bf.game_map, bf.generals, bf)
                    sim.run(None, visualizer=None, target_tps=0, max_ticks=10000)  # Headless

                    survivors = set(u.owner for u in bf.get_all_units() if u.is_alive())

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
                        if not swapped:
                            wins[winner] += 1
                        else:
                            if winner == 0:
                                wins[1] += 1
                            else:
                                wins[0] += 1

                # Fin du matchup
                print(f" Done. Score: {wins[0]}-{wins[1]} (D:{wins['draw']})\n")

    except KeyboardInterrupt:
        print(f"\n\n{'-' * 60}")
        print(" INTERRUPTION UTILISATEUR (Ctrl+C)")
        print(" Finalisation des résultats partiels...")

    total_time = time.time() - start_time
    print(f"\n\n Total time: {total_time:.2f} seconds.")
    print(f"{'=' * 60}")

    # 4. GENERATION DU RAPPORT
    HTMLSnapshot.save_tournament_report(tournament_data)


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

    width, height = simulation.battlefield.width, simulation.battlefield.height

    visualizer = None
    if args.gui:
        visualizer = PygameVisualizer(battlefield=simulation.battlefield)
    elif args.terminal:
        visualizer = CLIVisualizer(width, height)

    target_tps = 30 if visualizer else 0

    print("\n Loading battle...\n")

    if args.gui:
        with PygameInputProvider() as inp:
            simulation.run(input_provider=inp, visualizer=visualizer, target_tps=target_tps)
    elif args.terminal:
        with ConsoleInputProvider() as inp:
            simulation.run(input_provider=inp, visualizer=visualizer, target_tps=target_tps)

    # Print results
    full_output = simulation.battlefield.print_battle_result()
    sys.stdout.write(full_output)
    sys.stdout.flush()

def run_lanchester_plot(args):
    unit_type = args.unit_type
    n_values = range(args.min_n, args.max_n + 1, args.step)
    
    results_n = []
    results_percent_alive= [] 

    print(f"Starting Lanchester Plot for {unit_type}...")

    for n in n_values:
        # --- LOGIQUE DE TAILLE D'ARMEE ---
        count_p0 = n
        
        if unit_type == "Crossbowman" or unit_type == "EliteSkirmisher":
            # Attention : N^2 grandit très vite !
            count_p1 = n * n
        else:
            # Loi Linéaire (Corps à corps)
            count_p1 = n * 2

        print(f"Simulating N={count_p0} vs {count_p1}...", end="", flush=True)
        # 3. Génération Dynamique du Scénario
        scenario_data = create_lanchester_scenario(unit_type, count_p0, count_p1)        
        # 4. Mise en place du champ du battlefield
        width = scenario_data["map"]["width"]
        height = scenario_data["map"]["height"]
        bf = Battlefield(width, height)

        p1_ai = "daft" 
        p2_ai = "daft"
        
        bf.generals = [create_general(p1_ai, 0), create_general(p2_ai, 1)]
        
        # On passe les overrides au loader au cas où il en a besoin pour l'initialisation
        overrides = {0: p1_ai, 1: p2_ai}
        
        ScenarioLoader.spawn_scenario(scenario_data, bf, overrides)
        
        sim = Simulation(bf.game_map, bf.generals, bf)
        
        with ConsoleInputProvider() as inp:
            sim.run(inp, visualizer=None, target_tps=0, max_ticks=10000)
            
        # 6. Collecte des Données (Après la bataille)
        survivors_p2 = len(bf.units_by_owner(0))
        survivors_p1 = len(bf.units_by_owner(1))
        initial_p1 = count_p1
        casualties = initial_p1 - survivors_p1
        
        results_n.append(n)
        results_percent_alive.append((survivors_p1 / initial_p1) * 100)
        
        print(f"nombre de survivants P1: {survivors_p1}")
        print(f"nombre de survivant P2: {survivors_p2}")
        print(f" Done. Casualties: {casualties}")

    # 7. Tracé du Graphique (Matplotlib)
    plt.figure(figsize=(10, 6))
    
    label_text = f'{unit_type} (vs N^2)' if unit_type == "Crossbowman" or unit_type == "EliteSkirmisher" else f'{unit_type} (vs 2N)'
    
    plt.plot(results_n, results_percent_alive, marker='o', linestyle='-', color='b', label=label_text)
    
    plt.title(f"Lois de Lanchester : {label_text}")
    plt.xlabel("N (Taille de l'armée perdante)")
    plt.ylabel("Pourcentage de Survivants (Vainqueur)")
    plt.grid(True)
    plt.legend()
    
    # Affichage de la fenêtre graphique
    plt.show()

def run_temporal_plot(args):
    unit_type = args.unit_type
    n = args.n
    
    # Configuration N vs 2N (Standard Lanchester)
    count_p0 = n
    count_p1 = n * 2
    
    print(f"Starting Temporal Plot for {unit_type} ({count_p0} vs {count_p1})...")
    
    # 1. Création du Scénario
    scenario_data = create_lanchester_scenario(unit_type, count_p0, count_p1)
    
    width = scenario_data["map"]["width"]
    height = scenario_data["map"]["height"]
    bf = Battlefield(width, height)
    bf.generals = [create_general("daft", 0), create_general("daft", 1)]
    ScenarioLoader.spawn_scenario(scenario_data, bf)
    
    sim = Simulation(bf.game_map, bf.generals, bf)
    
    # 2. Préparation des listes de données
    history_time = []
    history_p0 = []
    history_p1 = []
    
    # 3. Boucle de Simulation Manuelle
    max_ticks = 5000
    sim.is_running = True
    dt = 1.0 / 30.0  # Temps logique par tick
    
    print("Simulating...", end="", flush=True)
    
    while sim.is_running and sim.tick_count < max_ticks:
        # Exécuter un tick
        sim.tick(dt)
        
        # Enregistrer les données (Tous les 10 ticks pour alléger le graphique si besoin, ou 1 pour précision max)
        if sim.tick_count % 5 == 0:
            history_time.append(sim.tick_count)
            history_p0.append(len(bf.units_by_owner(0)))
            history_p1.append(len(bf.units_by_owner(1)))
            
        # Arrêt si une équipe est morte
        if bf.is_battle_over():
            break
            
    print(" Done.")

    # 4. Tracé du Graphique
    plt.figure(figsize=(10, 6))
    
    plt.plot(history_time, history_p0, color='red', label=f'Player 0 (N={count_p0})', linewidth=2)
    plt.plot(history_time, history_p1, color='blue', label=f'Player 1 (2N={count_p1})', linewidth=2)
    
    plt.title(f"Évolution des effectifs au cours du temps : {unit_type}")
    plt.xlabel("Temps (Ticks)")
    plt.ylabel("Nombre de Survivants")
    plt.legend()
    plt.grid(True)
    
    # Limites pour bien voir le début et la fin
    plt.ylim(0, count_p1 + 5)
    plt.xlim(0, len(history_time) * 5) # Ajusté selon le modulo d'enregistrement
    
    plt.show()
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

    # 4. Setup View & Input Provider
    visualizer = None

    if args.gui:
        visualizer = PygameVisualizer(battlefield=bf)
    elif args.terminal:
        visualizer = CLIVisualizer(width, height)

    # 5. Run Simulation
    sim = Simulation(bf.game_map, bf.generals, bf)
    target_tps = 30 if visualizer else 0

    # 6. Affichage des headers statiques

    print(f"\n Scenario: {scenario_data['name']}")
    print(f"\n {scenario_data.get('description', '')}")
    print(f" Map: {width}x{height}")
    print(f" Spawned {len(bf.units_by_owner(0))} units for Player 0")
    print(f" Spawned {len(bf.units_by_owner(1))} units for Player 1")
    print("\n Starting battle...\n")

    if args.gui:
        with PygameInputProvider() as inp:
            sim.run(input_provider=inp, visualizer=visualizer, target_tps=target_tps)
    elif args.terminal:
        with ConsoleInputProvider() as inp:
            sim.run(input_provider=inp, visualizer=visualizer, target_tps=target_tps)
    else:
        sim.run(input_provider=None, visualizer=None, target_tps=0)

    # Print results
    full_output = bf.print_battle_result()
    sys.stdout.write(full_output)
    sys.stdout.flush()


def main():
    args = parse_args()

    if args.command == "list":
        command_list()

    elif args.command == "run":
        run_battle(args)

    elif args.command == "plot":
        run_lanchester_plot(args)

    elif args.command == "load":
        command_load(args)

    elif args.command == "tourney":
        run_tournament(args)

    elif args.command == "plot_time":
        run_temporal_plot(args)

    else:
        print(" No command specified. Use --help for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
