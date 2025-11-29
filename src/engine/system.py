import math
import time

from src.engine.battlefield import Battlefield

from ..units.unit_base import Unit


class MovementSystem:
    """Handles all unit movement logic"""

    @staticmethod
    def move_towards(unit: "Unit", target: "Unit", dt: float, battlefield: "Battlefield") -> bool:
        """
        déplace l'unité d'un pas vers l'unité cible
        dépend de la vitesse de notre unité et du temps passé (dt)
        dt: secondes par tick
        déplace l'unité seulement si l'unité cible est déjà assez proche pour attaquer
        OU la vitesse de l'unité est supérieure à 0
        OU dt > 0
        """
        edge_dist = unit.edge_dist_to(target)

        if not unit.can_attack(target) and unit.speed > 0 and dt > 0:
            dist = unit.dist_to(target)
            if dist == 0:
                return False

            step = min(unit.speed * dt, edge_dist)

            target_x, target_y = target.position
            x, y = unit.position
            dx = target_x - x
            dy = target_y - y

            new_x = x + (dx / dist * step)
            new_y = y + (dy / dist * step)

            return battlefield.move_unit_on_map(unit, new_x, new_y)

        return False

    @staticmethod
    def move_to_position(unit: "Unit", target_x: float, target_y: float, dt: float, battlefield: "Battlefield") -> bool:
        """
        déplace l'unité d'un pas vers une position (x, y)
        mêmes spécifications que move_towards
        """

        x, y = unit.position
        dist = math.dist((x, y), (target_x, target_y))

        if dist == 0 or unit.speed == 0 or dt == 0:
            return False

        step = min(unit.speed * dt, dist)
        dx = target_x - x
        dy = target_y - y
        new_x = x + (dx / dist * step)
        new_y = y + (dy / dist * step)

        return battlefield.move_unit_on_map(unit, new_x, new_y)


class CombatSystem:
    """Handles all combat logic"""

    @staticmethod
    def attack(attacker: "Unit", defender: "Unit") -> bool:
        """
        Attaque une unité si elle est à portée et que le cooldown est terminé.
        Modifie la vie de la cible et met à jour le temps de la dernière attaque.
        """

        current_time = time.time()

        # Check if in range
        if not attacker.can_attack(defender):
            return False

        # Check cooldown
        if current_time - attacker.time_since_last_attack < attacker.attack_cooldown:
            return False

        # Apply damage
        damage = max(0, attacker.damage - defender.armor)
        defender.hp -= damage
        defender.hp = max(0, defender.hp)  # pour ne pas avoir d'hp < 0

        # Update attacker state
        attacker.time_since_last_attack = current_time

        return True

    @staticmethod
    def choose_nearest_target(unit: "Unit", enemies: list["Unit"]) -> "Unit | None":
        """Choose nearest living enemy"""
        living_enemies = [e for e in enemies if e.is_alive()]

        if not living_enemies:
            return None

        return min(living_enemies, key=lambda e: unit.dist_to(e))

    @staticmethod
    def choose_weakest_target(unit: "Unit", enemies: list["Unit"]) -> "Unit | None":
        """
        Choose the weakest (lowest HP) living enemy.
        Useful for focus-fire strategies (for other generals than braindead and daft)
        """
        living_enemies = [e for e in enemies if e.is_alive()]
        
        if not living_enemies:
            return None
        
        return min(living_enemies, key=lambda e: e.hp)
    
    @staticmethod
    def get_enemies_in_range(unit: "Unit", enemies: list["Unit"]) -> list["Unit"]:
        """
        Filter enemies to only those within attack range.
        
        Args:
            unit: The unit checking range
            enemies: List of potential enemies
        
        Returns:
            List of enemies that can be attacked right now
        """
        return [e for e in enemies if e.is_alive() and unit.can_attack(e)]
class UnitController:
    """Main controller that coordinates unit behavior"""

    @staticmethod
    def update(unit: "Unit", battlefield: "Battlefield", dt: float):  # noqa: C901
        """Update unit behavior based on its current order"""
        if not unit.is_alive():
            battlefield.remove_unit(unit.id)
            return

        # If unit has no order, idle
        if not unit.current_order:
            return

        order = unit.current_order

        if order["type"] == "move_to":
            target_pos = order["target"]
            target_pos_x, target_pos_y = target_pos
            reached = MovementSystem.move_to_position(unit, target_pos_x, target_pos_y, dt, battlefield)

            # Clear order if reached
            if reached and unit.dist_to_point(target_pos) < 0.5:
                unit.current_order = None

        elif order["type"] == "attack_move":
            # Move to destination, attacking enemies on the way
            target_pos = order["target"]
            # First, look for enemies
            enemies = [u for u in battlefield.get_all_units() if u.owner != unit.owner and u.is_alive()]

            if enemies:
                target = min(enemies, key=lambda e: unit.dist_to(e))
                if target:
                    # Try to attack if in range
                    if unit.can_attack(target):
                        CombatSystem.attack(unit, target)
                    else:
                        # Move towards target
                        MovementSystem.move_towards(unit, target, dt, battlefield)
            else:
                # No enemies, continue to destination
                if target_pos:
                    reached = MovementSystem.move_to_position(unit, target_pos[0], target_pos[1], dt, battlefield)
                    # Clear order if reached
                    if reached and unit.dist_to_point(target_pos) < 0.5:
                        unit.current_order = None

        elif order["type"] == "attack_unit":
            target = order["target"]
            if target and target.is_alive():
                if unit.can_attack(target):
                    CombatSystem.attack(unit, target)
                else:
                    MovementSystem.move_towards(unit, target, dt, battlefield)
            else:
                # Target died, clear order
                unit.current_order = None
