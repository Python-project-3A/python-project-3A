from __future__ import annotations

from src.engine.battlefield import Battlefield
from src.engine.system import CombatSystem

from .general_base import BaseGeneral


class GeneralDaft(BaseGeneral):
    """
    Major DAFT - Dumb as fuck.

    Strategy: ATTACK NEAREST ENEMY
    - Every unit attacks the nearest enemy
    - No formations
    - No tactics
    - No counter-type considerations
    - Pure mindless aggression
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Major DAFT")

    def update(self, bf: "Battlefield", tick: int) -> None:
        """
        DAFT: Agressivité totale.
        - Utilise la vision globale du Général.
        - Chasse l'ennemi le plus proche sur toute la carte.
        """
        my_units = self.get_my_units(bf)
        enemies = self.get_enemy_units(bf)

        if not enemies:
            return

        for unit in my_units:
            if not unit.is_alive():
                continue

            current_order = unit.current_order
            if current_order and current_order["type"] == "attack_unit" and current_order["target"].is_alive() and unit.dist_to(current_order["target"]) < 10.0:  # Garde le focus si < 10m
                continue

            target = CombatSystem.choose_nearest_target(unit, enemies, bf)

            # 2. Ordre
            if target:
                self._order_attack_opti(unit, target)
            else:
                self._order_regroup(unit, bf)
