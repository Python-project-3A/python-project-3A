from __future__ import annotations

from typing import TYPE_CHECKING

from .general_base import BaseGeneral

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield


class GeneralBraindead(BaseGeneral):
    """
    Captain BRAINDEAD - The lobotomy victim.

    Strategy: PURE REACTIVE
    - Units don't move or seek combat
    - They ONLY attack if enemy is literally within attack range
    - This is the absolute minimum AI
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Captain BRAINDEAD")

    def update(self, battlefield: Battlefield, tick: int) -> None:
        """
        BRAINDEAD: Units only attack enemies that are RIGHT NEXT TO THEM.
        No movement, no chasing, purely reactive.
        """
        my_units = self.get_my_units(battlefield)

        for unit in my_units:
            if not unit.is_alive():
                continue

            # Look for enemies ONLY within attack range (no chasing)
            enemies_in_range = battlefield.units_in_radius(
                unit.position[0],
                unit.position[1],
                unit.attack_range + 0.1,  # Slight buffer for floating point
            )

            # Filter to actual enemies
            enemies_in_range = [e for e in enemies_in_range if e.owner != self.player_id and e.is_alive()]

            if enemies_in_range:
                # Enemy is right next to us - attack the nearest one
                nearest = min(enemies_in_range, key=lambda e: unit.dist_to(e))
                unit.current_order = {"type": "attack_unit", "target": nearest}
            else:
                # No enemies nearby - do nothing (idle)
                unit.current_order = None
