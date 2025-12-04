import sys

import pygame

from src.engine.battlefield import Battlefield
from src.map.game_map import GameMap
from src.units.unit_base import Unit

class PygameVisualizer:
    """
    Renders the battlefield in a 2.5D isometric view using Pygame.
    Handles user input for pausing and quitting.
    """

    ISO_TILE_WIDTH = 64
    ISO_TILE_HEIGHT = 32

    def __init__(self, battlefield, screen_width=1280, screen_height=720):
        """
        Initializes Pygame, the screen, and visualizer settings.
        """
        pygame.init()
        self.battlefield = battlefield
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Age of Empires 2 - Simulation")
        
        self.font = pygame.font.SysFont("Arial", 16)
        self.colors = {
            0: (50, 50, 255),  # Blue for Player 0
            1: (255, 50, 50),  # Red for Player 1
            "bg": (24, 116, 205),  # A deep blue for the "sea"
            "ground": (107, 142, 35),  # Olive Drab for the ground
        }

        # Camera offset to center the map
        self.camera_offset_x = self.screen_width / 2
        self.camera_offset_y = 100  # Offset from the top of the screen
    
    def world_to_screen(self, world_x, world_y):
        """
        Converts world (grid) coordinates to isometric screen coordinates.
        """
        screen_x = self.camera_offset_x + (world_x - world_y) * (self.ISO_TILE_WIDTH / 2)
        screen_y = self.camera_offset_y + (world_x + world_y) * (self.ISO_TILE_HEIGHT / 2)
        return int(screen_x), int(screen_y)

    def get_key(self):
        """
        Processes Pygame events to get user input.
        Returns 'q' to quit, 'p' to pause.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "q"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return "q"
                if event.key == pygame.K_p:
                    return "p"
        return None
    
    def _draw_ground(self):
        """
        Draws the isometric ground plane.
        """
        # Create a diamond shape for the ground
        points = [
            self.world_to_screen(0, 0),
            self.world_to_screen(self.battlefield.width, 0),
            self.world_to_screen(self.battlefield.width, self.battlefield.height),
            self.world_to_screen(0, self.battlefield.height),
        ]
        pygame.draw.polygon(self.screen, self.colors["ground"], points)
        pygame.draw.polygon(self.screen, (0, 0, 0), points, 2) # Black border

    def _draw_unit(self, unit):
        """
        Draws a single unit on the screen at its isometric position.
        """
        world_x, world_y = unit.position
        screen_x, screen_y = self.world_to_screen(world_x, world_y)

        # Simple representation: a circle as the base
        radius = int(unit.radius * self.ISO_TILE_WIDTH / 2)
        color = self.colors.get(unit.owner, (200, 200, 200))

        # Draw an ellipse for a 3D-like base
        ellipse_rect = pygame.Rect(screen_x - radius, screen_y - radius // 2, radius * 2, radius)
        pygame.draw.ellipse(self.screen, (0,0,0), ellipse_rect, 2) # Black outline
        pygame.draw.ellipse(self.screen, color, ellipse_rect.inflate(-4, -4))

        # Draw a vertical line to represent the unit's body
        body_height = 30
        pygame.draw.line(self.screen, color, (screen_x, screen_y - body_height), (screen_x, screen_y), 4)

        # Draw HP bar above the unit
        hp_ratio = unit.hp / unit.max_hp
        hp_bar_width = 30
        hp_bar_height = 5
        hp_bar_x = screen_x - hp_bar_width // 2
        hp_bar_y = screen_y - body_height - 10

        # Background of HP bar
        pygame.draw.rect(self.screen, (100, 0, 0), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
        # Foreground of HP bar
        pygame.draw.rect(self.screen, (0, 200, 0), (hp_bar_x, hp_bar_y, hp_bar_width * hp_ratio, hp_bar_height))
        # Border of HP bar
        pygame.draw.rect(self.screen, (0, 0, 0), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), 1)

    def render(self, battlefield: Battlefield, tick_count: int):
        """
        Renders the entire scene.
        1. Fills the background.
        2. Draws the ground.
        3. Sorts all units by their Y-coordinate (Painter's Algorithm).
        4. Draws each unit in the sorted order.
        5. Updates the display.
        """
        self.screen.fill(self.colors["bg"])

        self._draw_ground()

        # --- Y-SORTING (PAINTER'S ALGORITHM) ---
        # Get all units and sort them by their world Y-coordinate.
        # This ensures objects further "back" (smaller Y) are drawn first.
        all_units = battlefield.get_all_units()
        sorted_units = sorted(all_units, key=lambda u: u.position[1])

        for unit in sorted_units:
            if unit.is_alive():
                self._draw_unit(unit)

        # Display tick count
        tick_text = self.font.render(f"Tick: {tick_count}", True, (255, 255, 255))
        self.screen.blit(tick_text, (10, 10))

        pygame.display.flip()

    def finish(self):
        """
        Cleans up and quits Pygame.
        """
        print("Visualizer shutting down.")
        pygame.quit()