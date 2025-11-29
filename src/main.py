# src/main.py
import argparse

from src.cli.cli import CLIVisualizer
from src.engine.battlefield import Battlefield
from src.engine.simulation import Simulation
from src.units.pikeman import Pikeman
from src.engine.simulation import DEFAULT_FPS


# --- gestion des arguments ---------------------------------------------
def parse_args():
    # création d'un objet parser (= interpréteur d'arguments)
    parser = argparse.ArgumentParser(description="AoE-like RTS simulation CLI")  # descrption = text affiché avec : python -m src.main --help

    parser.add_argument("--width", type=int, default=40, help="Largeur de la map")
    parser.add_argument("--height", type=int, default=20, help="Hauteur de la map")
    parser.add_argument("--ticks", type=int, default=100, help="Nombre de ticks")
    parser.add_argument("--speed", type=float, default=1.0, help="Multiplicateur de vitesse : 0.5, 1, 2, 3...")
    parser.add_argument("--no-visual", action="store_true", help="Désactive l'affichage CLI")

    return parser.parse_args()


# --- Implementations minimal de General pour les tests ---------------------------------------------


class General_minimal:
    """
    Général ultra simple :
    - ne fait rien pour l'instant, a le mérite d'exister
    """

    def update(self, battlefield, tick):
        pass


# --- MAIN ----------------------------------------------------------
def main():
    args = parse_args()
    base_tick_duration = 1 / DEFAULT_FPS
    real_tick_duration = base_tick_duration / args.speed

    print("=== DEMARRAGE SIMULATION ===")

    bf = Battlefield(args.width, args.height)

    # spawn deux unités
    u1_id = bf.spawn_unit(lambda: Pikeman(team=0, x=0, y=0), 33.0, 0.0, owner=0)
    u2_id = bf.spawn_unit(lambda: Pikeman(team=0, x=0, y=1), 35.0, 0.0, owner=1)

    # ajout d’un général
    bf.generals.append(General_minimal())

    # Visualizer
    visualizer = None
    if not args.no_visual:  # Si l'utilisateur veut un visualizer, (= si il n'a pas demandé de ne pas lancer le visualiser)
        visualizer = CLIVisualizer(args.width, args.height)

    # création de laSimulation
    sim = Simulation(game_map=bf.game_map, generals=bf.generals, battlefield=bf, tick_duration=real_tick_duration)

    # lancement de la simulation
    sim.run(max_ticks=args.ticks, visualizer=visualizer)

    print("\n=== SNAPSHOT FINALE ===\n")
    print(bf.snapshot())  # affiche le snapshot finale


# pour que la fonction main() ne soit exécutée que si le script est lancé directement, mais pas s'il est importé (protection).
if __name__ == "__main__":
    main()

# commande de test : python -m src.main --ticks 100
# commande de test : python -m src.main --ticks 100 --no-visual
