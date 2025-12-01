from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
import logging
from math import hypot

# L'importation de Battlefield est implicite dans le type hinting,
# mais on peut l'importer pour les vérifications de type si besoin
# from src.engine.battlefield import Battlefield 
# Note : Pour éviter une dépendance cyclique, on utilise 'Any' ou on importe si nécessaire.

logger = logging.getLogger(__name__)

class BaseGeneral:
    """
    Classe de base pour un "général" IA.

    Fournit :
    - update(battlefield, tick) : appelée chaque tick (méthode principale)
    - decide_orders(battlefield) : méthode à surcharger pour la stratégie
    - helpers : get_my_units, get_enemy_units, get_nearest_enemy, etc.
    - order_... : méthodes pour assigner des ordres aux unités (order_move, order_attack, ...)

    L'unité doit implémenter unit.set_order(order).
    """

    # Paramètres par défaut qui peuvent être surchargés par les sous-classes
    DEFAULT_PARAMS = {
        "group_radius": 5.0,  # Rayon de regroupement / formation (en tiles)
        "retreat_hp_ratio": 0.25, # Si hp faction < 25% => retreat
    }

    def __init__(self, id: int, strategy: str = "default"):
        """
        Initialisation du Général.
        :param id: ID du joueur (0 ou 1)
        :param strategy: Nom de la stratégie (ex: "aggressive")
        """
        self.id = id
        self.strategy = strategy
        self.memory: Dict[str, Any] = {}  # Mémoire persistante entre ticks
        self.params = self.DEFAULT_PARAMS.copy() 
        logger.info("BaseGeneral %s created (strategy=%s, id=%s)", self.__class__.__name__, strategy, id)

    # ----------------------------------------------------
    # Interface Publique (Méthodes principales du Général)
    # ----------------------------------------------------

    def update(self, battlefield: Any, tick: int) -> None:
        """
        Appelée chaque tick par Simulation. Point d'entrée pour la prise de décision.
        Doit être surchargée par l'IA concrète si des actions avant decide_orders sont nécessaires.
        """
        self.decide_orders(battlefield)
    
    def decide_orders(self, battlefield: Any) -> None:
        """
        Organise la stratégie globale et donne des ordres.
        C'est le cœur de l'IA. Doit être surchargée par chaque Général concret.
        """
        raise NotImplementedError("decide_orders doit être implémentée par la classe fille.")

    # Compatibilité : certaines IA utilisent `decide(game_state)` (ex: braindead.py)
    def decide(self, game_state: Any) -> Any:
        """
        Alias vers decide_orders pour compatibilité avec d'autres implémentations.
        """
        return self.decide_orders(game_state)

    # ----------------------------------------------------
    # Helpers : Sélection d'unités et informations
    # ----------------------------------------------------

    def get_my_units(self, battlefield: Any) -> List[Any]:
        """
        Renvoie la liste des unités appartenant à ce général (self.id).
        Utilise la méthode units_by_owner de Battlefield.
        """
        # Le général prend le commandement de son armée.
        return battlefield.units_by_owner(self.id)

    def get_enemy_units(self, battlefield: Any) -> List[Any]:
        """
        Renvoie la liste des unités ennemies. (Projet à 2 joueurs seulement)
        """
        # Assumant que les IDs des joueurs sont 0 et 1 (convention commune)
        enemy_id = 1 if self.id == 0 else 0
        return battlefield.units_by_owner(enemy_id)

    def get_nearest_enemy(self, unit: Any, battlefield: Any) -> Optional[Any]:
        """
        Trouve l'unité ennemie la plus proche d'une unité donnée.
        """
        my_x, my_y = unit.position
        nearest_enemy = None
        min_dist = float('inf')

        for enemy in self.get_enemy_units(battlefield):
            if not getattr(enemy, "is_alive", lambda: False)():
                continue
            
            # Assurez-vous que l'ennemi a une position
            enemy_pos = getattr(enemy, "position", None)
            if enemy_pos is None:
                continue

            enemy_x, enemy_y = enemy_pos
            dist = hypot(my_x - enemy_x, my_y - enemy_y)

            if dist < min_dist:
                min_dist = dist
                nearest_enemy = enemy
        
        return nearest_enemy

    def get_low_hp_units(self, battlefield: Any) -> List[Any]:
        """
        Renvoie les unités alliées avec des PV faibles (ex: < 25% HP).
        """
        low_hp_units = []
        # Utilise le ratio de retrait défini dans les paramètres du général
        retreat_ratio = self.params.get("retreat_hp_ratio", 0.25)
        
        for unit in self.get_my_units(battlefield):
            hp = getattr(unit, "hp", float('inf'))
            max_hp = getattr(unit, "max_hp", float('inf'))
            
            if hp != float('inf') and max_hp != float('inf') and hp / max_hp < retreat_ratio:
                low_hp_units.append(unit)
        
        return low_hp_units


    def group_units_by_type(self, battlefield: Any) -> Dict[str, List[Any]]:
        """
        Regroupe les unités alliées par type (Knight, Pikeman, Crossbowman, etc.).
        """
        groups: Dict[str, List[Any]] = {}
        for unit in self.get_my_units(battlefield):
            # Tente de récupérer le type/classe de l'unité
            unit_type = getattr(unit, "type", getattr(unit, "__class__", type(unit)).__name__)
            if unit_type not in groups:
                groups[unit_type] = []
            groups[unit_type].append(unit)
        return groups

    # ----------------------------------------------------
    # Ordres : Assignation des commandes aux unités
    # ----------------------------------------------------

    def order_move(self, unit: Any, x: float, y: float) -> None:
        """
        Ordonne à une unité de se déplacer vers la position (x, y).
        """
        order = {"type": "move", "target_pos": (x, y), "priority": 10}
        # unit.set_order doit être implémenté par la classe Unit
        unit.set_order(order)
        # logger.debug("Unit %s ordered to move to (%.2f,%.2f)", getattr(unit, "id", None), x, y)
    
    def order_attack(self, unit: Any, enemy: Any) -> None:
        """
        Ordonne à une unité d'attaquer une unité ennemie spécifique.
        """
        order = {"type": "attack", "target_unit_id": getattr(enemy, "id", None), "priority": 20}
        unit.set_order(order)
        # logger.debug("Unit %s ordered to attack unit %s", getattr(unit, "id", None), getattr(enemy, "id", None))

    def order_retreat(self, unit: Any, to_x: float, to_y: float) -> None:
        """
        Ordonne à une unité de battre en retraite vers la position (to_x, to_y).
        """
        order = {"type": "retreat", "target_pos": (to_x, to_y), "priority": 30}
        unit.set_order(order)
        # logger.debug("Unit %s ordered to retreat to (%.2f,%.2f)", getattr(unit, "id", None), to_x, to_y)

    def order_idle(self, unit: Any) -> None:
        """
        Ordonne à une unité de rester inactive (par défaut : se défendre si attaquée).
        """
        order = {"type": "idle", "priority": 5}
        unit.set_order(order)
        # logger.debug("Unit %s ordered to idle", getattr(unit, "id", None))