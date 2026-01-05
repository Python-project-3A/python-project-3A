from __future__ import annotations

from typing import TYPE_CHECKING

from src.engine.system import CombatSystem

from .general_base import BaseGeneral

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield


class GeneralBraindead(BaseGeneral):
    """
    Captain BRAINDEAD - Pure Reactive Aggression.

    Strategy: ATTACK VISIBLE ENEMY
    - Units do NOT move unless pursuing a visible enemy.
    - As soon as an enemy is spotted (within vision_range), the unit moves to attack.
    - Prioritizes the nearest visible enemy.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Captain BRAINDEAD")

    def update(self, battlefield: Battlefield, tick: int) -> None:
        my_units = self.get_my_units(battlefield)
        enemies = self.get_enemy_units(battlefield)

        if not enemies:
            return

        for unit in my_units:
            if not unit.is_alive():
                continue

            # --- 1. Check current order persistence ---
            # If the unit already has an active attack order, let it continue execution
            if (unit.current_order and 
                unit.current_order["type"] == "attack_unit" and 
                unit.current_order["target"].is_alive()):
                continue # Let the UnitController handle the current chase/attack.

            # --- 2. Find a new target within VISION RANGE ---
            # Using the logic from UnitController, which relies on the battlefield for efficiency.
            visible_enemies = battlefield.units_in_los(unit) 
            # Note: Assuming units_in_los returns living *enemies* within vision_range.

            if visible_enemies:
                # Find the nearest enemy among the visible ones
                target = CombatSystem.choose_nearest_target(unit, visible_enemies)

                if target:
                    # Issue the ATTACK_UNIT order. The UnitController will handle movement
                    # towards the target until it is in attack range.
                    unit.current_order = {"type": "attack_unit", "target": target}
            else:
                # No visible targets, and no active order. Unit is truly idle.
                unit.current_order = None