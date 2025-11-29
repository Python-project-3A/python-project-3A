import sys

from src.engine.battlefield import Battlefield


class CLIVisualizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.first_frame = True
        self.lines_printed = 0

    def render(self, battlefield: Battlefield, tick: int):  # noqa: C901
        # Effacer la frame précédente
        if not self.first_frame:
            sys.stdout.write(f"\033[{self.lines_printed}A")
        else:
            self.first_frame = False

        # Construire la grille vide
        grille = [["." for _ in range(self.width)] for _ in range(self.height)]

        # Placer les unités sur la grille
        for unit in battlefield.get_all_units():
            if not unit.is_alive():
                continue

            x = int(unit.position[0])
            y = int(unit.position[1])

            if 0 <= x < self.width and 0 <= y < self.height:
                # Symbole de l'unité (première lettre du nom)
                symbol = unit.name[0].upper()

                # Couleur selon l'équipe
                if unit.owner == 0:
                    colored_symbol = f"\033[34m{symbol}\033[0m"  # Bleu
                elif unit.owner == 1:
                    colored_symbol = f"\033[91m{symbol}\033[0m"  # Rouge
                else:
                    colored_symbol = symbol

                current_tile = grille[y][x]
                # Placer dans la grille

                if current_tile == ".":
                    grille[y][x] = colored_symbol
                else:
                    # Plusieurs unités sur la même case
                    # Jaune pour collision
                    import re

                    existing_clean = re.sub(r"\033\[\d+m", "", current_tile)

                    if existing_clean.isdigit():
                        count = int(existing_clean) + 1
                    else:
                        count = 2  # First collision

                    # Color yellow and show number
                    grille[y][x] = f"\033[93m{count}\033[0m"

        # Compter les unités vivantes
        alive_by_owner = {0: 0, 1: 0}
        hp_by_owner = {0: 0, 1: 0}

        for unit in battlefield.get_all_units():
            if unit.is_alive():
                alive_by_owner[unit.owner] += 1
                hp_by_owner[unit.owner] += unit.hp

        # Affichage
        header_lines = []
        header_lines.append("=" * 60)
        header_lines.append(f"TICK {tick:04d}")
        header_lines.append("-" * 60)

        # Stats des généraux
        if battlefield.generals:
            gen0 = battlefield.generals[0]
            gen1 = battlefield.generals[1]

            header_lines.append(f"\033[34m{gen0.name:20s}\033[0m │ Units: {alive_by_owner[0]:3d} │ HP: {hp_by_owner[0]:5.0f}")
            header_lines.append(f"\033[91m{gen1.name:20s}\033[0m │ Units: {alive_by_owner[1]:3d} │ HP: {hp_by_owner[1]:5.0f}")

        header_lines.append("=" * 60)

        # Afficher header
        for line in header_lines:
            print(line)

        # Afficher la grille
        for ligne in grille:
            print(" ".join(ligne))

        sys.stdout.flush()
        self.lines_printed = len(header_lines) + self.height

    def finish(self):
        # Remonter proprement
        sys.stdout.write(f"\033[{self.lines_printed}B")
        sys.stdout.flush()
