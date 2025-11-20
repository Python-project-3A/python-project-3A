import random
import math

from src.map.game_map import GameMap
from src.map.tile import Tile


def test_display_projected_points():
    """
    Affiche une grande carte, mais uniquement quelques points flottants
    projetés sur les tiles entières correspondantes.
    (x, y float) → tile (floor(x), floor(y))
    """
    width, height = 80, 20
    game_map = GameMap(width, height)

    float_points = [
        (5.4, 10.8),
        (12.7, 5.2),
        (18.3, 17.9),
        (23.5, 9.6),
        (40.1, 20.4),
    ]

    for x, y in float_points:
        i, j = math.floor(x), math.floor(y)
        game_map.tiles[(i, j)] = Tile()

    for y in range(height - 1, -1, -1):
        line = ""
        for x in range(width):
            tile = game_map.get_tile(x, y)
            if tile and tile.occupants == [] and (x, y) in game_map.tiles:
                # Est-ce un de nos float_points ?
                if any(math.floor(px) == x and math.floor(py) == y for px, py in float_points):
                    line += "*"   # point flottant projeté
                else:
                    line += "."   # tile normale
        print(line)


def test_display_large_random_points():
    """
    Affiche une grande map et 50 points flottants positionnés aléatoirement.
    Chaque float est projeté sur une tile entière : (floor(x), floor(y)).
    """
    width, height = 80, 20
    game_map = GameMap(width, height)

    num_points = 50
    float_points = [
        (random.uniform(0, width), random.uniform(0, height))
        for _ in range(num_points)
    ]

    # Projection float → tile
    for x, y in float_points:
        i, j = math.floor(x), math.floor(y)
        game_map.tiles[(i, j)] = Tile()

    for y in range(height - 1, -1, -1):
        line = ""
        for x in range(width):
            if any(math.floor(px) == x and math.floor(py) == y for px, py in float_points):
                line += "⁕"  # point flottant
            else:
                line += "."  # vide
        print(line)


if __name__ == "__main__":
    test_display_projected_points()
    print("\n" + "=" * 50 + "\n")
    test_display_large_random_points()
