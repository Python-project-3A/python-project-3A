import math
from typing import Literal, TypedDict


# L'unité reçoit maintenant un certain nombre d'instructions: 3 pour être précis
# soit "move_to" pour se déplacer à une position spécifique (un couple (x, y) de coordonnées)
# soit "attack_move" pour trouver l'ennemi le plus proche et l'attack
# soit "attack_unit" pour attaquer l'unit directement
class MoveToOrder(TypedDict):
    type: Literal["move_to"]
    target: tuple[float, float]


class AttackMoveOrder(TypedDict):
    type: Literal["attack_move"]
    target: tuple[float, float]


class AttackUnitOrder(TypedDict):
    type: Literal["attack_unit"]
    target: "Unit"


Order = MoveToOrder | AttackMoveOrder | AttackUnitOrder


# la classe unit est maintenant entièrement des données, elle n'effectue plus d'action comme se déplacer, ces actions sont gérées par un système externe
class Unit:
    def __init__(self, name: str, owner: int, x: float, y: float, r: float, hp: int, armor: int, damage: int, attack_range: float, attack_cooldown: float, speed: float, id: int = None):
        # identity and ownership
        self.id = id
        self.name = name
        self.owner = owner

        # Physical properties
        self.position = (float(x), float(y))
        self.radius = r

        # Combat stats
        self.hp = hp
        self.armor = armor
        self.damage = damage
        self.attack_range = attack_range
        self.attack_cooldown = attack_cooldown
        self.speed = speed

        # state
        self.time_since_last_attack = 0.0
        self.current_target: Unit | None = None
        self.current_order: Order | None = None

    def __repr__(self):
        return f"<Unit_minimal id={self.id} pos={self.position}>"

    # -------- BASICS --------

    def is_alive(self) -> bool:
        """return True si l'unité est encore en vie"""
        return self.hp > 0

    # Pure calculation methods (no side effects)
    def dist_to(self, other: "Unit") -> float:
        """
        calcule et retourne la distance entre les centres de deux unités
        """
        x, y = self.position
        ox, oy = other.position
        return math.dist((x, y), (ox, oy))

    def edge_dist_to(self, other: "Unit") -> float:
        """calcule et retourne la distance entre les hitbox de deux unités"""
        center_dist = self.dist_to(other)
        return center_dist - (self.radius + other.radius)

    def can_attack(self, other: "Unit") -> bool:
        """
        vérifie si les deux unités sont assez proches (selon attack range)
        pour que l'une des unité puisse attaquer (self)
        """
        return self.edge_dist_to(other) <= self.attack_range

    def to_dict(self):
        """
        retourne un dictionnaire qui associe chaque nom d'attribut à sa valeur actuelle
        utile pour le save/load et la partie statistique plus tard
        """
        return {
            "name": self.name,
            "owner": self.owner,
            "position": self.position,
            "radius": self.radius,
            "hp": self.hp,
            "armor": self.armor,
            "damage": self.damage,
            "attack_range": self.attack_range,
            "attack_cooldown": self.attack_cooldown,
            "speed": self.speed,
        }

    # helper method
    def dist_to_point(self, point: tuple[float, float]) -> float:
        """Distance from unit to a point"""
        x, y = self.position
        px, py = point
        return math.dist((x, y), (px, py))
