import sys

from src.engine.battlefield import Battlefield

# Codes ANSI
RESET = "\033[0m"
BLUE = "\033[34m"
RED = "\033[91m"
YELLOW = "\033[93m"
CLEAR_LINE = "\033[K"
UP = "\033[A"


class CLIVisualizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.first_frame = True
        self.lines_printed = 5 + self.height  # 5 c'est le nb de lignes de headers

    def render_opti(self, bf: Battlefield, tick: int, speed: float = 1.0, paused: bool = False):
        # 1. Remonter le curseur (Double Buffering simulation)
        if not self.first_frame:
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

            x, y = int(unit.position[0]), int(unit.position[1])

            if 0 <= x < self.width and 0 <= y < self.height:
                key = (x, y)
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

        # Header (5 lignes)
        lines.append(f"\n{'=' * 60}")
        status_str = f"{f'TICK {tick:05d}':15} Speed: x{speed:<4.1f}"
        if paused:
            status_str += f" {YELLOW}[PAUSED]{RESET}"
        status_str += CLEAR_LINE
        lines.append(status_str)

        g0 = bf.generals[0].name if bf.generals else "P0"
        g1 = bf.generals[1].name if bf.generals else "P1"

        lines.append(f"{BLUE}{g0:15}{RESET} Units: {alive_counts[0]:3} | HP: {hp_counts[0]:5.0f}")
        lines.append(f"{RED}{g1:15}{RESET} Units: {alive_counts[1]:3} | HP: {hp_counts[1]:5.0f}")
        lines.append(f"{'=' * 60}")

        # Grille
        # On construit ligne par ligne
        for y in range(self.height):
            row_chars = []
            for x in range(self.width):
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
        # Remonter proprement
        sys.stdout.write(f"\033[{self.lines_printed}B")
        sys.stdout.flush()
