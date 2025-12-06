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

    ISO_BASE_TILE_WIDTH = 64
    ISO_BASE_TILE_HEIGHT = 32

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
        # Calculate initial projected map dimensions without scaling
        # The isometric projection of (0,0) is (0,0) relative to an unshifted origin.
        # The isometric projection of (width,0) is (width * TILE_W/2, width * TILE_H/2)
        # The isometric projection of (0,height) is (-height * TILE_W/2, height * TILE_H/2)
        # The isometric projection of (width,height) is ((width-height)*TILE_W/2, (width+height)*TILE_H/2)

        projected_min_x_raw = -self.battlefield.height * (self.ISO_BASE_TILE_WIDTH / 2)
        projected_max_x_raw = self.battlefield.width * (self.ISO_BASE_TILE_WIDTH / 2)
        total_projected_width_raw = projected_max_x_raw - projected_min_x_raw

        projected_min_y_raw = 0 # The top-most point is (0,0) or (width,0) or (0,height)
        projected_max_y_raw = (self.battlefield.width + self.battlefield.height) * (self.ISO_BASE_TILE_HEIGHT / 2)
        total_projected_height_raw = projected_max_y_raw - projected_min_y_raw

        # Determine scaling factor if map is too large for the screen
        self.scale_factor = 1.0
        padding_ratio = 0.9  # Use 90% of screen for map to leave some margin
        if total_projected_width_raw > self.screen_width * padding_ratio or total_projected_height_raw > self.screen_height * padding_ratio:
            scale_x = (self.screen_width * padding_ratio) / total_projected_width_raw
            scale_y = (self.screen_height * padding_ratio) / total_projected_height_raw
            self.scale_factor = min(scale_x, scale_y)

        self._tile_width = self.ISO_BASE_TILE_WIDTH * self.scale_factor
        self._tile_height = self.ISO_BASE_TILE_HEIGHT * self.scale_factor

        # Recalculate projected dimensions with scaling applied
        projected_min_x = -self.battlefield.height * (self._tile_width / 2)
        projected_max_x = self.battlefield.width * (self._tile_width / 2)
        total_projected_width = projected_max_x - projected_min_x

        projected_min_y = 0
        projected_max_y = (self.battlefield.width + self.battlefield.height) * (self._tile_height / 2)
        total_projected_height = projected_max_y - projected_min_y

        # Calculate camera offset to center the entire projected map
        self.camera_offset_x = (self.screen_width / 2) - (projected_min_x + total_projected_width / 2)
        self.camera_offset_y = (self.screen_height / 2) - (projected_min_y + total_projected_height / 2)
    
    def world_to_screen(self, world_x, world_y):
        """
        Converts world (grid) coordinates to isometric screen coordinates.
        """
        screen_x = self.camera_offset_x + (world_x - world_y) * (self._tile_width / 2)
        screen_y = self.camera_offset_y + (world_x + world_y) * (self._tile_height / 2)
        return int(screen_x), int(screen_y)

    def get_key(self):
        """
        Processes Pygame events to get user input.
        Returns 'q' to quit, 'p' to pause.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "escape"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "escape"
                if event.key == pygame.K_q:
                    return "q"
                if event.key == pygame.K_p:
                    return "p"
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                    return "="
                if event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    return "-"
                if event.key == pygame.K_r:
                    return "r"
        return None

    def __enter__(self):
        """Allows the visualizer to be used as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensures Pygame is shut down cleanly on exit."""
        self.finish()
    
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
        radius = int(unit.radius * self._tile_width / 2)
        color = self.colors.get(unit.owner, (200, 200, 200))

        # Draw an ellipse for a 3D-like base
        ellipse_rect = pygame.Rect(screen_x - radius, screen_y - radius // 2, radius * 2, radius)
        pygame.draw.ellipse(self.screen, (0,0,0), ellipse_rect, 2) # Black outline
        pygame.draw.ellipse(self.screen, color, ellipse_rect.inflate(int(-4 * self.scale_factor), int(-4 * self.scale_factor)))

        # Draw a vertical line to represent the unit's body
        body_height = int(30 * self.scale_factor)
        line_width = int(4 * self.scale_factor) or 1 # Ensure line width is at least 1
        pygame.draw.line(self.screen, color, (screen_x, screen_y - body_height), (screen_x, screen_y), line_width)

        # Draw HP bar above the unit
        hp_ratio = unit.hp / unit.max_hp
        hp_bar_width = int(30 * self.scale_factor)
        hp_bar_height = int(5 * self.scale_factor) or 1 # Ensure hp bar height is at least 1
        hp_bar_x = screen_x - hp_bar_width // 2
        hp_bar_y = screen_y - body_height - int(10 * self.scale_factor)

        # Background of HP bar
        pygame.draw.rect(self.screen, (100, 0, 0), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
        # Foreground of HP bar
        pygame.draw.rect(self.screen, (0, 200, 0), (hp_bar_x, hp_bar_y, hp_bar_width * hp_ratio, hp_bar_height))
        # Border of HP bar
        pygame.draw.rect(self.screen, (0, 0, 0), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), int(1 * self.scale_factor) or 1)

    def render(self, battlefield: Battlefield, tick_count: int, speed: float = 1.0, paused: bool = False):
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

        # Display status text
        status_str = f"Tick: {tick_count} | Speed: x{speed:.1f}"
        if paused:
            status_str += " [PAUSED]"

        tick_text = self.font.render(status_str, True, (255, 255, 255))
        self.screen.blit(tick_text, (10, 10))

        pygame.display.flip()

    def finish(self):
        """
        Cleans up and quits Pygame.
        """
        print("Visualizer shutting down.")
        pygame.quit()