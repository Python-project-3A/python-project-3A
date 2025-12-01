from __future__ import annotations
from typing import Any
# Importer BaseGeneral de son emplacement relatif
from .base_general import BaseGeneral

class CaptainBRAINDEAD(BaseGeneral):
    """
    Captain BRAINDEAD : Le général incapable de donner des ordres offensifs.
    Il ordonne à chaque unité de rester inactive, laissant leur comportement
    par défaut (riposte ou "idle") faire le seul travail.
    """

    def __init__(self, id: int):
        # Initialise avec sa propre stratégie
        super().__init__(id, "braindead")

    def decide_orders(self, battlefield: Any) -> None:
        """
        Ne donne aucun ordre actif de mouvement ou d'attaque.
        Ordonne simplement à toutes les unités de rester inactives.
        """
        for unit in self.get_my_units(battlefield):
            if not getattr(unit, "is_alive", lambda: False)():
                continue
            
            # Ordonne l'état IDLE.
            self.order_idle(unit)
        # Note : Si l'unité a un comportement par défaut de riposte, elle se défendra si attaquée.