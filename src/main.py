# src/main.py
from src.engine.battlefield import Battlefield
from src.engine.simulation import Simulation

# --- MOCKS POUR TEST ---------------------------------------------


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
    - ne fait rien pour l’instant
    """

    def update(self, battlefield, tick):
        pass


# --- MAIN ----------------------------------------------------------


def main():
    print("=== DEMARRAGE SIMULATION ===")

    bf = Battlefield(width=20, height=20)

    # fabrique d’unité
    def make_unit_A():
        return MockUnit("A", size=0.5)

    def make_unit_B():
        return MockUnit("B", size=0.8)

    # spawn deux unités
    u1 = bf.spawn_unit(make_unit_A, 1.0, 1.0, owner=0)
    u2 = bf.spawn_unit(make_unit_B, 1.8, 1.0, owner=1)

    # ajout d’un général
    bf.generals.append(MockGeneral())

    # Simulation
    sim = Simulation(
        game_map=bf.game_map, generals=bf.generals, battlefield=bf, tick_duration=0.1
    )

    sim.run(max_ticks=50)

    print("\n--- SNAPSHOT FINAL ---")
    print(bf.snapshot())


if __name__ == "__main__":
    main()
