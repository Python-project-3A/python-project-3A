# src/engine/simulation.py
import time
import msvcrt

FPS = 30
paused = False

# === CONSTANTES GLOBALES DU MOTEUR TEMPS ===
DEFAULT_FPS = 30  # FPS max du visualiseur (affichage)
DEFAULT_SPEED = 1.0  # x1 (sera modifié via argparse dans main)
# Le vrai rythme du jeu dépend de tick_duration passé au constructeur


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
        self.tick_duration = tick_duration  # tick_duration = durée réelle (en secondes) entre deux ticks. Exemple : 1/30 = 0.033s → 30 ticks/sec ou (1/30) / 2 = 0.016s → x2 vitesse
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

    def run(self, max_ticks=20000, visualizer=None):
        """Boucle principale."""
        self.is_running = True
        debut = time.time()

        # Gestion FPS du visualiseur
        last_render = 0
        render_interval = 1 / DEFAULT_FPS  # 30 FPS (modifiable) timer indépendant du tick

        # Horloge interne
        next_tick_time = time.time()

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

            # -------- TICK LOGIQUE --------
            if visualizer:
                # Mode VISUEL → respecter le temps réel
                now = time.time()
                if now >= next_tick_time:
                    self.tick()
                    next_tick_time += self.tick_duration
            else:
                # Mode SANS VISUEL → ticks en vitesse max
                self.tick()

            if visualizer and (now - last_render) >= render_interval:
                visualizer.render(self.battlefield, self.tick_count)
                # print(f"TICK {self.tick_count}")  # pour debug
                last_render = now
                # évite l'affichage écrasé (limiter a 50 ms soit 50 fps max)
                time.sleep(0.05)

        if visualizer:
            visualizer.finish()  # Remonter à la fin proprement

        print(f"Simulation terminée après {self.tick_count} ticks. Durée : {time.time() - debut}s")
