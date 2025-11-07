import random

from src.map.game_map import GameMap
from src.map.tile import Tile


def test_display_floating_points():
    """Affiche uniquement quelques points flottants sur une carte sombre."""
    width, height = 120, 120
    game_map = GameMap(width, height)

    points = [
        (5.4, 10.8),
        (12.7, 5.2),
        (18.3, 17.9),
        (23.5, 9.6),
        (40.1, 20.4),
    ]

    for x, y in points:
        game_map.add_tile(x, y, Tile())

    for y in range(height - 1, -1, -1):
        line = ""
        for x in range(width):
            found = any((round(tx), round(ty)) == (x, y) for tx, ty in game_map.tiles)
            line += "*" if found else "·"
        print(line)


def test_display_large_map():
    """Test affichage d'une grande carte avec points flottants."""
    width, height = 120, 120
    game_map = GameMap(width, height)

    num_points = 50
    points = [
        (random.uniform(0, width), random.uniform(0, height)) for _ in range(num_points)
    ]

    for x, y in points:
        game_map.add_tile(x, y, Tile())

    for y in range(height - 1, -1, -1):
        line = ""
        for x in range(width):
            found = any(
                abs(x - tx) < 1 and abs(y - ty) < 1 for tx, ty in game_map.tiles
            )
            line += "⁕" if found else "·"
        print(line)


if __name__ == "__main__":
    test_display_large_map()
