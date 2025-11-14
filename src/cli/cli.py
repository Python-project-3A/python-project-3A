# src/cli/cli.py
import sys
import time


class CLIVisualizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.first_frame = True

    def _unit_symbol(self, unit):
        t = unit.type.lower()
        if t.startswith("k"):
            return "K"
        if t.startswith("p"):
            return "P"
        if t.startswith("c"):
            return "C"
        return "?"

    def render(self, battlefield, tick):
        # Déplacement curseur : remonter la frame précédente
        if not self.first_frame:
            sys.stdout.write(f"\x1b[{self.height + 3}A")
        else:
            self.first_frame = False

        # Génération de la grille vide
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]

        # Placement des unités
        for unit in battlefield.get_all_units():
            if not unit.is_alive():
                continue

            x = int(unit.position[0])
            y = int(unit.position[1])

            if 0 <= x < self.width and 0 <= y < self.height:
                symbol = self._unit_symbol(unit)
                if grid[y][x] == ".":
                    grid[y][x] = symbol
                else:
                    grid[y][x] = "*"

        print(f"=== TICK {tick} ===")
        for row in grid:
            print(" ".join(row))

        sys.stdout.flush()
