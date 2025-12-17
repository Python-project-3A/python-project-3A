from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


class BaseGeneral(ABC):
    """
    Base class for all generals (AI commanders).
    Each general controls units of one player/team.
    """

    def __init__(self, player_id: int, name: str = "General"):
        self.player_id = player_id  # 0 or 1
        self.name = name

    @abstractmethod
    def update(self, battlefield: Battlefield, tick: int) -> None:
        """
        Called every tick by the simulation.
        General analyzes the battlefield and gives orders to units.

        Args:
            battlefield: The battlefield state
            tick: Current tick number
        """
        pass

    def get_my_units(self, battlefield: Battlefield) -> list[Unit]:
        """Get all units belonging to this general"""
        return battlefield.units_by_owner(self.player_id)

    def get_enemy_units(self, battlefield: Battlefield) -> list[Unit]:
        """Get all enemy units"""
        all_units = battlefield.get_all_units()
        return [u for u in all_units if u.owner != self.player_id and u.is_alive()]

    def __repr__(self):
        return f"<{self.__class__.__name__} player={self.player_id} name={self.name}>"

    # --- MATHS VECTORS ---
    @staticmethod
    def get_dist(p1, p2):
        """Return distance between p1 and p2"""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    @staticmethod
    def normalize_vec(v):
        """Normalize vector v"""
        norm = math.hypot(v[0], v[1])
        if norm < 0.01:
            return (0, 0)
        return (v[0] / norm, v[1] / norm)

    @staticmethod
    def soustract_vec(v1, v2):
        """Soustract vector v2 from v1"""
        return (v1[0] - v2[0], v1[1] - v2[1])

    @staticmethod
    def add_vec(v1, v2):
        """Add vector v2 to v1"""
        return (v1[0] + v2[0], v1[1] + v2[1])

    @staticmethod
    def scale_vec(v, factor):
        """Return vector v scaled by factor"""
        return (v[0] * factor, v[1] * factor)

    @staticmethod
    def dot_product(v1, v2):
        """Return dot product of v1 and v2"""
        return v1[0] * v2[0] + v1[1] * v2[1]

    @staticmethod
    def _projection_vector(v1, v2, dist_proj):
        """Return vector v2 projected on v1 with length dist_proj"""
        projected_x = v1[0] + v2[0] * dist_proj
        projected_y = v1[1] + v2[1] * dist_proj
        return projected_x, projected_y

    @staticmethod
    def _clamp_position(v, bf: Battlefield):
        """Return v clamped inside battlefield"""
        clamp_x = max(0, min(v[0], bf.width - 0.01))
        clamp_y = max(0, min(v[1], bf.height - 0.01))
        return clamp_x, clamp_y

    #
    @staticmethod
    def _get_centroid(units: list[Unit]) -> tuple[float, float]:
        """Calcule le barycentre d'une liste d'unités."""
        if not units:
            return (0.0, 0.0)

        # Optimisation : On évite de faire 2 boucles sum() séparées
        count = len(units)
        sx = 0.0
        sy = 0.0
        for u in units:
            sx += u.position[0]
            sy += u.position[1]

        return (sx / count, sy / count)

    # --- PERCEPTION & ANALYSE (Lecture du jeu) ---

    def _analyze_enemy_clusters(self, enemies: list[Unit]):
        """
        Découpe les ennemis en groupes logiques (Clusters).
        Utile pour savoir si l'ennemi est séparé en deux armées.
        """
        # TODO: Implémenter un vrai K-Means ou DBSCAN si besoin plus tard.
        # Pour l'instant : Une seule grosse armée.
        if not enemies:
            return []

        return [{"center": self._get_centroid(enemies), "units": enemies, "count": len(enemies)}]

    # --- MOUVEMENT ---

    def _get_ennemis_repulsion_vector(self, unit, enemies: list["Unit"], threat_radius=10.0):
        """Calcule un vecteur de répulsion des ennemis. (Barycentre pondéré)"""
        threat_count = 0
        repulsion_x, repulsion_y = 0.0, 0.0
        for enemy in enemies:
            if not enemy.is_alive():
                continue

            dx, dy = self.soustract_vec(unit.position, enemy.position)
            dist_sq = dx * dx + dy * dy

            if dist_sq < threat_radius * threat_radius:  # répulsion inversement proportionnelle à la distance
                dist = math.sqrt(dist_sq)
                force = 1.0 / (dist + 0.1)  # +0.1 pour éviter division par zéro

                repulsion_x += (dx / dist) * force
                repulsion_y += (dy / dist) * force
                threat_count += 1
        return repulsion_x, repulsion_y

    def _get_wall_repulsion(self, unit, bf, margin=5.0):
        """Calcule un vecteur de répulsion des murs."""
        wall_margin = margin
        wall_repulsion_x, wall_repulsion_y = 0.0, 0.0

        # Mur Gauche (x=0) -> Pousse vers la droite (+x)
        if unit.position[0] < wall_margin:
            force = (wall_margin - unit.position[0]) / wall_margin
            wall_repulsion_x += force * 2.0  # *2.0 pour donner priorité à l'évitement du mur

        # Mur Droit (x=Width) -> Pousse vers la gauche (-x)
        if unit.position[0] > bf.width - wall_margin:
            force = (unit.position[0] - (bf.width - wall_margin)) / wall_margin
            wall_repulsion_x -= force * 2.0

        # Mur Haut (y=0) -> Pousse vers le bas (+y)
        if unit.position[1] < wall_margin:
            force = (wall_margin - unit.position[1]) / wall_margin
            wall_repulsion_y += force * 2.0

        # Mur Bas (y=Height) -> Pousse vers le haut (-y)
        if unit.position[1] > bf.height - wall_margin:
            force = (unit.position[1] - (bf.height - wall_margin)) / wall_margin
            wall_repulsion_y -= force * 2.0

        return wall_repulsion_x, wall_repulsion_y

    def _get_separation_vector(self, my_nearby_friends: list["Unit"], unit: "Unit") -> tuple[float, float]:
        """Calcule un vecteur de separation."""
        separation_x, separation_y = 0, 0
        separation_radius = 1.3  # Rayon très court (juste l'espace vital)

        for friend in my_nearby_friends:
            dist = unit.dist_to(friend)
            if dist < separation_radius and dist > 0:
                push = (separation_radius - dist) / separation_radius  # Force linéaire

                # Vecteur unit -> friend
                dx, dy = self.soustract_vec(unit.position, friend.position)

                # On ajoute une petite force répulsive
                separation_x -= (dx / dist) * push * 0.5  # Poids faible (0.5)
                separation_y -= (dy / dist) * push * 0.5
        return separation_x, separation_y

    # --- CIBLAGE ---

    def _filter_enemies(self, enemies, types: list[str] | None = None):
        """Renvoie les ennemis filtrés par type."""
        if not types:
            return []
        return [e for e in enemies if e.name.lower() in types and e.is_alive()]

    # --- COMPORTEMENTS GENERIQUES ---

    def _order_regroup(self, unit: Unit, bf: Battlefield):
        """
        Ordre de repli stratégique : L'unité rejoint le gros de l'armée.
        """
        my_army = [u for u in self.get_my_units(bf) if u.is_alive()]

        if not my_army:
            return

        sum_x = sum(u.position[0] for u in my_army)
        sum_y = sum(u.position[1] for u in my_army)
        count = len(my_army)

        center_x = sum_x / count
        center_y = sum_y / count

        # Optimisation, si on est déjà quasi collé on fait rien
        dist_sq = (unit.position[0] - center_x) ** 2 + (unit.position[1] - center_y) ** 2
        if dist_sq < 16.0:  # distance² (éviter les racines carrés innutiles)
            return

        unit.current_order = {"type": "attack_move", "target": (center_x, center_y)}  # attaque_move pour ne pas être passif sur le trajet

    def _fuite_strategique(self, unit: "Unit", enemies: list["Unit"], bf: "Battlefield"):
        """
        Calcule un vecteur de fuite basé sur la somme des répulsions.
        Prend en compte : Les ennemis proches, les murs.
        """
        # Vecteur de mouvement (x, y)
        move_x, move_y = 0.0, 0.0

        # RÉPULSION DES ENNEMIS
        repulsion_x, repulsion_y = self._get_ennemis_repulsion_vector(unit, enemies, 10.0)
        move_x += repulsion_x
        move_y += repulsion_y

        # RÉPULSION DES MURS
        wall_repulsion_x, wall_repulsion_y = self._get_wall_repulsion(unit, bf, 5.0)
        move_x += wall_repulsion_x
        move_y += wall_repulsion_y

        # NORMALISATION & APPLICATION
        nmove_x, nmove_y = self.normalize_vec((move_x, move_y))
        if (nmove_x, nmove_y) == (0.0, 0.0):
            return

        target_x, target_y = self._projection_vector(unit.position, (nmove_x, nmove_y), 6.0)

        # Clamp final de sécurité
        clamp_x, clamp_y = self._clamp_position((target_x, target_y), bf)

        unit.current_order = {"type": "move_to", "target": (clamp_x, clamp_y)}

    def _order_attack_opti(self, unit: Unit, target: Unit) -> None:
        """
        Donne l'ordre d'attaquer une cible spécifique.
        Optimisation : Ne réinitialise pas l'ordre s'il est déjà actif (évite le spam).
        """
        # Vérification anti-spam
        if unit.current_order and unit.current_order["type"] == "attack_unit" and unit.current_order["target"] == target:
            return

        # Application de l'ordre
        unit.current_order = {"type": "attack_unit", "target": target}

    def to_dict(self):
        """
        retourne un dictionnaire qui associe chaque nom d'attribut à sa valeur actuelle
        utile pour le save/load
        """
        data = {"class": self.__class__.__name__, "player_id": self.player_id, "name": self.name}
        return data
