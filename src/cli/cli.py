# src/cli/cli.py
import sys
import time


class CLIVisualizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.first_frame = True
        self.lines_printed = 0

    def render(self, battlefield, tick):
        # Effacer la frame précédente
        if not self.first_frame:
            sys.stdout.write(f"\033[{self.lines_printed}A")
        else:
            self.first_frame = False

        # Construire la grille
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]

        for unit in battlefield.get_all_units():
            if not unit.is_alive():
                continue

            x = int(unit.position[0])
            y = int(unit.position[1])

            if 0 <= x < self.width and 0 <= y < self.height:
                symbol = unit.type[0].upper()
                if grid[y][x] == ".":
                    grid[y][x] = symbol
                else:
                    grid[y][x] = "*"

        # Affichage
        print(f"=== TICK {tick} ===")
        for row in grid:
            print(" ".join(row))

        sys.stdout.flush()

        # Nombre de lignes affichées :
        self.lines_printed = 1 + self.height

    def finish(self):
        # Remonter à la fin proprement
        sys.stdout.write(f"\033[{self.lines_printed}B")
        sys.stdout.flush()
