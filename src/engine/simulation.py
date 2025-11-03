import time
from typing import List


class Simulation:
    def __init__(self, game_map, generals, tick_duration=0.1):
        """
        game_map : instance de GameMap
        generals : liste [general_joueur1, general_joueur2]
        tick_duration : durée entre 2 ticks (en secondes)
        """
        self.map = game_map
        self.generals = generals
        self.tick_duration = tick_duration
        self.tick_count = 0
        self.is_running = False

    def run(self, max_ticks=10000, visualizer=None):
        """Boucle principale de simulation"""
        self.is_running = True

        while self.is_running and self.tick_count < max_ticks:
            self.tick_count += 1

            # 1. Mettre à jour chaque général IA
            for general in self.generals:
                general.update(self.map, self.tick_count)

            # 2. Faire agir chaque unité (mouvements, attaques)
            for unit in self.map.get_all_units():
                if unit.is_alive():
                    unit.update(self.map, self.tick_count)

            # 3. Vérifier conditions de victoire
            if self.map.is_battle_over():
                self.is_running = False

            # 4. Appeler la visualisation (si fournie)
            if visualizer:
                visualizer.render(self.map, self.tick_count)

            # 5. Attendre avant le prochain tick
            time.sleep(self.tick_duration)

        print(f"Simulation terminée après {self.tick_count} ticks.")
