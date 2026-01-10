import time
from src.engine.battlefield import Battlefield
from src.general.general_base import BaseGeneral
from src.cli.cli import CLIVisualizer
from src.map.game_map import GameMap
from src.pygame.pygame_visualizer import PygameVisualizer
from src.pygame.pygame_input_provider import PygameInputProvider
from src.engine.input_provider import ConsoleInputProvider
from .system import UnitController
from .html_snapshot import HTMLSnapshot
from .save_load import save_game, load_game


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
        self.snapshot_utility = HTMLSnapshot(battlefield)
        self.LOGICAL_DT = 1.0 / 30.0

    def tick(self, dt):
        """Exécute un tick unique."""
        self.tick_count += 1

        # 1. Les généraux réfléchissent
        for general in self.generals:
            general.update(self.battlefield, self.tick_count, dt)

        all_units = self.battlefield.get_all_units()

        # 2. PHASE DE MOUVEMENT DES UNITÉS
        for unit in all_units:
            if unit.is_alive():
                UnitController.process_movement(unit, self.battlefield, dt)

        # 3. PHASE D'ATTAQUE DES UNITÉS
        for unit in all_units:
            if unit.is_alive():
                UnitController.process_attack(unit, self.battlefield)

        # --- 4. PHASE DE RESOLUTION DES DEGATS ---
        # On applique tous les dégâts en attente d'un coup
        for unit in all_units:
            if unit.pending_damage > 0:
                unit.hp = max(0, unit.hp - unit.pending_damage)
                unit.pending_damage = 0  # Reset pour le prochain tour

        # --- 4. PHASE DE NETTOYAGE ---
        self.battlefield.remove_dead_units()

        # 5. Fin de bataille
        if self.battlefield.is_battle_over():
            self.is_running = False

    def run(self, input_provider, target_tps=30, max_ticks=20000, visualizer=None):
        """Boucle principale."""
        self.is_running = True

        # LIMITEUR DE VITESSE (SLEEP)
        tick_duration = 1.0 / target_tps if target_tps > 0 else 0  # Si target_tps = 0 (Tournoi), on ne dort jamais (min_frame_duration = 0).Sinon, on dort pour respecter le rythme (ex: 1/30s)

        # VARIABLES DE STATS
        frames_this_second = 0
        second_timer = time.time()
        debut = time.time()  # juste pour connaitre le temps d'execution d'une simulation
        self.real_tick_rate = 0  # Pour une consultation externe

        if visualizer:
            visualizer.render(self.battlefield, 0, speed=self.game_speed, paused=self.paused)  # On affiche le TICK 0, pour voir la position initiale des unités.
            time.sleep(0.05)  # Laisse le temps au visualizer de se mettre en place

        is_gui = isinstance(visualizer, PygameVisualizer)
        step = 20 if is_gui else 2  # vitesse de déplacement de la cam, on met ce qu'on veut

        while self.is_running and self.tick_count < max_ticks:
            loop_start = time.time()

            # --- TERMINAL INPUTS ---
            if not is_gui:
                if input_provider:
                    terminal_key = input_provider.get_key()
                    switch_signal = self.base_key_matching(terminal_key)

                    if switch_signal == "switch_visualizer":
                        if visualizer:
                            visualizer.finish()
                        if input_provider:
                            input_provider.__exit__(None, None, None)

                        # Switch to GUI
                        visualizer = PygameVisualizer(battlefield=self.battlefield)
                        input_provider = PygameInputProvider()
                        input_provider.__enter__()

                        is_gui = True
                        step = 20
                        continue

                    if visualizer and terminal_key in ["w", "a", "s", "d", "z", "q"]:  # pour clavier qwerty et azerty
                        step = 2
                        self.direction_key_matching(terminal_key, step, visualizer=visualizer)

            # --- GUI INPUTS ---
            if is_gui:
                if input_provider:
                    pygame_key = input_provider.get_key()
                    switch_signal = self.base_key_matching(pygame_key)

                    if switch_signal == "switch_visualizer":
                        # Clean up current visualizer
                        if visualizer:
                            visualizer.finish()
                        if input_provider:
                            input_provider.__exit__(None, None, None)

                        # Switch to CLI
                        visualizer = CLIVisualizer(self.battlefield.width, self.battlefield.height)
                        input_provider = ConsoleInputProvider()
                        input_provider.__enter__()

                        is_gui = False
                        step = 2
                        continue

                    self.direction_key_matching(pygame_key, step, visualizer=visualizer)
                    match pygame_key:
                        case "zoom_in":
                            visualizer.zoom(1)
                        case "zoom_out":
                            visualizer.zoom(-1)

                    if hasattr(input_provider, "get_camera_drag"):
                        drag_dx, drag_dy = input_provider.get_camera_drag()
                        if drag_dx != 0 or drag_dy != 0:
                            visualizer.move_camera(drag_dx, drag_dy)

            # --- LOGIQUE (TPS) ----
            if not self.paused:
                self.tick(self.LOGICAL_DT * self.game_speed)

                # STATS DE PERFORMANCE
                frames_this_second += 1
                if time.time() - second_timer >= 1.0:
                    self.real_tick_rate = frames_this_second
                    frames_this_second = 0
                    second_timer = time.time()
                    # print(f"TPS Réel: {self.real_tick_rate}")

            # --- RENDU (FPS) ---
            if visualizer:
                visualizer.render(self.battlefield, self.tick_count, speed=self.game_speed, paused=self.paused)

            # ---  SYNCHRONISATION (limiteur de frame) ---
            # Si on veut 30 TPS, et que le calcul a pris 0.01s, on sleep 0.023s. Si le calcul a pris 0.04s (lag), on ne dort pas (on est déjà en retard)
            elapsed = time.time() - loop_start
            wait = tick_duration - elapsed

            if wait > 0:
                time.sleep(wait)

        print(f" Simulation terminée après {self.tick_count} ticks. Durée : {(time.time() - debut):.4f}s. Environ : {self.tick_count / (time.time() - debut):.0f} TPS.")

    def base_key_matching(self, key: str):
        match key:
            case "p":
                self.paused = not self.paused
            case "escape":
                self.is_running = False
            case "=":
                self.game_speed += 0.2
            case "-":
                self.game_speed = max(0.2, self.game_speed - 0.2)
            case "r":
                self.game_speed = 1
            case "tab":
                self.snapshot_utility.save_and_open_html_file(self.tick_count)
            case "F9":
                return "switch_visualizer"
            case "F11":
                # autoriser d'autres noms de fichier de sauvegarde plus tard
                save_game(self)
            case "F12":
                # Quick Load
                try:
                    # Remplacer la simulation actuelle par la version chargée
                    loaded_sim = load_game()
                    self.map = loaded_sim.map
                    self.generals = loaded_sim.generals
                    self.battlefield = loaded_sim.battlefield
                    self.tick_count = loaded_sim.tick_count
                    self.paused = True
                    self.snapshot_utility = loaded_sim.snapshot_utility  # Mise à jour de l'utilitaire
                except FileNotFoundError:
                    print("\n Erreur: Pas de Quick Save trouvée.")
                except Exception as e:
                    print(f"\n Erreur pendant le rechargement: {e}")

    @staticmethod
    def direction_key_matching(key: str, step: int, visualizer):
        match key:
            case "z":
                visualizer.move_camera(0, -step)  # haut
            case "w":
                visualizer.move_camera(0, -step)  # haut
            case "s":
                visualizer.move_camera(0, step)  # bas
            case "q":
                visualizer.move_camera(-step, 0)  # gauche
            case "a":
                visualizer.move_camera(-step, 0)  # gauche
            case "d":
                visualizer.move_camera(step, 0)  # droite

    def to_dict(self):
        """
        retourne un dictionnaire qui associe chaque nom d'attribut à sa valeur actuelle
        utile pour le save/load
        """
        data = {"tick_count": self.tick_count, "generals": [g.to_dict() for g in self.generals]}

        return data
