# src/engine/battlefield.py
from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Callable, Any
from math import hypot  # distance euclidienne : sqrt(dx*dx + dy*dy)
from src.map.game_map import GameMap
from src.map.tile import Tile


class Battlefield:
    """
    Battlefield: état global. Gère:
    - game_map
    - unités (dict id -> instance)
    - généraux (liste)
    - spawn/add/remove/move unit
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.game_map: GameMap = GameMap(width, height)
        self.units: Dict[int, Any] = {}
        self.generals: List[Any] = []
        self._next_unit_id: int = 1

    # ---------- HELPERS--------------
    def isalmost(self, n, m, d=1e-2):  # 1e-2 ou 1e-3 ???
        return (abs(n - m)) < d

    def _assign_id_if_needed(self, unit: Any) -> None:
        """Assigne un id si besoin."""
        if not hasattr(unit, "id") or getattr(unit, "id") is None:
            unit.id = self._next_unit_id
            self._next_unit_id += 1

    @staticmethod  # fontion dans une classe qui ne dépend pas de self
    def _tile_index_from_pos(x: float, y: float) -> Tuple[int, int]:
        """Convertit une position continue (float) en coordonnées discrètes (tile) en utilisant un arrondi inférieur (floor)."""
        return int(x), int(y)  # NB : int(3.99) → 3 -> jsp si c'est la meilleur option. Sinon on peut utiliser round()

    # ---------- SPAWN/ADD/REMOVE UNIT--------------

    def spawn_unit(self, unit_factory: Callable[[], Any], x: float, y: float, owner: int) -> int:
        """
        Créer une instance unité via une fonction factory et l'ajoute au Battlefield.
        Renvoie l'id de l'unité.
        """
        unit = unit_factory()
        self._assign_id_if_needed(unit)
        unit.position = (float(x), float(y))
        unit.owner = owner
        unit.battlefield = self

        ix, iy = self._tile_index_from_pos(x, y)
        tile = self.game_map.ensure_tile(ix, iy)  # ensure tile exists
        tile.add_occupant(unit)  # add unit to structures
        self.units[unit.id] = unit
        return unit.id

    def add_existing_unit(self, unit) -> int:
        """Ajoute une unité existante au Battlefield (tile) et renvoie son id. Pour chager un scénario."""
        x, y = unit.position
        self._assign_id_if_needed(unit)
        tx, ty = self._tile_index_from_pos(x, y)
        tile = self.game_map.ensure_tile(tx, ty)
        tile.add_occupant(unit)
        self.units[unit.id] = unit
        return unit.id

    def add_unit_to_tile(self, unit: Any):
        """
        Ajoute une unité à la tile correspondante à sa position flottante.
        Sert uniquement pour affichage ou regroupement rapide.
        """
        ix, iy = self._tile_index_from_pos(*unit.position)
        tile = self.game_map.ensure_tile(ix, iy)
        if unit not in tile.occupants:
            tile.add_occupant(unit)

    def remove_unit_from_old_tile(self, unit: Any):
        """
        Retire l'unité de la tile correspondant à sa position actuelle.
        Sert uniquement pour mise à jour de la map pour affichage.
        """
        ix, iy = self._tile_index_from_pos(*unit.position)
        tile = self.game_map.get_tile(ix, iy)
        if tile and unit in tile.occupants:
            tile.remove_occupant(unit)

    # ---------- UTILS COLLISIONS ----------

    def check_position(self, unit, new_x: float, new_y: float) -> bool:
        """vérifie si une unité est présente sur ces coordonnées."""
        for other in self.units.values():
            if other is unit:
                continue
            if unit.collides_with_position(other, new_x, new_y):
                return True
        return False

    def resolve_soft_collisions(self, unit):
        for other in self.units.values():
            if other is unit:
                continue
            unit.soft_push(other)

    # ------------- MOUVEMENT --------------

    def attempt_sliding_move(self, unit, new_x, new_y):
        """Tente un glissement si le mouvement direct est bloqué.
        Retourne (x,y) soit corrigé soit identique.
        """

        # tentative direct
        if not self.check_position(unit, new_x, new_y):
            return new_x, new_y

        ux, uy = unit.position

        # slide horizontal
        if not self.check_position(unit, new_x, uy):
            return new_x, uy

        # slide vertical
        if not self.check_position(unit, ux, new_y):
            return ux, new_y

        # petit décalage orthogonal
        eps = 0.3
        if not self.check_position(unit, new_x, new_y + eps):
            return new_x, new_y + eps
        if not self.check_position(unit, new_x, new_y - eps):
            return new_x, new_y - eps

        # rien à faire → bloqué
        return unit.position

    def move_unit_on_map(self, unit: Any, new_x: float, new_y: float) -> bool:
        """
        Déplace une unit ciruculaire à (new_x, new_y) en float.
        - Vérifie les bordures de map.
        - test  collision cicrulaire.
        - sliding si necessaire.
        - soft collision pour eviter overlap circulaire.
        - Mets à jour la position flottante de l'unité.
        - Mets à jour les occupants des tiles (pour affichage/optimisation).
        """
        # --------- CHECK BORDURES  ----------
        if not self.in_map(new_x, new_y):
            return False

        # --------- CHECK COLLISION  ----------
        if self.check_position(unit, new_x, new_y):
            # tente sliding move
            new_x, new_y = self.attempt_sliding_move(unit, new_x, new_y)

        if (new_x, new_y) == unit.position:  # Si toujours bloqué, ne bouge pas
            return False

        # --- Mise à jour des tiles pour affichage ---
        self.remove_unit_from_old_tile(unit)
        unit.position = (new_x, new_y)  # source de vérité en float
        self.add_unit_to_tile(unit)

        # ---------- SOFT COLLISION  ----------
        self.resolve_soft_collisions(unit)

        return True

    # ------------- UTILS --------------
    def in_map(self, x: float, y: float) -> bool:
        """Test si (x, y) est dans la carte."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_all_units(self) -> List[Any]:
        """Renvoie une liste des unité du Battlefield."""
        return list(self.units.values())

    def units_by_owner(self, owner: int) -> List[Any]:
        """Renvoie une liste des unité du Battlefield appartenant au team owner."""
        return [u for u in self.units.values() if getattr(u, "owner", None) == owner]

    def find_unit(self, unit_id: int) -> Optional[Any]:
        """Renvoie l'unité ayant l'id unit_id."""
        return self.units.get(unit_id)

    def units_in_radius(self, x: float, y: float, radius: float) -> List[Any]:
        """Renvoie une liste des unité du Battlefield dans un rayon de radius autour de (x,y)."""
        result: List[Any] = []
        for u in self.get_all_units():
            ux, uy = u.position
            if ux is None:
                continue
            if hypot(ux - x, uy - y) <= float(radius):
                result.append(u)
        return result

    def is_battle_over(self) -> bool:
        """Renvoie True si la bataille est finie."""
        teams_alive = {u.owner for u in self.units.values() if getattr(u, "is_alive", lambda: False)()}
        return len(teams_alive) <= 1

    def snapshot(self) -> dict:
        """Renvoie un snapshot du Battlefield."""
        units_ser = []
        for u in self.units.values():
            units_ser.append(
                {
                    "id": u.id,
                    "type": u.name,
                    "owner": u.owner,
                    # "position": u.position,
                    "position": tuple(int(v * 100) / 100 for v in u.position),  # position arrondie
                    "hp": u.hp,
                    "hibtox": u.radius,
                }
            )
        return {"width": self.width, "height": self.height, "units": units_ser, "generals": [str(g) for g in self.generals], "tiles": len(self.game_map.tiles)}
