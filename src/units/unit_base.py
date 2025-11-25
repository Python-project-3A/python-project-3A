import math
import time
from src.engine.battlefield import Battlefield


class Unit:
    def __init__(self, name, team, x, y, height, width, hp, armor, damage, attack_range, attack_cooldown, speed):
        self.name = name
        self.team = team
        self.position = (float(x), float(y))
        self.height = height
        self.width = width
        self.hp = hp
        self.armor = armor
        self.damage = damage
        self.attack_range = attack_range
        self.attack_cooldown = attack_cooldown
        self.speed = speed
        self.cooldown_remaining = 0  # en ticks
        self.id = None
        self.battlefield = None

    def __repr__(self):
        return f"<Unit_minimal id={self.id} pos={self.position}>"

    def is_alive(self) -> bool:
        """return True si l'unité est encore en vie"""
        return self.hp > 0

    def take_damage(self, attack_damage):
        """-calcul les degats subis apres une attaque
        -les soustrais aux hp
        -indique si la troupe est encore en vie apres l'attaque"""

        take = max(0, attack_damage - self.armor)
        self.hp -= take
        if not self.is_alive():
            pass

    def to_dict(self):
        """
        retourne un dictionnaire qui associe chaque nom d'attribut à sa valeur actuelle
        peut être utile pour le save/load et la partie statistique plus tard
        """
        return {
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "width": self.width,
            "height": self.height,
            "hp": self.hp,
            "armor": self.armor,
            "damage": self.damage,
            "attack_range": self.attack_range,
            "attack_cooldown": self.attack_cooldown,
            "speed": self.speed,
        }

    def dist_to(self, other: "Unit") -> float:
        """
        calcule et retourne la distance entre les centres de deux unités
        """
        return math.dist((self.x, self.y), (other.x, other.y))

    def edge_dist_to(self, other: "Unit") -> float:
        """
        différent de dist_to, retourne la différence de la distance entre les centres de
        deux unités et la somme de leur rayons
        nécessaire pour déterminer si l'unité cible est dans l'attack range étant donné
        que ce dernier commence à partir du rayon de l'unité et non pas de son centre
        """
        center_dist = self.dist_to(other)
        self_radius = 0.5 * math.hypot(self.width, self.height)
        target_radius = 0.5 * math.hypot(other.width, other.height)
        return max(0.0, center_dist - (self_radius + target_radius))

    def move_towards(self, target: "Unit", bf: Battlefield):
        """Se déplace vers la cible d'au maximum 'speed' unités par tick."""
        edge_dist = self.edge_dist_to(target)

        # si déjà à portée → pas besoin d'avancer
        if self.can_attack(target):
            return False

        x, y = self.position
        tx, ty = target.position

        dx = tx - x
        dy = ty - y
        dist = math.hypot(dx, dy)

        if dist == 0:
            return False

        step = min(self.speed, edge_dist)

        new_x = x + dx / dist * step
        new_y = y + dy / dist * step

        return bf.move_unit_on_map(self, new_x, new_y)

    def move_to(self, px: float, py: float, bf: Battlefield):
        """Se déplace vers (px, py) d'au maximum 'speed' unités par tick."""
        x, y = self.position
        dx = px - x
        dy = py - y

        dist = math.hypot(dx, dy)
        if dist == 0:
            return False

        step = min(self.speed, dist)

        new_x = x + dx / dist * step
        new_y = y + dy / dist * step

        return bf.move_unit_on_map(self, new_x, new_y)

    def can_attack(self, other: "Unit") -> bool:
        """
        vérifie si les deux unités sont assez proches (selon attack range)
        pour que l'une des unité puisse attaquer (self)
        """
        if self.edge_dist_to(other) <= self.attack_range:
            return True
        else:
            return False

    def attack(self, other: "Unit") -> bool:
        """Attaque si le cooldown est fini."""
        if not self.can_attack(other):
            return False

        if self.cooldown_remaining > 0:
            return False

        # inflige les dégâts
        damage = max(0, self.damage - other.armor)
        other.hp = max(0, other.hp - damage)

        # réarme le cooldown
        self.cooldown_remaining = self.attack_cooldown

        return True

    def choose_target(self, enemies: list):
        living_enemies = [e for e in enemies if e.is_alive()]
        if not living_enemies:
            return None
        return min(living_enemies, key=lambda e: self.distance_to(e))

    def update(self, bf: Battlefield, tick: int):
        """Update logique de l'unité à chaque tick."""

        # si morte → suppression
        if not self.is_alive():
            bf.remove_unit(self.id)
            return

        # mettre à jour le cooldown
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1

        # exemple de déplacement automatique (à remplacer par de l'IA plus tard)
        x, y = self.position
        new_x = x + 0.1 * self.speed
        new_y = y
        bf.move_unit_on_map(self, new_x, new_y)
