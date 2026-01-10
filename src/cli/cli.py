import sys
import os
import shutil  # pour connaitre la taille du terminal

from src.engine.battlefield import Battlefield

# Codes ANSI
RESET = "\033[0m"
BLUE = "\033[34m"
RED = "\033[91m"
YELLOW = "\033[93m"
CLEAR_LINE = "\033[K"
UP = "\033[A"
DOWN = "\033[B"


class CLIVisualizer:
    def __init__(self, map_width, map_height):
        if os.name == "nt":
            self.setup_terminal()
        self.map_width = map_width
        self.map_height = map_height
        self.first_frame = True
        self.lines_printed = 0
        # 6 + self.map_height  # 6 c'est le nb de lignes de headers

        # taille du terminal
        terminal_width, terminal_height = shutil.get_terminal_size(fallback=(80, 24))  # détection de la taille du terminal
        safe_width = terminal_width - 2  # -2 marge de sécurité
        max_terminal_width = safe_width // 2
        self.view_width = min(map_width, max_terminal_width)
        available_height = terminal_height - 7  # 7 c'est le nb de lignes de headers + 1 (marge de sécu)
        safe_height = max(5, available_height)  # on affiche au moins 5 lignes de la map même si fait du scroll up
        self.view_height = min(map_height, safe_height)

        # position de la cam
        self.cam_x = 0
        self.cam_y = 0

    @staticmethod
    def setup_terminal():
        """
        Active le support ANSI sur Windows si nécessaire.
        """
        import ctypes

        # Récupérer le handle de la sortie standard (stdout)
        kernel32 = ctypes.windll.kernel32
        hStdOut = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()  # Récupérer le mode actuel
        kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode))
        mode.value |= 0x0004  # Activer le bit 0x0004 (ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        kernel32.SetConsoleMode(hStdOut, mode)  # Appliquer le nouveau mode

    def move_camera(self, dx: int, dy: int):
        """Déplace la caméra en s'assurant qu'elle ne sort pas de la map."""
        self.cam_x += dx
        self.cam_y += dy

        # bornage de la cam
        max_x = max(0, self.map_width - self.view_width)
        max_y = max(0, self.map_height - self.view_height)

        self.cam_x = max(0, min(self.cam_x, max_x))
        self.cam_y = max(0, min(self.cam_y, max_y))

    def render(self, bf: Battlefield, tick: int, speed: float = 1.0, paused: bool = False):
        # 1. Remonter le curseur (Double Buffering simulation)
        if not self.first_frame and self.lines_printed > 0:
            # On remonte de N lignes
            sys.stdout.write(f"\033[{self.lines_printed}A")
        self.first_frame = False

        # 2. Préparer le buffer d'affichage (Dictionnaire spars)
        # Clé = (x, y), Valeur = (char, color_code)
        display_buffer = {}
        counts = {}  # Pour gérer les collisions
        alive_counts = {0: 0, 1: 0}  # 3. Remplir avec les unités, optimisation : On ne fait qu'une passe
        hp_counts = {0: 0, 1: 0}

        for unit in bf.get_all_units():
            if not unit.is_alive():
                continue

            # Stats globales
            alive_counts[unit.owner] += 1
            hp_counts[unit.owner] += unit.hp

            # x = max(0, min(int(round(unit.position[0])), self.map_width - 1))
            # y = max(0, min( int(round(unit.position[1])), self.map_height - 1))
            x, y = int(unit.position[0]), int(unit.position[1])

            if self.cam_x <= x < self.cam_x + self.view_width and self.cam_y <= y < self.cam_y + self.view_height:
                screen_x = x - self.cam_x
                screen_y = y - self.cam_y

                key = (screen_x, screen_y)

                if key in counts:
                    counts[key] += 1
                    display_buffer[key] = (str(counts[key]), YELLOW)
                else:
                    counts[key] = 1
                    symbol = unit.name[0].upper()
                    color = BLUE if unit.owner == 0 else RED
                    display_buffer[key] = (symbol, color)

        # 4. Construire le buffer de texte
        lines = []

        # Header (6 lignes)
        lines.append(f"{'=' * 60}")
        status_str = f"{f'TICK {tick:05d}':15} Speed: x{speed:<4.1f}"
        if paused:
            status_str += f" {YELLOW}[PAUSED]{RESET}"
        lines.append(status_str + CLEAR_LINE)

        g0 = bf.generals[0].name if bf.generals else "P0"
        g1 = bf.generals[1].name if bf.generals else "P1"

        lines.append(f"{BLUE}{g0:15}{RESET} Units: {alive_counts[0]:3} | HP: {hp_counts[0]:5.0f}" + CLEAR_LINE)
        lines.append(f"{RED}{g1:15}{RESET} Units: {alive_counts[1]:3} | HP: {hp_counts[1]:5.0f}" + CLEAR_LINE)
        lines.append(f"{'-' * 40}{f' [CAM: {self.cam_x},{self.cam_y}]'}{'-' * (20 - len(f' [CAM: {self.cam_x},{self.cam_y}]'))}")
        lines.append(f"{'=' * 60}")

        # Grille
        # On construit ligne par ligne
        for y in range(self.view_height):
            row_chars = []
            for x in range(self.view_width):
                if (x, y) in display_buffer:
                    char, color = display_buffer[(x, y)]
                    row_chars.append(f"{color}{char}{RESET}")
                else:
                    row_chars.append(".")  # Fond vide
            lines.append(" ".join(row_chars))  # Espace pour aérer horizontalement

        # 5. Affichage final (Flush unique pour éviter le scintillement)
        full_output = "\n".join(lines) + "\n"
        sys.stdout.write(full_output)
        sys.stdout.flush()

        self.lines_printed = len(lines) + 1  # +1 pour le dernier \n

    def finish(self):
        """
        Cleans up the CLI visualizer.
        """
        print("\nCLI Visualizer shutting down.")
