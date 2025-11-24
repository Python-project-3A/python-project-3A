import random

from src.map.game_map import GameMap


def test_display_projected_points():
    """
    Affiche une carte sparse avec seulement quelques points flottants.
    (x, y float) → (floor(x), floor(y)).
    """
    width, height = 80, 20
    game_map = GameMap(width, height)

    float_points = [
        (5.4, 10.8),
        (12.7, 5.2),
        (18.3, 17.9),
        (23.5, 9.6),
        (40.1, 19.4),  # 20.4 était hors map (y=20 → hors 0..19)
    ]

    # Projection float → tile integer
    for x, y in float_points:
        ix, iy = int(x), int(y)
        if 0 <= ix < width and 0 <= iy < height:
            game_map.ensure_tile(ix, iy)

    # Affichage
    for y in range(height - 1, -1, -1):
        line = ""
        for x in range(width):
            # Est-ce un point projeté ?
            is_point = any(int(px) == x and int(py) == y for px, py in float_points)
            line += "*" if is_point else "."
        print(line)


def test_display_large_random_points():
    """
    Affiche une grande map sparse avec 50 points flottants aléatoires.
    """
    width, height = 80, 20
    game_map = GameMap(width, height)

    num_points = 50
    float_points = [
        (random.uniform(0, width), random.uniform(0, height)) for _ in range(num_points)
    ]

    # Projection float → tile integer
    for x, y in float_points:
        ix, iy = int(x), int(y)
        if 0 <= ix < width and 0 <= iy < height:
            game_map.ensure_tile(ix, iy)

    # Affichage
    for y in range(height - 1, -1, -1):
        line = ""
        for x in range(width):
            is_point = any(int(px) == x and int(py) == y for px, py in float_points)
            line += "⁕" if is_point else "."
        print(line)


if __name__ == "__main__":
    test_display_projected_points()
    print("\n" + "=" * 50 + "\n")
    test_display_large_random_points()
