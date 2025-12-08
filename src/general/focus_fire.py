from __future__ import annotations

from typing import TYPE_CHECKING

from src.engine.system import CombatSystem

from .general_base import BaseGeneral

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


class GeneralFocusFire(BaseGeneral):
    """
    Colonel FOCUSFIRE - The focused assassin.

    Strategy: CONCENTRATION OF FIRE
    - All units concentrate on eliminating one target at a time
    - Focus target = enemy with lowest HP (easiest kill)
    - When target dies, switch to next lowest HP
    - This ensures rapid elimination of enemies one by one
    - Very effective at snowballing victory

    Pros:
    - Eliminates threats quickly
    - Snowball effect: as units die, remaining units are weaker
    - Simple coordination
    - Efficient resource use

    Cons:
    - Can waste effort on "tank" units with high HP
    - Vulnerable to scatter/retreat tactics
    - Can be baited into bad positions
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Colonel FOCUSFIRE")
        self.focus_target: Unit | None = None

    def _choose_focus_target(self, enemies: list[Unit]) -> Unit | None:
        """
        Choose the next focus target.
        Strategy: lowest HP enemy (easiest to kill quickly).
        """
        if not enemies:
            return None

        # Filter alive enemies
        alive_enemies = [e for e in enemies if e.is_alive()]
        if not alive_enemies:
            return None

        # Sort by HP (ascending) - choose weakest enemy
        sorted_enemies = sorted(alive_enemies, key=lambda e: e.hp)

        return sorted_enemies[0]

    def update(self, battlefield: Battlefield, tick: int) -> None:
        """
        FocusFire: All units attack the same target (lowest HP enemy).
        """
        my_units = self.get_my_units(battlefield)
        enemies = self.get_enemy_units(battlefield)

        if not enemies:
            # No enemies left, we won!
            return

        # Update focus target if dead or not set
        if self.focus_target is None or not self.focus_target.is_alive():
            self.focus_target = self._choose_focus_target(enemies)

        if self.focus_target is None:
            # Fallback: this shouldn't happen but safety net
            return

        # Issue orders to all units
        for unit in my_units:
            if not unit.is_alive():
                continue

            enemies_in_range = CombatSystem.get_enemies_in_range(unit, [self.focus_target])

            if enemies_in_range:
                # Target is in attack range, attack it
                unit.current_order = {"type": "attack_unit", "target": self.focus_target}
            else:
                # Target is not in range, move towards it
                unit.current_order = {"type": "move_to", "target": self.focus_target.position}
