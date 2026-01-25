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


CAMERA_SPEED_MULTIPLIER = 2


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
        self.game_speed = 1.0
        self.snapshot_utility = HTMLSnapshot(battlefield)
        self.error: str | None = None
        self.error_timer = 0
        self.game_save: str | None = None
        self.game_save_timer = 0
        self.game_load: str | None = None
        self.game_load_timer = 0

        self.TARGET_TPS = 60
        self.FIXED_DT = 1.0 / self.TARGET_TPS

    def trigger_error(self, message: str):
        self.error = message
        self.error_timer = 60

    def trigger_game_save(self):
        self.game_save = "Game saved"
        self.game_save_timer = 60

    def trigger_game_load(self):
        self.game_load = "Game loaded"
        self.game_load_timer = 60

    def tick(self, dt):
        """Exécute un tick unique."""

        if self.battlefield.is_battle_over():
            return

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
            # If we are in GUI mode, we keep the loop alive to show the Game Over screen.
            # If we are in CLI/Headless mode, we exit immediately.
            is_gui = isinstance(getattr(self, "visualizer", None), PygameVisualizer)
            if not is_gui:
                self.is_running = False

    def run(self, input_provider, target_tps=60, max_ticks=20000, visualizer=None):
        """Boucle principale."""
        self.is_running = True
        self.visualizer = visualizer

        # LIMITEUR DE VITESSE (SLEEP)
        # tick_duration = 1.0 / target_tps if target_tps > 0 else 0  # Si target_tps = 0 (Tournoi), on ne dort jamais (min_frame_duration = 0).Sinon, on dort pour respecter le rythme (ex: 1/30s)
        if target_tps > 0:
            self.TARGET_TPS = target_tps
            self.FIXED_DT = 1.0 / self.TARGET_TPS

        # VARIABLES DE STATS
        frames_this_second = 0
        second_timer = time.time()
        debut = time.time()  # juste pour connaitre le temps d'execution d'une simulation
        self.real_tick_rate = 0  # Pour une consultation externe

        if visualizer:
            visualizer.render(self.battlefield, 0, speed=self.game_speed, paused=self.paused)  # On affiche le TICK 0, pour voir la position initiale des unités.
            time.sleep(0.05)  # Laisse le temps au visualizer de se mettre en place

        is_gui = isinstance(visualizer, PygameVisualizer)
        base_step = 20 if is_gui else 2  # vitesse de déplacement de la cam, on met ce qu'on veut

        # INITIALISATION ACCUMULATOR
        current_time = time.time()
        accumulator = 0.0

        while self.is_running and self.tick_count < max_ticks:
            # CALCUL DU TEMPS ÉCOULÉ
            new_time = time.time()
            frame_time = new_time - current_time
            current_time = new_time

            # "Spiral of Death" protection (lu sur un Reddit) : pour pas rattraper 5000 ticks si on a un freeze
            if frame_time > 0.25:
                frame_time = 0.25

            # ON REMPLIT L'ACCUMULATOR
            if not self.paused:
                accumulator += frame_time * self.game_speed

            # TODO : mettre tout ça dans une fonction : self._handle_inputs(input_provider, visualizer, base_step, is_gui)

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
                        base_step = 20
                        continue

                    if visualizer and terminal_key in ["w", "a", "s", "d", "z", "q"]:  # pour clavier qwerty et azerty
                        step = base_step * CAMERA_SPEED_MULTIPLIER if input_provider.is_shift_pressed() else base_step
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
                        base_step = 2
                        continue

                    # Calculate step with shift modifier
                    step = base_step * CAMERA_SPEED_MULTIPLIER if input_provider.is_shift_pressed() else base_step

                    self.direction_key_matching(pygame_key, step, visualizer=visualizer)
                    match pygame_key:
                        case "zoom_in":
                            visualizer.zoom(1)
                        case "zoom_out":
                            visualizer.zoom(-1)
                        case "F1":
                            visualizer.show_perf_stats = not visualizer.show_perf_stats
                        case "F2":
                            visualizer.show_generals_stats = not visualizer.show_generals_stats

                    if hasattr(input_provider, "get_camera_drag"):
                        drag_dx, drag_dy = input_provider.get_camera_drag()
                        if drag_dx != 0 or drag_dy != 0:
                            visualizer.move_camera(drag_dx, drag_dy)

                    # ------------------------ FIN DE LA FONCTION INPUT ----------------------------------------

            # Récupération du visualiser au cas où ça ait changé
            # if getattr(self, "visualizer", None):
            #     is_gui = isinstance(self.visualizer, PygameVisualizer)

            # BOUCLE PHYSIQUE (Consommation Accumulateur)
            # == executer autant de ticks que nécessaire pour vider le temps accumulé.
            while accumulator >= self.FIXED_DT:
                self.tick(self.FIXED_DT)
                accumulator -= self.FIXED_DT
                if not self.is_running or self.tick_count >= max_ticks:
                    break

            # STATS PERF
            frames_this_second += 1
            if time.time() - second_timer >= 1.0:
                self.real_tick_rate = frames_this_second
                frames_this_second = 0
                second_timer = time.time()

            # --- RENDU (FPS) ---
            # Le rendu se fait "autant que possible", décorrélé de la physique
            if self.visualizer:
                self.visualizer.render(self.battlefield, self.tick_count, speed=self.game_speed, paused=self.paused, game_save=self.game_save, game_load=self.game_load, error=self.error)

            # [MODIF] PAUSE CPU (VSYNC-like)
            time.sleep(0.005)

            if self.error_timer > 0:
                self.error_timer -= 1
                if self.error_timer <= 0:
                    self.error = None

            if self.game_save_timer > 0:
                self.game_save_timer -= 1
                if self.game_save_timer <= 0:
                    self.game_save = None

            if self.game_load_timer > 0:
                self.game_load_timer -= 1
                if self.game_load_timer <= 0:
                    self.game_load = None

        print(f" Simulation terminée après {self.tick_count} ticks. Durée : {(time.time() - debut):.4f}s. Environ : {self.tick_count / (time.time() - debut):.0f} TPS.")

    def base_key_matching(self, key: str):
        match key:
            case "p":
                self.paused = not self.paused
            case "escape":
                self.is_running = False
            case "=":
                self.game_speed += 0.2  # TODO : RETIRER CE FONCTIONNEMENT
            case "-":
                self.game_speed = max(0.2, self.game_speed - 0.2)  # TODO : RETIRER CE FONCTIONNEMENT
            case "r":
                self.game_speed = 1
            case "tab":
                self.snapshot_utility.save_and_open_html_file(self.tick_count)
            case "F9":
                return "switch_visualizer"
            case "F11" | "k":
                # autoriser d'autres noms de fichier de sauvegarde plus tard
                save_game(self)
                self.trigger_game_save()
            case "F12" | "l":
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
                    self.trigger_game_load()
                except FileNotFoundError:
                    self.trigger_error("Error: No quick save found")
                except Exception as e:
                    self.trigger_error(f"Error during loading: {e}")

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
