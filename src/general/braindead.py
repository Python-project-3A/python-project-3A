from __future__ import annotations

from src.engine.battlefield import Battlefield

from .general_base import BaseGeneral


class GeneralBraindead(BaseGeneral):
    """
    Captain BRAINDEAD - The lobotomy victim.

    Strategy: NO STRATEGY AT ALL
    - Units act individually
    - They only attack if an enemy is RIGHT NEXT TO THEM
    - They don't seek combat
    - They don't move unless attacked

    This is basically: units have NO orders, they're idle.
    They will only react if attacked (retaliation behavior handled by systems).
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, name="Captain BRAINDEAD")

    def update(self, battlefield: Battlefield, tick: int) -> None:
        """
        BRAINDEAD does nothing.
        Units have no orders, they stand idle.
        They might attack if an enemy walks into their attack range
        (if the UnitController implements such reactive behavior).
        """
        my_units = self.get_my_units(battlefield)

        # Give NO orders - units remain idle
        for unit in my_units:
            if unit.is_alive():
                # Clear any existing orders
                unit.current_order = None

                # Optional: Make units attack ONLY if enemy is literally
                # within attack range (pure reactive, no seeking)
                enemies = battlefield.units_in_radius(unit.position[0], unit.position[1], unit.attack_range)
                enemies = [e for e in enemies if e.owner != self.player_id and e.is_alive()]

                if enemies:
                    # Enemy right next to us, attack the nearest one
                    nearest = min(enemies, key=lambda e: unit.dist_to(e))
                    unit.current_order = {"type": "attack_unit", "target": nearest}
