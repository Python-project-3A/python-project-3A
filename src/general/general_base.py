from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit


class BaseGeneral(ABC):
    """
    Base class for all generals (AI commanders).
    Each general controls units of one player/team.
    """

    def __init__(self, player_id: int, name: str = "General"):
        self.player_id = player_id  # 0 or 1
        self.name = name

    @abstractmethod
    def update(self, battlefield: Battlefield, tick: int) -> None:
        """
        Called every tick by the simulation.
        General analyzes the battlefield and gives orders to units.

        Args:
            battlefield: The battlefield state
            tick: Current tick number
        """
        pass

    def get_my_units(self, battlefield: Battlefield) -> list[Unit]:
        """Get all units belonging to this general"""
        return battlefield.units_by_owner(self.player_id)

    def get_enemy_units(self, battlefield: Battlefield) -> list[Unit]:
        """Get all enemy units"""
        all_units = battlefield.get_all_units()
        return [u for u in all_units if u.owner != self.player_id and u.is_alive()]

    def __repr__(self):
        return f"<{self.__class__.__name__} player={self.player_id} name={self.name}>"
