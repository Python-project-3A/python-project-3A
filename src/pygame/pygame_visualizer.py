from pathlib import Path
from src.units.unit_base import Unit

import pygame

from src.engine.battlefield import Battlefield


class PygameVisualizer:
    """
    Renders the battlefield in a 2.5D isometric view using Pygame.
    Handles user input for pausing and quitting.
    """

    ISO_BASE_TILE_WIDTH = 64
    ISO_BASE_TILE_HEIGHT = 32

    def __init__(self, battlefield: Battlefield, screen_width=1280, screen_height=720):
        """
        Initializes Pygame, the screen, and visualizer settings.
        """
        pygame.init()

        # Enable key repeat: (delay_ms, interval_ms)
        pygame.key.set_repeat(500, 50)

        self.battlefield = battlefield
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Age of Empires 2 - Simulation")

        self.font = pygame.font.SysFont("Inter", 28)
        self.colors = {
            0: (50, 50, 255),  # Blue for Player 0
            1: (255, 50, 50),  # Red for Player 1
            "ground_fallback": (107, 142, 35),  # Olive Drab for the ground
        }

        # Load Textures
        self.load_assets()

        # Calculate initial scale factor to fit map on screen
        total_projected_width = (self.battlefield.width + self.battlefield.height) * (self.ISO_BASE_TILE_WIDTH / 2)
        total_projected_height = (self.battlefield.width + self.battlefield.height) * (self.ISO_BASE_TILE_HEIGHT / 2)

        self.scale_factor = 1.0
        padding_ratio = 0.9  # Use 90% of screen for map to leave some margin
        if total_projected_width > self.screen_width * padding_ratio or total_projected_height > self.screen_height * padding_ratio:
            scale_x = (self.screen_width * padding_ratio) / total_projected_width
            scale_y = (self.screen_height * padding_ratio) / total_projected_height
            self.scale_factor = min(scale_x, scale_y)

        self._tile_width = self.ISO_BASE_TILE_WIDTH * self.scale_factor
        self._tile_height = self.ISO_BASE_TILE_HEIGHT * self.scale_factor

        # Calculate camera offset to center the map
        self.camera_offset_x = self.screen_width / 2
        self.camera_offset_y = self.screen_height / 2

        self.update_map_texture()

    @staticmethod
    def load_img(name):
        texture_dir = Path(__file__).parent.parent / "data" / "textures"
        try:
            path = texture_dir / name
            if path.exists():
                return pygame.image.load(str(path)).convert_alpha()
        except Exception as e:
            print(f"Warning: Could not load {name}: {e}")
        return None

    def load_assets(self):
        """Loads the map texture and unit sprites."""
        # Load the grass texture that will cover everything
        self.grass_source = self.load_img("aoe-empty-map.png")

        if self.grass_source:
            # Pre-create a very large tiled surface that we'll use as base
            # This ensures we never run out of texture when zooming out
            base_size = 8192  # Very large base texture size
            self.base_map_surface = pygame.Surface((base_size, base_size))

            grass_w, grass_h = self.grass_source.get_size()
            for x in range(0, base_size, grass_w):
                for y in range(0, base_size, grass_h):
                    self.base_map_surface.blit(self.grass_source, (x, y))
        else:
            self.base_map_surface = None

        # Load unit sprites
        self.unit_sprites = {"knight": self.load_img("knight.png"), "crossbowman": self.load_img("crossbowman.png"), "pikeman": self.load_img("pikeman.png")}

        # Track unit HP to detect damage (for flash effect)
        self.unit_hp_tracker = {}

        # This will store the current zoomed version
        self.current_map_surface = None
        self.map_offset_x = 0
        self.map_offset_y = 0
        self.base_texture_size = 8192

    def update_map_texture(self):
        """
        Scales the base map surface according to current zoom level.
        Ensures texture is always large enough to cover the screen.
        """
        if not self.base_map_surface:
            return

        # Calculate minimum size needed to cover the screen with plenty of margin
        min_size_needed = max(self.screen_width, self.screen_height) * 4

        # Scale the base surface, but never smaller than what's needed to cover screen
        scaled_size = int(self.base_texture_size * self.scale_factor)
        scaled_size = max(scaled_size, int(min_size_needed))

        self.current_map_surface = pygame.transform.scale(self.base_map_surface, (scaled_size, scaled_size))

        # Calculate offset to center this surface on the battlefield
        center_world_x = self.battlefield.width / 2
        center_world_y = self.battlefield.height / 2
        screen_center_x, screen_center_y = self.world_to_screen(center_world_x, center_world_y)

        # Position the surface so its center aligns with battlefield center
        self.map_offset_x = screen_center_x - scaled_size / 2
        self.map_offset_y = screen_center_y - scaled_size / 2

    def zoom(self, direction: int):
        """
        Adjusts the zoom level.
        `direction` > 0 for zoom in, < 0 for zoom out.
        """
        zoom_step = 0.1
        if direction > 0:
            self.scale_factor *= 1 + zoom_step
        else:
            self.scale_factor *= 1 - zoom_step

        self._tile_width = self.ISO_BASE_TILE_WIDTH * self.scale_factor
        self._tile_height = self.ISO_BASE_TILE_HEIGHT * self.scale_factor
        self.update_map_texture()

    def move_camera(self, dx: int, dy: int):
        """
        Moves the camera by a given pixel offset.
        """
        self.camera_offset_x -= dx
        self.camera_offset_y -= dy
        # Update map position when camera moves
        if self.current_map_surface:
            center_world_x = self.battlefield.width / 2
            center_world_y = self.battlefield.height / 2
            screen_center_x, screen_center_y = self.world_to_screen(center_world_x, center_world_y)
            self.map_offset_x = screen_center_x - self.current_map_surface.get_width() / 2
            self.map_offset_y = screen_center_y - self.current_map_surface.get_height() / 2

    def world_to_screen(self, world_x, world_y):
        """
        Converts world (grid) coordinates to isometric screen coordinates.
        """
        screen_x = self.camera_offset_x + (world_x - world_y) * (self._tile_width / 2)
        screen_y = self.camera_offset_y + (world_x + world_y) * (self._tile_height / 2)
        return int(screen_x), int(screen_y)

    def __enter__(self):
        """Allows the visualizer to be used as a context manager."""
        return self

    def __exit__(self):
        """Ensures Pygame is shut down cleanly on exit."""
        self.finish()

    def _draw_background(self):
        """
        Draws the large tiled grass texture that covers everything.
        No distinction between background and ground - it's all one seamless texture.
        """
        if self.current_map_surface:
            self.screen.blit(self.current_map_surface, (self.map_offset_x, self.map_offset_y))
        else:
            # Fallback if texture didn't load
            self.screen.fill(self.colors["ground_fallback"])

    def _draw_unit(self, unit: Unit):
        """
        Draws a single unit on the screen at its isometric position using sprites.
        """
        world_x, world_y = unit.position
        screen_x, screen_y = self.world_to_screen(world_x, world_y)

        current_hp = unit.hp

        if unit.id not in self.unit_hp_tracker:
            self.unit_hp_tracker[unit.id] = [current_hp, 0]
        else:
            last_hp, flash_timer = self.unit_hp_tracker[unit.id]

            if current_hp < last_hp:
                flash_timer = 5

            if flash_timer > 0:
                flash_timer -= 1

            self.unit_hp_tracker[unit.id] = [current_hp, flash_timer]

        # Draw team color ellipse under the unit
        if unit.owner in self.colors:
            ellipse_radius = int(16 * self.scale_factor)
            ellipse_rect = pygame.Rect(screen_x - ellipse_radius, screen_y - ellipse_radius // 3, ellipse_radius * 2.5, int(ellipse_radius * 0.6))
            player_color = self.colors[unit.owner]
            pygame.draw.ellipse(self.screen, player_color, ellipse_rect)
            pygame.draw.ellipse(self.screen, (0, 0, 0), ellipse_rect, 1)  # Black outline

        # Get the appropriate sprite based on unit type
        sprite = self.unit_sprites.get(unit.name.lower())

        if sprite:
            # Scale sprite according to zoom level
            base_unit_size = int(40 * self.scale_factor)

            # Maintain aspect ratio
            sprite_rect = sprite.get_rect()
            aspect_ratio = sprite_rect.width / sprite_rect.height

            if aspect_ratio > 1:
                sprite_width = base_unit_size
                sprite_height = int(base_unit_size / aspect_ratio)
            else:
                sprite_height = base_unit_size
                sprite_width = int(base_unit_size * aspect_ratio)

            scaled_sprite = pygame.transform.scale(sprite, (sprite_width, sprite_height))

            _, flash_timer = self.unit_hp_tracker[unit.id]
            if flash_timer > 0:
                # red flash overlay
                flash_sprite = scaled_sprite.copy()
                red_overlay = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
                red_overlay.fill((255, 0, 0, 180))  # Red with opacity

                # apply red tint to non-transparent pixels
                flash_sprite.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                # Then add brightness to make it pop
                bright_overlay = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
                bright_overlay.fill((100, 0, 0, 100))
                flash_sprite.blit(bright_overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

                scaled_sprite = flash_sprite

            # Center the sprite on the unit position
            sprite_rect = scaled_sprite.get_rect()
            sprite_rect.centerx = screen_x
            sprite_rect.bottom = screen_y

            self.screen.blit(scaled_sprite, sprite_rect)
        else:
            # Fallback to simple representation if sprite not found
            radius = int(unit.radius * self._tile_width / 2)
            color = self.colors.get(unit.owner, (200, 200, 200))
            ellipse_rect = pygame.Rect(screen_x - radius, screen_y - radius // 2, radius * 2, radius)
            pygame.draw.ellipse(self.screen, color, ellipse_rect)

        # Draw HP bar above the unit
        hp_ratio = unit.hp / unit.max_hp
        hp_bar_width = int(30 * self.scale_factor)
        hp_bar_height = int(5 * self.scale_factor) or 1

        # Position HP bar above the sprite
        body_height = int(40 * self.scale_factor)
        hp_bar_x = screen_x - hp_bar_width // 2
        hp_bar_y = screen_y - body_height - int(10 * self.scale_factor)

        # Background of HP bar
        pygame.draw.rect(self.screen, (100, 0, 0), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
        # Foreground of HP bar
        pygame.draw.rect(self.screen, (0, 200, 0) if unit.hp > unit.max_hp * 0.2 else (200, 0, 0), (hp_bar_x, hp_bar_y, int(hp_bar_width * hp_ratio), hp_bar_height))
        # Border of HP bar
        pygame.draw.rect(self.screen, (0, 0, 0), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), int(1 * self.scale_factor) or 1)

    def render(self, battlefield: Battlefield, tick_count: int, speed: float = 1.0, paused: bool = False):
        """
        Renders the entire scene.
        1. Fills the background.
        2. Draws the ground (large tiled texture).
        3. Sorts all units by their Y-coordinate (Painter's Algorithm).
        4. Draws each unit in the sorted order.
        5. Updates the display.
        """
        self._draw_background()

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
