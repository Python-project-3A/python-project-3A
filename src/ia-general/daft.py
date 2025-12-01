from __future__ import annotations
from typing import Any
# Importer BaseGeneral de son emplacement relatif
from .base_general import BaseGeneral

class MajorDAFT(BaseGeneral):
    """
    Major DAFT : Le général qui attaque l'ennemi le plus proche sans stratégie.
    Les unités cherchent activement une cible, à la différence de Cpt.BRAINDEAD.
    """

    def __init__(self, id: int):
        # Initialise avec sa propre stratégie
        super().__init__(id, "daft")

    def decide_orders(self, battlefield: Any) -> None:
        """
        Pour chaque unité alliée, trouve l'ennemi le plus proche
        et ordonne l'attaque immédiate.
        """
        for unit in self.get_my_units(battlefield):
            if not getattr(unit, "is_alive", lambda: False)():
                continue # Ignore les unités mortes
            
            # 1. Trouver l'ennemi le plus proche
            target_enemy = self.get_nearest_enemy(unit, battlefield)

            # 2. Donner l'ordre
            if target_enemy:
                # Ordonne l'attaque. L'unité s'approchera si nécessaire.
                self.order_attack(unit, target_enemy)
            else:
                # Si aucun ennemi n'est trouvé, l'unité reste inactive.
                self.order_idle(unit)