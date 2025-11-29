from __future__ import annotations

import math

from src.units.unit_base import Unit

from .tile import Tile


class GameMap:
    """
    Carte en grille éparse : dict[(ix, iy)] -> Tuile.
    Gère l'accès au terrain et aux occupants.
    """

    def __init__(self, width: int, height: int):
        self.width = int(width)
        self.height = int(height)
        self.tiles: dict[tuple[int, int], Tile] = {}  # grille éparse

    # --------------------------
    # 1. Bounds & Basic Access
    # --------------------------
    def _in_bounds(self, ix: int, iy: int) -> bool:
        return 0 <= ix < self.width and 0 <= iy < self.height

    def get_tile(self, ix: int, iy: int) -> Tile | None:
        """Retourne la tuile si stockée (éparse)."""
        return self.tiles.get((ix, iy))

    def add_tile(self, ix: int, iy: int, tile: Tile | None = None) -> None:
        """Crée ou remplace une tuile à des coordonnées entières."""
        if not self._in_bounds(ix, iy):
            raise ValueError("add_tile: out of bounds")
        if tile is None:
            tile = Tile()
        self.tiles[(ix, iy)] = tile

    def ensure_tile(self, ix: int, iy: int) -> Tile:
        """
        Retourne une tuile ; la crée si elle est absente.
        Utilise setdefault pour une implémentation concise.
        """
        if not self._in_bounds(ix, iy):
            raise ValueError("ensure_tile: out of bounds")

        # Retourne la tuile existante, ou en crée une par défaut et l'insère.
        return self.tiles.setdefault((ix, iy), Tile())

    # --------------------------
    # 2. Terrain / Mouvement
    # --------------------------
    def is_walkable(self, ix: int, iy: int) -> bool:
        """API: Retourne True si l'unité peut marcher sur la case (minimal: toujours True)."""
        if not self._in_bounds(ix, iy):
            return False
        # Logique minimale pour terrain plat : toujours True
        # (À étendre plus tard pour les obstructions/bâtiments)
        return True

    def get_neighbors(self, ix: int, iy: int, diagonals: bool = False) -> list[tuple[int, int]]:
        """API: Retourne les tuiles voisines (4-voisins minimal)."""
        voisins = [(ix + 1, iy), (ix - 1, iy), (ix, iy + 1), (ix, iy - 1)]

        if diagonals:
            # Ajout des 4 voisins diagonaux si demandé
            voisins.extend([(ix + 1, iy + 1), (ix - 1, iy - 1), (ix + 1, iy - 1), (ix - 1, iy + 1)])

        # Retourne uniquement les coordonnées qui sont dans les limites
        return [(x, y) for x, y in voisins if self._in_bounds(x, y)]

    # --------------------------
    # 3. Requêtes spatiales
    # --------------------------

    def get_units_in_radius(self, x: float, y: float, radius: float, all_units: list[Unit]) -> list[Unit]:
        """API: Retourne une liste d'unités dans un rayon continu (float) autour de (x, y)."""
        result: list[Unit] = []
        for unit in all_units:
            ux, uy = getattr(unit, "position", (None, None))
            if ux is None or uy is None:
                continue

            # Distance euclidienne
            distance = math.hypot(ux - x, uy - y)

            if distance <= radius:
                result.append(unit)
        return result

    def get_units_at_tile(self, ix: int, iy: int) -> list[Unit]:
        """API: Retourne les unités occupant la case arrondie (ix, iy)."""
        tile = self.get_tile(ix, iy)
        # Si la tuile existe, retourne ses occupants. Sinon, liste vide.
        return tile.occupants if tile else []

    def get_visible_tiles(self, unit: Unit) -> list[tuple[int, int]]:
        """API: Simule le champ de vision (minimal: toutes les tuiles dans la portée de vision)."""
        # Pour une implémentation minimale sur terrain plat, ceci est une simplification
        vision_range = getattr(unit, "vision_range", 4)  # Utilise l'attribut vision_range de l'unité
        center_x, center_y = unit.position

        visible_tiles: set[tuple[int, int]] = set()

        # Parcourt une boîte autour de l'unité
        for ix in range(int(center_x - vision_range), int(center_x + vision_range + 1)):
            for iy in range(int(center_y - vision_range), int(center_y + vision_range + 1)):
                if self._in_bounds(ix, iy):
                    # Calcule la distance du centre de la tuile au centre de l'unité
                    tile_dist = math.hypot(ix + 0.5 - center_x, iy + 0.5 - center_y)
                    if tile_dist <= vision_range:
                        visible_tiles.add((ix, iy))

        return list(visible_tiles)

    def get_units_in_line_of_sight(self, unit: Unit, all_units: list[Unit]) -> list[Unit]:
        """API: Retourne toutes les unités dans la portée de vision (minimal: équivalent à get_units_in_radius)."""
        # Terrain plat : la portée de vision est la portée de la ligne de mire (Line of Sight)
        vision_range = getattr(unit, "vision_range", 4)
        x, y = unit.position

        # Réutilise la fonction de rayon, car pas d'obstacles visuels pour l'instant
        # Note : Dans AoE, la Line of Sight est la portée de vision, pas la portée d'attaque.
        return self.get_units_in_radius(x, y, vision_range, all_units)

    # --------------------------
    # 4. Pathfinding & Mouvement
    # --------------------------
    def compute_path(self, start: tuple[float, float], goal: tuple[float, float]) -> list[tuple[float, float]]:
        """API: Calcule le chemin (minimal: renvoie juste l'objectif pour un mouvement en ligne droite)."""
        # Mouvement en ligne droite naïve
        return [goal]

    def update_unit_position(self, unit: Unit, old_pos: tuple[float, float], new_pos: tuple[float, float]) -> None:
        """
        API: Met à jour la position de l'unité dans la grille de tuiles (Battlefield appelle cette méthode).
        Ceci est crucial pour maintenir la cohérence de la carte éparse.
        """
        old_ix, old_iy = int(old_pos[0]), int(old_pos[1])
        new_ix, new_iy = int(new_pos[0]), int(new_pos[1])

        # Vérifie si l'unité a changé de case
        if (old_ix, old_iy) != (new_ix, new_iy):
            # 1. Retirer de l'ancienne tuile
            old_tile = self.get_tile(old_ix, old_iy)
            if old_tile is not None:
                old_tile.remove_occupant(unit)
                # Optionnel: Supprimer la tuile si elle devient vide et n'est pas un terrain spécial

            # 2. Ajouter à la nouvelle tuile (assurée d'exister pour l'occupation)
            # On utilise ensure_tile qui crée la tuile si elle n'existe pas encore.
            new_tile = self.ensure_tile(new_ix, new_iy)
            new_tile.add_occupant(unit)

        # Note: Les coordonnées flottantes de l'unité (unit.position) sont mises à jour par le Battlefield.
        # Cette méthode gère uniquement la mise à jour de l'occupation discrète des tuiles.

    # --------------------------
    # 5. Utils
    # --------------------------
    def is_free(self, ix: int, iy: int) -> bool:
        """True si la tuile n'a pas d'occupants ou n'est pas présente (par défaut vide)."""
        tile = self.get_tile(ix, iy)
        return tile is None or tile.is_free()

    def is_free_float(self, x: float, y: float) -> bool:
        """Vérifie si la tuile correspondant à (x, y) est libre."""
        return self.is_free(int(x), int(y))

    def tile_from_float(self, x: float, y: float) -> Tile | None:
        """Convertit une position flottante en tuile, la créant si nécessaire (via ensure_tile)."""
        ix = int(x)
        iy = int(y)
        if not self._in_bounds(ix, iy):
            return None
        return self.ensure_tile(ix, iy)

    def __contains__(self, coords):
        return coords in self.tiles

    def __repr__(self):
        return f"<SparseGameMap {self.width}x{self.height} / {len(self.tiles)} tiles>"
