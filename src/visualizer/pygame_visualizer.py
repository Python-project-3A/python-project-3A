import sys

import pygame

from src.engine.battlefield import Battlefield
from src.map.game_map import GameMap
from src.units.unit_base import Unit

class PygameVisualizer:
    def __init__(self, width: int, height: int, tile_size: int = 32):
        pygame.init()

        self.tile_size = tile_size
        self.screen_width = width * self.tile_size
        self.screen_height = height * self.tile_size
        self.screen = pygame.display.setmode((self.screen_width, self.screen_height))
        pygame.display.setcaption("Age of Empires 2 - Simulation")
        self.clock = pygame.time.Clock()
        self.running = True