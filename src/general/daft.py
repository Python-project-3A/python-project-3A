from __future__ import annotations

from src.engine.battlefield import Battlefield
from src.engine.system import CombatSystem

from .general_base import BaseGeneral


class GeneralDaft(BaseGeneral):
    """
    Major DAFT - Dumb as a rock.

    Strategy: ATTACK NEAREST ENEMY
    - Every unit attacks the nearest enemy
    - No formations
    - No tactics
    - No counter-type considerations
    - Pure mindless aggression

    This is slightly better than BRAINDEAD because units
    actively seek and chase enemies.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Major DAFT")

    def update(self, battlefield: Battlefield, tick: int) -> None:
        """
        Simple strategy: every unit attacks the nearest enemy.
        """
        my_units = self.get_my_units(battlefield)
        enemies = self.get_enemy_units(battlefield)

        if not enemies:
            # No enemies left, we won!
            return

        for unit in my_units:
            if not unit.is_alive():
                continue

            # Find nearest enemy to THIS unit
            target = CombatSystem.choose_nearest_target(unit, enemies)

            if target:
                unit.current_order = {"type": "attack_unit", "target": target}
