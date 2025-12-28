import sys
from pathlib import Path

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

        # Enable key repeat: (delay_ms, interval_ms)
        pygame.key.set_repeat(500, 50)

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

        # Load Textures
        self.load_assets()

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
        self.base_scale_factor = 1.0 # To keep the initial fit-to-screen scale
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

        self.update_tile_textures()

    def load_assets(self):
        """Loads textures from data/textures."""
        texture_dir = Path(__file__).parent.parent / "data" / "textures"
        
        def load_img(name):
            try:
                path = texture_dir / name
                if path.exists():
                    return pygame.image.load(str(path)).convert_alpha()
            except Exception as e:
                print(f"Warning: Could not load {name}: {e}")
            return None

        self.water_img = load_img("g_wtr_00_color.png")

        # Load multiple grass textures for variety to avoid a repetitive look
        self.grass_textures_raw = []
        # Using a single grass texture for consistency
        img = load_img("g_gr2_00_color.png")
        if img:
            self.grass_textures_raw.append(img)

        # Keep high-resolution rotated versions of each texture
        # Scaling will be done from these sources, ensuring quality at any zoom level
        self.grass_iso_rotated_imgs = []
        if self.grass_textures_raw:
            for img_raw in self.grass_textures_raw:
                self.grass_iso_rotated_imgs.append(pygame.transform.rotate(img_raw, 45))

        self.current_grass_tiles = []

    def update_tile_textures(self):
        """Rescales tile sprites based on current zoom level."""
        self.current_grass_tiles = []
        if self.grass_iso_rotated_imgs:
            for rotated_img in self.grass_iso_rotated_imgs:
                # Scale from the high-res rotated source to the target size for rendering
                # This ensures textures look good even when zoomed in
                scaled_tile = pygame.transform.scale(rotated_img, (int(self._tile_width), int(self._tile_height)))
                self.current_grass_tiles.append(scaled_tile)

    def zoom(self, direction: int):
        """
        Adjusts the zoom level.
        `direction` > 0 for zoom in, < 0 for zoom out.
        """
        zoom_step = 0.1
        if direction > 0:
            self.scale_factor *= (1 + zoom_step)
        else:
            self.scale_factor *= (1 - zoom_step)
        
        self._tile_width = self.ISO_BASE_TILE_WIDTH * self.scale_factor
        self._tile_height = self.ISO_BASE_TILE_HEIGHT * self.scale_factor
        self.update_tile_textures()

    def move_camera(self, dx: int, dy: int):
        """
        Moves the camera by a given pixel offset.
        """
        self.camera_offset_x -= dx
        self.camera_offset_y -= dy

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
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    return "zoom_in"
                elif event.y < 0:
                    return "zoom_out"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "escape"
                # Camera Movement Keys
                if event.key in (pygame.K_w, pygame.K_z): return "w" # z for AZERTY
                if event.key == pygame.K_s: return "s"
                if event.key in (pygame.K_a, pygame.K_q): return "a" # q for AZERTY
                if event.key == pygame.K_d: return "d"

                # Simulation Control Keys
                if event.key == pygame.K_p:
                    return "p"
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                    return "="
                if event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS or event.key == pygame.K_6:
                    return "-"
                if event.key == pygame.K_r:
                    return "r"
                if event.key == pygame.K_TAB:
                    return "tab"

        return None

    def __enter__(self):
        """Allows the visualizer to be used as a context manager."""
        return self

    def __exit__(self):
        """Ensures Pygame is shut down cleanly on exit."""
        self.finish()
    
    def _draw_background(self):
        """Draws the water background (tiled) or solid color."""
        if self.water_img:
            w, h = self.water_img.get_size()
            # Simple tiling
            for x in range(0, self.screen_width, w):
                for y in range(0, self.screen_height, h):
                    self.screen.blit(self.water_img, (x, y))
        else:
            self.screen.fill(self.colors["bg"])

    def _draw_ground(self):
        """
        Draws the isometric ground plane.
        """
        # Draw a solid base polygon first to hide gaps/cracks between tiles
        points = [
            self.world_to_screen(0, 0),
            self.world_to_screen(self.battlefield.width, 0),
            self.world_to_screen(self.battlefield.width, self.battlefield.height),
            self.world_to_screen(0, self.battlefield.height),
        ]
        pygame.draw.polygon(self.screen, self.colors["ground"], points)

        # Draw tiles if texture is available
        if self.current_grass_tiles:
            half_w = int(self._tile_width / 2)
            num_textures = len(self.current_grass_tiles)
            # Iterate over all map tiles
            for x in range(self.battlefield.width):
                for y in range(self.battlefield.height):
                    sx, sy = self.world_to_screen(x, y)
                    # Simple culling to avoid drawing off-screen tiles
                    if -self._tile_width < sx < self.screen_width + self._tile_width and -self._tile_height < sy < self.screen_height + self._tile_height:
                        # Choose a texture based on tile position for variety, creating a non-uniform, more natural look.
                        # Using prime numbers in the hash helps to break up patterns.
                        texture_index = (x * 7 + y * 13) % num_textures
                        tile_to_draw = self.current_grass_tiles[texture_index]
                        # Center the sprite horizontally (sx is the top vertex x, which is the center of the tile's width)
                        self.screen.blit(tile_to_draw, (sx - half_w, sy))

        # Draw Map Border
        points = [
            self.world_to_screen(0, 0),
            self.world_to_screen(self.battlefield.width, 0),
            self.world_to_screen(self.battlefield.width, self.battlefield.height),
            self.world_to_screen(0, self.battlefield.height),
        ]
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
        self._draw_background()
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