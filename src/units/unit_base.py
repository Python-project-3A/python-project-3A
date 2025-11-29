import math
import time
from src.engine.battlefield import Battlefield


class Unit:
    def __init__(self, name, team, x, y, r, hp, armor, damage, attack_range, attack_cooldown, speed):
        self.name = name
        self.team = team

        self.position = (float(x), float(y))
        self.radius = float(r)  # hitbox ronde des unites

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

    # -------- BASICS --------

    def is_alive(self) -> bool:
        """return True si l'unité est encore en vie"""
        return self.hp > 0

    def take_damage(self, attack_damage):
        """-calcul les degats subis apres une attaque et les soustrais aux hp"""
        if not self.is_alive():
            pass
        take = max(0, attack_damage - self.armor)
        self.hp -= take

    def to_dict(self):
        """
        retourne un dictionnaire qui associe chaque nom d'attribut à sa valeur actuelle
        peut être utile pour le save/load et la partie statistique plus tard
        """
        return {
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "hitbox": self.radius,
            "hp": self.hp,
            "armor": self.armor,
            "damage": self.damage,
            "attack_range": self.attack_range,
            "attack_cooldown": self.attack_cooldown,
            "speed": self.speed,
        }

    # ------ DISTANCES -------

    def dist_to(self, other: "Unit") -> float:
        """
        calcule et retourne la distance entre les centres de deux unités
        """
        return math.dist(self.position, other.position)

    def edge_dist_to(self, other: "Unit") -> float:
        """calcule et retourne la distance entre les hitbox de deux unités"""
        center_dist = self.dist_to(other)
        return center_dist - (self.radius + other.radius)

    # ------ COLLSIONS ------

    def collision(self, other):  # deux unités ne doivent pas avoir leurs centres trop proches
        """retourne True si deux unité sont en collision"""
        return self.dist_to(other) < self.radius + other.radius

    def collides_with_position(self, other, x, y):
        """Vérifie si 'unit' placée à (px, py) entrerait en collision avec 'other'."""
        ox, oy = other.position
        dx = x - ox
        dy = y - oy
        return math.hypot(dx, dy) < (self.radius + other.radius)

    def soft_push(self, other, push_strength=0.5):
        """Applique un 'soft push' entre deux unités si elles overlappent."""
        ox, oy = other.position
        sx, sy = self.position

        # vecteur entre les centres
        dx = sx - ox
        dy = sy - oy
        dist = math.hypot(dx, dy)

        min_dist = self.radius + other.radius  # distance à respecter

        if dist >= min_dist or dist == 0:
            return  # rien à faire, elles ne se chevauchent pas

        # quantité d'overlap (chevauchement des hitbox)
        overlap = min_dist - dist

        # vecteur orthogonal exact
        # normal au vecteur distance (dx,dy) => (dy, -dx)
        ortho_x = dy
        ortho_y = -dx

        ortho_len = math.hypot(ortho_x, ortho_y)
        if ortho_len == 0:
            return

        # normalisation
        ortho_x /= ortho_len
        ortho_y /= ortho_len

        # déplacement proportionnel au recouvrement
        push_x = ortho_x * overlap * push_strength  # entre 0.2 et 0.5
        push_y = ortho_y * overlap * push_strength

        # appliquer la correction
        self.position = (sx + push_x, sy + push_y)

    def move_towards(self, target: "Unit", bf: Battlefield):
        """Se déplace vers la cible d'au maximum 'speed' unités par tick."""

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

        # distance dont on peut encore s'approcher sans toucher la hitbox de target
        edge_dist = self.edge_dist_to(target)
        step = min(self.speed, edge_dist)
        if step <= 0:
            return False

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

    # ------ ATTACKS ------

    def can_attack(self, other: "Unit") -> bool:
        """Peut attaquer si distance (bord à bord) <= attack range."""
        return self.edge_dist_to(other) <= self.attack_range

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

    # ------ UPDATE ------

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
