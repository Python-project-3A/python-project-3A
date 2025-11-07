# src/engine/battlefield.py
from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Iterable
import logging
from dataclasses import field

from src.map.game_map import GameMap
from src.map.tile import Tile

logger = logging.getLogger(__name__)


class Battlefield:
    """
    Battlefield orchestre la carte, les unités et les généraux.
    Il garantit la cohérence entre map.tiles[(x,y)].occupied et self.units.

    Note: ce module n'impose pas une implémentation concrète de Unit/General,
    mais s'attend aux attributs/méthodes minimales décrites dans le module doc.
    """

    def __init__(
        self,
        width: int,
        height: int,
        game_map: GameMap,
        units: Dict[int, object],
        generals: List[object],
        next_unit_id: int,
    ):
        self.width = width
        self.height = height
        self.game_map = field(init=False)
        self.units = field(default_factory=dict)  # unit_id -> Unit instance
        self.generals = field(default_factory=list)  # liste de General
        self.next_unit_id = field(default=1, init=False)

    def __post_init__(self):
        self.game_map = GameMap(self.width, self.height)
        logger.info("Battlefield initialisé %dx%d", self.width, self.height)
