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

    def tick(self):
        """Exécute un tick unique de simulation."""
        self.tick_count += 1
        for general in self.generals:
            general.update(self.map, self.tick_count)

        for unit in self.map.get_all_units():
            if unit.is_alive():
                unit.update(self.map, self.tick_count)

        if self.map.is_battle_over():
            self.is_running = False

    def run(self, max_ticks=10000, visualizer=None):
        self.is_running = True
        while self.is_running and self.tick_count < max_ticks:
            self.tick()
            if visualizer:
                visualizer.render(self.map, self.tick_count)
            time.sleep(self.tick_duration)
        print(f"Simulation terminée après {self.tick_count} ticks.")
