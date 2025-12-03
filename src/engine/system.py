import math

# import time # NE JAMAIS UTILISER TIME DANS CE FICHIER !!! PAS COMPATIBLE AVEC LE MODE SANS VISUEL (TICKS ACCELERES)
import heapq
from typing import List, Tuple, Optional

from src.engine.battlefield import Battlefield

from ..units.unit_base import Unit


MOVE_COST_STRAIGHT = 10
MOVE_COST_DIAGONAL = 14


class PathFinding:
    """
    Gère le calcul de chemin (A*) sur la grille, mais pour des unités fluides.
    """

    @staticmethod
    def get_neighbors(node: Tuple[int, int], battlefield: "Battlefield") -> List[Tuple[Tuple[int, int], int]]:
        """
        Retourne les voisins valides et leur coût de mouvement.
        Gère les 8 directions (Diagonales incluses).
        """
        neighbors = []
        x, y = node
        width, height = battlefield.width, battlefield.height
        game_map = battlefield.game_map

        # Directions: (dx, dy, cost)
        # On privilégie les entiers pour A*
        directions = [
            (0, 1, MOVE_COST_STRAIGHT),
            (0, -1, MOVE_COST_STRAIGHT),
            (1, 0, MOVE_COST_STRAIGHT),
            (-1, 0, MOVE_COST_STRAIGHT),
            (1, 1, MOVE_COST_DIAGONAL),
            (1, -1, MOVE_COST_DIAGONAL),
            (-1, 1, MOVE_COST_DIAGONAL),
            (-1, -1, MOVE_COST_DIAGONAL),
        ]

        for dx, dy, cost in directions:
            nx, ny = x + dx, y + dy

            # 1. Vérification des limites de la carte
            if 0 <= nx < width and 0 <= ny < height:
                # 2. Vérification des obstacles (Murs, Bâtiments, Eau)
                # On accède à la tuile via game_map (supposons qu'elle a une méthode ou attr pour ça)
                # Note: Dans votre code actuel, game_map.get_tile peut retourner None ou une Tile
                tile = game_map.get_tile(nx, ny)

                # Si la tuile existe et n'est pas un obstacle (à implémenter dans Tile/GameMap)
                # Pour l'instant on suppose que tout est walkable sauf si défini autrement
                is_walkable = True
                if tile and hasattr(tile, "is_obstacle") and tile.is_obstacle:
                    is_walkable = False

                if is_walkable:
                    neighbors.append(((nx, ny), cost))

        return neighbors

    @staticmethod
    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        """
        Distance octile
        """
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return MOVE_COST_STRAIGHT * (dx + dy) + (MOVE_COST_DIAGONAL - 2 * MOVE_COST_STRAIGHT) * min(dx, dy)

    @staticmethod
    def search(start_pos: Tuple[float, float], end_pos: Tuple[float, float], battlefield: "Battlefield") -> List[Tuple[float, float]]:
        """
        Exécute l'algo A*.
        Prend des coordonnées flottantes (Unit pos), les convertit en grille, calcule le chemin,
        et retourne une liste de waypoints (centres des tuiles) en float.
        """
        # Conversion Float -> Grille
        start_node = (int(start_pos[0]), int(start_pos[1]))
        end_node = (int(end_pos[0]), int(end_pos[1]))

        # Si départ == arrivée (même tuile), on retourne juste le point final précis
        if start_node == end_node:
            return [end_pos]

        # Init A*
        open_set = []
        heapq.heappush(open_set, (0, start_node))
        came_from = {}
        g_score = {start_node: 0}

        # Optimisation : limite de recherche pour éviter de geler le jeu si pas de chemin
        iterations = 0
        max_iterations = 2000

        while open_set:
            iterations += 1
            if iterations > max_iterations:
                break  # Abandon si trop long

            current = heapq.heappop(open_set)[1]

            if current == end_node:
                # Reconstruction du chemin
                path = []
                while current in came_from:
                    # On ajoute le CENTRE de la tuile pour le mouvement fluide
                    path.append((current[0] + 0.5, current[1] + 0.5))
                    current = came_from[current]
                # On inverse pour avoir le chemin du début
                path.reverse()
                # On remplace le dernier point (centre de la case) par la vraie cible exacte
                if path:
                    path[-1] = end_pos
                return path

            for neighbor, cost in PathFinding.get_neighbors(current, battlefield):
                tentative_g_score = g_score[current] + cost

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score = tentative_g_score + PathFinding.heuristic(neighbor, end_node)
                    heapq.heappush(open_set, (f_score, neighbor))

        # Si échec, on tente d'aller tout droit (fallback)
        return [end_pos]


class MovementSystem:
    """Handles all unit movement logic"""

    @staticmethod
    def move_towards(unit: "Unit", target: "Unit", dt: float, battlefield: "Battlefield") -> bool:
        """
        déplace l'unité vers l'unité cible, s'arrête dès qu'elle est à portée d'attaque.
        dépend de la vitesse de notre unité et du temps passé : dt (secondes par tick)
        """
        # vérifications
        if unit.can_attack(target):
            return False

        if unit.speed <= 0 or dt <= 0:
            return False

        # calcul de la distance centre à centre
        dist_center = unit.dist_to(target)

        if dist_center < 0.001:
            return False

        # calcul de la distance qu'il reste à parcourir soit <= attack range
        current_edge_dist = unit.edge_dist_to(target)
        dist_needed = max(0, current_edge_dist - (unit.attack_range * 0.9))  # la multiplcation par 0.9 c'est pour être à 90% de la portée max pour être sûr d'être à porté d'attaque et pas à la limite

        # calcul du pas de mouvement, min entre ce qu'on peut faire et ce qu'on doit faire
        step = min(unit.speed * dt, dist_needed)

        # application du Vecteur Normalisé
        tx, ty = target.position
        ux, uy = unit.position
        dx = tx - ux
        dy = ty - uy

        # ratio soit le pourcentage du chemin total qu'on parcourt ce tick-ci
        ratio = step / dist_center

        new_x = ux + (dx * ratio)
        new_y = uy + (dy * ratio)

        return battlefield.move_unit_on_map(unit, new_x, new_y)

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

        if attacker.reload_timer > 0:
            return False

        # Check if in range
        if not attacker.can_attack(defender):
            return False

        # Apply damage
        damage = max(0, attacker.damage - defender.armor)
        defender.hp = max(0, defender.hp - damage)  # pour ne pas avoir d'hp < 0

        # reset du timer avec la valeur du cooldown
        attacker.reload_timer = attacker.attack_cooldown

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
        Filter enemies to only those within the unit's vision range

        Args:
            unit: The unit checking range (to use its vision_range)
            enemies: List of potential enemies

        Returns:
            List of enemies that are currently visible/detectable by the unit.
        """
        return [
            e for e in enemies 
            if e.is_alive() and unit.dist_to(e) <= unit.vision_range
        ]

class UnitController:
    """Main controller that coordinates unit behavior"""

    @staticmethod
    def _follow_path(unit: "Unit", target_pos: tuple[float, float], order: dict, battlefield: "Battlefield", dt: float):
        """
        Logique partagée pour suivre un chemin A*.
        Gère le calcul initial et le déplacement waypoint par waypoint.
        """
        # calcul du chemin si nécessaire
        if "path" not in order:
            # si très proche (< 2 tuiles), ligne droite directe
            if unit.dist_to_point(target_pos) < 2.0:
                order["path"] = [target_pos]
            else:
                order["path"] = PathFinding.search(unit.position, target_pos, battlefield)

        path = order["path"]

        # suivi du chemin
        if path:
            next_waypoint = path[0]

            # utilise move_to_position pour aller vers le waypoint
            MovementSystem.move_to_position(unit, next_waypoint[0], next_waypoint[1], dt, battlefield)

            # Si on est arrivé au waypoint (seuil 0.2 tuile)
            if unit.dist_to_point(next_waypoint) < 0.2:
                path.pop(0)  # Waypoint atteint, on passe au suivant

        # 3. Fin de parcours
        if not path:
            # On est arrivé au bout
            return True  # Reached
        return False  # Not reached yet

    @staticmethod
    def update(unit: "Unit", battlefield: "Battlefield", dt: float):  # noqa: C901
        """Update unit behavior based on its current order"""
        if not unit.is_alive():
            battlefield.remove_unit(unit.id)
            return

        if not unit.current_order:
            return

        order = unit.current_order

        # --- GESTION DU TEMPS DE RECHARGEMENT ---
        if unit.reload_timer > 0:
            unit.reload_timer -= dt  # On décrémente selon le temps du JEU, pas le temps RÉEL

        # --- EXECUTION DES ORDRES ---
        if order["type"] == "move_to":
            reached = UnitController._follow_path(unit, order["target"], order, battlefield, dt)
            if reached:
                unit.current_order = None

        # ---------------------------------------------------------
        # GESTION ATTACK MOVE (Avancer, taper si ennemi, sinon avancer)
        # ---------------------------------------------------------
        elif order["type"] == "attack_move":
            target_pos = order["target"]

            # Recherche d'ennemis
            enemies_around = [u for u in battlefield.units_in_radius(unit.position[0], unit.position[1], unit.vision_range) if u.owner != unit.owner and u.is_alive()]
            target = None
            if enemies_around:
                # Trouve le plus proche
                target = min(enemies_around, key=lambda e: unit.dist_to(e))

            # Optimisation: ne chercher la cible la plus proche que si on en a (eviter O(N^2) inutile)
            # enemies = [u for u in battlefield.get_all_units() if u.owner != unit.owner and u.is_alive()]
            # if enemies:
            # On ne regarde que ceux dans vision_range
            # visible_enemies = [e for e in enemies if unit.dist_to(e) < unit.vision_range]
            # if visible_enemies:
            # target = min(visible_enemies, key=lambda e: unit.dist_to(e))

            if target:
                if unit.can_attack(target):
                    CombatSystem.attack(unit, target)
                else:
                    # Si on chasse une unité, on utilise move_towards (pas de A* dynamique pour l'instant)
                    MovementSystem.move_towards(unit, target, dt, battlefield)
            else:
                # Pas d'ennemi : on continue le mouvement prévu (A*)
                reached = UnitController._follow_path(unit, order["target"], order, battlefield, dt)
                if reached:
                    unit.current_order = None

        # ---------------------------------------------------------
        # GESTION ATTACK UNIT (Ciblage direct)
        # ---------------------------------------------------------
        elif order["type"] == "attack_unit":
            target = order["target"]
            if target and target.is_alive():
                if unit.can_attack(target):
                    CombatSystem.attack(unit, target)
                else:
                    MovementSystem.move_towards(unit, target, dt, battlefield)  # Pour suivre une unité mobile, on utilise move_towards (ligne droite)
            else:
                unit.current_order = None
        elif order["type"] == "pathing_attack_unit":
            target = order["target"]
            if target and target.is_alive():
                if unit.can_attack(target):
                    CombatSystem.attack(unit, target)
                    
                    # Clear path data after engaging
                    if "path" in order:
                        order["path"] = []
                    if "path_target_pos" in order:
                        del order["path_target_pos"]
                else:
                    target_pos = target.position
                    
                    # --- DYNAMIC PATH RECALCULATION CHECK (1.0 tile threshold) ---
                    path_is_stale = (
                        "path" in order and 
                        "path_target_pos" in order and 
                        unit.dist_to_point(order["path_target_pos"]) > 1.0
                    )
                    
                    if path_is_stale:
                        order["path"] = []
                        del order["path_target_pos"]
                        
                    # Execute pathfinding movement
                    UnitController._follow_path(unit, target_pos, order, battlefield, dt)

                    # Store the position for next tick's staleness check
                    if "path" in order and order["path"]:
                        order["path_target_pos"] = target_pos
            else:
                unit.current_order = None # Target is dead/gone, clear order.