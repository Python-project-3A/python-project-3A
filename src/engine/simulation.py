# src/engine/simulation.py
import time
import msvcrt

FPS = 30
paused = False


def read_key():
    """
    Lecture non bloquante d'une touche sous Windows (msvcrt).
    Retourne un caractère en minuscule, ou None si aucune touche.
    """
    if msvcrt.kbhit():
        key = msvcrt.getch()
        try:
            key = key.decode().lower()
        except UnicodeDecodeError:
            return None
        return key
    return None


class Simulation:
    """
    Boucle de temps du jeu.
    - Appelle les généraux pour décisions stratégiques
    - Appelle les unités pour mouvements/attaques
    - S'arrête en cas de victoire
    """

    def __init__(self, game_map, generals, battlefield, tick_duration=0.1):
        self.map = game_map
        self.generals = generals
        self.battlefield = battlefield
        self.tick_duration = tick_duration
        self.tick_count = 0
        self.is_running = False
        self.paused = False

    def tick(self):
        """Exécute un tick unique."""
        self.tick_count += 1

        # 1. Les généraux réfléchissent et donnent des ordres
        for general in self.generals:
            general.update(self.battlefield, self.tick_count)

        # 2. Les unités agissent
        for unit in self.battlefield.get_all_units():
            if unit.is_alive():
                unit.update(self.battlefield, self.tick_count)

        # 3. Condition de fin de bataille
        if self.battlefield.is_battle_over():
            self.is_running = False

    def run(self, max_ticks=2000, visualizer=None):
        """Boucle principale."""
        self.is_running = True
        last_render = 0
        render_interval = 1 / FPS  # 30 FPS (modifiable) timer indépendant du tick
        debut = time.time()

        if visualizer:
            # On affiche le TICK 0, pour voir la position initiale des unités.
            visualizer.render(self.battlefield, 0)
            time.sleep(0.05)  # laisser le temps au visualizer de se mettre en place

        while self.is_running and self.tick_count < max_ticks:
            # --- LECTURE CLAVIER ---
            key = read_key()
            if key == "p":
                self.paused = True

                # -------- MODE PAUSE --------
                # Aucun tick, aucun render → console figée
                while True:
                    key2 = read_key()
                    if key2 == "p":
                        self.paused = False
                        break
                    time.sleep(0.05)

            # -------- MODE NORMAL --------
            self.tick()
            now = time.time()  # NB : techniquement c'est utilie que si on a un visualizer -> a changer ?

            if visualizer and (now - last_render) >= render_interval:  # on affiche que si le temps dépasse 1/30
                visualizer.render(self.battlefield, self.tick_count)
                # print(f"TICK {self.tick_count}")  # pour debug
                last_render = now
                # évite l'affichage écrasé (limiter a 50 ms soit 50 fps max)
                time.sleep(0.05)

        if visualizer:
            visualizer.finish()  # Remonter à la fin proprement

        print(f"Simulation terminée après {self.tick_count} ticks. Durée : {time.time() - debut}s")
