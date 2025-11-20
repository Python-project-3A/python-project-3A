# src/main.py
from src.engine.battlefield import Battlefield
from src.engine.simulation import Simulation
import argparse
from src.cli.cli import CLIVisualizer

# --- MOCKS POUR TEST ---------------------------------------------


def parse_args():
    # création d'un objet parser (= interpréteur d'arguments)
    parser = argparse.ArgumentParser(description="AoE-like RTS simulation CLI")  # descrption = text affiché avec : python -m src.main --help

    parser.add_argument("--width", type=int, default=20, help="Largeur de la map")
    parser.add_argument("--height", type=int, default=20, help="Hauteur de la map")
    parser.add_argument("--ticks", type=int, default=200, help="Nombre de ticks")
    parser.add_argument("--speed", type=float, default=0.1, help="Durée entre ticks")  # ne sert pas pour l'isntant, servira pour influer après sur la vitesse de déplacement des untiées, ex : Knight.speed = args.speed
    parser.add_argument("--no-visual", action="store_true", help="Désactive l'affichage CLI")

    return parser.parse_args()


class MockUnit:
    """
    Unité simple pour tests :
    - se déplace légèrement à chaque tick
    """

    def __init__(self, utype="Mock", size=0.4):
        self.id = None
        self.type = utype
        self.owner = 0
        self.position = (0.0, 0.0)
        self.hp = 10
        self.size = size

    def is_alive(self):
        return self.hp > 0

    def update(self, bf, tick):
        """
        Déplacement simple pour test :
        avance de 0.1 sur x à chaque tick
        mais vérifie collisions + terrain via battlefield.move_unit_on_map
        """
        x, y = self.position
        new_x = x + 0.1
        new_y = y
        try:
            bf.move_unit_on_map(self, new_x, new_y)
        except ValueError:
            # collision ou limite → ne bouge plus
            pass

    def __repr__(self):
        return f"<MockUnit id={self.id} pos={self.position}>"


class MockGeneral:
    """
    Général ultra simple :
    - ne fait rien pour l'instant
    """

    def update(self, battlefield, tick):
        pass


# --- MAIN ----------------------------------------------------------
def main():
    args = parse_args()

    print("=== DEMARRAGE SIMULATION ===")

    bf = Battlefield(args.width, args.height)

    # fabrique d’unité
    def make_unit_A():
        return MockUnit("k", size=0.5)

    def make_unit_B():
        return MockUnit("p", size=0.5)

    # spawn deux unités
    u1 = bf.spawn_unit(make_unit_A, 1.0, 1.0, owner=0)
    u2 = bf.spawn_unit(make_unit_B, 10.0, 10.0, owner=1)

    # ajout d’un général
    bf.generals.append(MockGeneral())

    # Visualizer
    visualizer = None
    if not args.no_visual:  # Si l'utilisateur veut un visualizer, (= si il n'a pas demandé de ne pas lancer le visualiser)
        visualizer = CLIVisualizer(args.width, args.height)

    # création de laSimulation
    sim = Simulation(game_map=bf.game_map, generals=bf.generals, battlefield=bf, tick_duration=0.1)
    # lancement de la simulation
    sim.run(max_ticks=args.ticks, visualizer=visualizer)

    print("\n--- SNAPSHOT FINAL ---\n")
    print(bf.snapshot())


# pôur que la fonction main() ne soit exécutée que si le script est lancé directement, mais pas s'il est importé (protextion).
if __name__ == "__main__":
    main()

# commande de test : python -m src.main --ticks 100
# commande de test : python -m src.main --ticks 100 --no-visual
