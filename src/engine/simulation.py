# src/engine/simulation.py

import platform  # Pour vérifier le système d'exploitation (OS)
import sys  # Pour l'accès à stdout et stdin
import time

# --- Imports pour la lecture de touche multiplateforme ---
system_name = platform.system()

if system_name == "Windows":
    # Import spécifique à Windows
    import msvcrt
else:
    # Imports spécifiques à Unix/Linux
    import select  # Pour la vérification non bloquante
    # termios et tty seront importés à l'intérieur de Simulation.run
# ---------------------------------------------------------


FPS = 30
# 'paused = False' a été retiré car défini dans la classe

# === CONSTANTES GLOBALES DU MOTEUR TEMPS ===
DEFAULT_FPS = 30  # FPS max du visualiseur (affichage)
DEFAULT_SPEED = 1.0  # x1 (sera modifié via argparse dans main)
# Le vrai rythme du jeu dépend de tick_duration passé au constructeur


def read_key():
    """
    Lecture de touche non bloquante pour Windows et Unix/Linux.
    Retourne un caractère en minuscule, ou None si aucune touche n'est pressée.

    NOTE : Sous Unix/Linux, cela nécessite que le TTY soit en mode cbreak,
    ce qui est géré par Simulation.run().
    """
    if system_name == "Windows":
        # --- Implémentation Windows (msvcrt) ---
        if msvcrt.kbhit():
            key = msvcrt.getch()
            try:
                # Décoder et mettre la touche en minuscule
                return key.decode().lower()
            except UnicodeDecodeError:
                return None
        return None

    # --- Implémentation Unix/Linux (select) ---
    else:
        # Vérifie si des données sont prêtes à être lues sur l'entrée standard (fd 0)
        # Un timeout de 0 signifie une vérification non bloquante
        try:
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                # Lit un caractère (nécessite la configuration TTY dans Simulation.run)
                key = sys.stdin.read(1)
                return key.lower()
            return None
        except OSError:
            # Gère le cas où select pourrait échouer (ex: terminal déconnecté)
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
        last_render = 0
        render_interval = 1 / FPS  # Intervalle de rendu (indépendant du tick)
        debut = time.time()

        # --- Configuration TTY pour l'entrée non bloquante Unix/Linux (Correction de la Pause) ---
        old_settings = None
        if system_name != "Windows":
            try:
                # Import ici pour éviter les problèmes si le module n'est pas disponible
                import termios
                import tty

                # Sauvegarde des paramètres actuels du terminal
                old_settings = termios.tcgetattr(sys.stdin)
                # Configure le terminal en mode cbreak (non canonique, sans écho)
                tty.setcbreak(sys.stdin.fileno())
            except Exception as e:
                # Si l'exécution n'est pas dans un environnement TTY (ex: certains IDEs), la pause ne fonctionnera pas
                print(f"Warning: Impossible de configurer le mode TTY pour la lecture de touche. La pause ('p') pourrait ne pas fonctionner. Erreur : {e}")
        # -----------------------------------------------------------------------------------------

        if visualizer:
            # On affiche le TICK 0, pour voir la position initiale des unités.
            visualizer.render(self.battlefield, 0)
            time.sleep(0.05)  # Laisse le temps au visualizer de se mettre en place

        while self.is_running and self.tick_count < max_ticks:
            # --- LECTURE CLAVIER ---
            key = read_key()
            if key == "p":
                self.paused = True
                print("\n--- PAUSE --- Appuyez sur 'p' pour reprendre...")  # Feedback visuel optionnel

                # -------- MODE PAUSE --------
                # Aucun tick, aucun render → console figée
                while self.paused:
                    key2 = read_key()
                    if key2 == "p":
                        self.paused = False
                        break
                    time.sleep(0.05)

                # Effectue le rendu immédiatement après la reprise pour effacer le message de PAUSE
                if visualizer:
                    visualizer.render(self.battlefield, self.tick_count)

            # -------- MODE NORMAL --------
            if not self.paused:
                self.tick()
                now = time.time()

                if visualizer and (now - last_render) >= render_interval:
                    visualizer.render(self.battlefield, self.tick_count)
                    last_render = now
                    # Évite l'affichage écrasé (limiter à 50 ms soit 50 fps max)
                    time.sleep(0.05)

        # --- 🛠️ Restauration TTY pour l'entrée non bloquante Unix/Linux ---
        if system_name != "Windows" and old_settings is not None:
            try:
                # Restaure les paramètres du terminal
                import termios

                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception as e:
                print(f"Warning: Impossible de restaurer les paramètres TTY: {e}")
        # ---------------------------------------------------------------

        if visualizer:
            visualizer.finish()  # Remonter à la fin proprement

        print(f"Simulation terminée après {self.tick_count} ticks. Durée : {time.time() - debut}s")
