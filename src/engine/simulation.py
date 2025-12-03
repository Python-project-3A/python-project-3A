import time
from src.engine.battlefield import Battlefield
from src.general.general_base import BaseGeneral
from src.map.game_map import GameMap
from .system import UnitController


class Simulation:
    """
    Boucle de temps du jeu.
    - Appelle les généraux pour décisions stratégiques
    - Appelle les unités pour mouvements/attaques
    - S'arrête en cas de victoire
    """

    def __init__(self, game_map: GameMap, generals: list[BaseGeneral], battlefield: Battlefield):
        self.map = game_map
        self.generals = generals
        self.battlefield = battlefield
        self.tick_count = 0
        self.is_running = False
        self.paused = False
        self.game_speed = 1

    def tick(self, constante_tick_duration):
        # TODO : utiliser contstante_tick_duration comme vitesse constante pour que les untités avance toujours de la même distance par tick.
        """Exécute un tick unique."""
        self.tick_count += 1

        # 1. Les généraux réfléchissent et donnent des ordres
        for general in self.generals:
            general.update(self.battlefield, self.tick_count)

        # 2. Les unités agissent
        for unit in self.battlefield.get_all_units():
            if unit.is_alive():
                UnitController.update(unit, self.battlefield, constante_tick_duration)

        # 3. Condition de fin de bataille
        if self.battlefield.is_battle_over():
            self.is_running = False

    def run(self, input_provider, target_tps=30, max_ticks=20000, visualizer=None):
        """Boucle principale."""
        self.is_running = True

        # CONSTANTE PHYSIQUE : Un tick vaut TOUJOURS 1/30ème de seconde en jeu. Peu importe si l'ordi le calcule en 1ms ou 1h.
        LOGICAL_DT = 1.0 / 30.0

        # LIMITEUR DE VITESSE (SLEEP)
        tick_duration = 1.0 / target_tps if target_tps > 0 else 0  # Si target_tps = 0 (Tournoi), on ne dort jamais (min_frame_duration = 0).Sinon, on dort pour respecter le rythme (ex: 1/30s)

        # VARIABLES DE STATS
        frames_this_second = 0
        second_timer = time.time()
        debut = time.time()  # juste pour connaitre le temps d'execution d'une simulation
        self.real_tick_rate = 0  # Pour une consultation externe

        if visualizer:
            visualizer.render(self.battlefield, 0)  # On affiche le TICK 0, pour voir la position initiale des unités.
            time.sleep(0.05)  # Laisse le temps au visualizer de se mettre en place

        while self.is_running and self.tick_count < max_ticks:
            loop_start = time.time()

            # --- INPUTS ---
            key = input_provider.get_key()
            if key == "p":
                self.paused = not self.paused
            elif key == "q":
                self.is_running = False
            elif key == "=":
                # augmenter la vitesse du jeu
                self.game_speed += 0.2
            elif key == "-":
                # diminuer la vitesse du jeu, minimu de 20%
                self.game_speed = max(0.2, self.game_speed - 0.2)

            # --- LOGIQUE (TPS) ----
            if not self.paused:
                self.tick(LOGICAL_DT * self.game_speed)

                # STATS DE PERFORMANCE
                frames_this_second += 1
                if time.time() - second_timer >= 1.0:
                    self.real_tick_rate = frames_this_second
                    frames_this_second = 0
                    second_timer = time.time()
                    # print(f"TPS Réel: {self.real_tick_rate}")

            # --- RENDU (FPS) ---
            if visualizer:
                visualizer.render(self.battlefield, self.tick_count)

                # ---  SYNCHRONISATION (limiteur de frame) ---
                # Si on veut 30 TPS, et que le calcul a pris 0.01s, on sleep 0.023s. Si le calcul a pris 0.04s (lag), on ne dort pas (on est déjà en retard)
                elapsed = time.time() - loop_start
                wait = tick_duration - elapsed

                if wait > 0:
                    time.sleep(wait)

        if visualizer:
            visualizer.finish()  # Remonter à la fin proprement

        print(f"Simulation terminée après {self.tick_count} ticks. Durée : {time.time() - debut}s")
