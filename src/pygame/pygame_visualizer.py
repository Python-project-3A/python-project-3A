from screeninfo import get_monitors
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

    MIN_ZOOM = 0.2
    MAX_ZOOM = 5.0

    monitor = get_monitors()[0]

    def __init__(self, battlefield: Battlefield, screen_width=monitor.width if monitor else 1280, screen_height=monitor.height if monitor else 720):
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

        # Minimap settings
        self.minimap_size = 200
        self.minimap_padding = 20
        self.minimap_position = (self.screen_width - self.minimap_size - self.minimap_padding, self.screen_height - self.minimap_size - self.minimap_padding)

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

        # Apply additional zoom to start closer to the action
        self.scale_factor *= 2.25

        self._tile_width = self.ISO_BASE_TILE_WIDTH * self.scale_factor
        self._tile_height = self.ISO_BASE_TILE_HEIGHT * self.scale_factor

        # Calculate camera offset to center on the units
        # Find the center point between all units
        all_units = list(battlefield.get_all_units())

        if all_units:
            # Calculate average position of all units
            avg_x = sum(u.position[0] for u in all_units) / len(all_units)
            avg_y = sum(u.position[1] for u in all_units) / len(all_units)

            # Convert to screen coordinates
            target_screen_x = (avg_x - avg_y) * (self._tile_width / 2)
            target_screen_y = (avg_x + avg_y) * (self._tile_height / 2)

            # Set camera offset to center this point on screen
            self.camera_offset_x = self.screen_width / 2 - target_screen_x
            self.camera_offset_y = self.screen_height / 2 - target_screen_y
        else:
            # Fallback: center on battlefield
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

        # Load unit sprites
        self.unit_sprites = {"knight": self.load_img("knight.png"), "crossbowman": self.load_img("crossbowman.png"), "pikeman": self.load_img("pikeman.png")}

        # Track unit HP to detect damage (for flash effect)
        self.unit_hp_tracker = {}

        # This will store the current zoomed version of the single tile
        self.scaled_grass = None

    def update_map_texture(self):
        """
        Scales the grass texture according to current zoom level.
        """
        if not self.grass_source:
            return

        # Scale the single grass tile instead of a giant map
        w, h = self.grass_source.get_size()
        new_w = int(w * self.scale_factor)
        new_h = int(h * self.scale_factor)

        # Ensure at least 1x1
        new_w = max(1, new_w)
        new_h = max(1, new_h)

        self.scaled_grass = pygame.transform.scale(self.grass_source, (new_w, new_h))

    def zoom(self, direction: int):
        """
        Adjusts the zoom level.
        `direction` > 0 for zoom in, < 0 for zoom out.
        """
        mouse_x, mouse_y = pygame.mouse.get_pos()
        old_scale = self.scale_factor

        zoom_step = 0.1
        if direction > 0:
            self.scale_factor *= 1 + zoom_step
        else:
            self.scale_factor *= 1 - zoom_step

        # Clamp zoom level to prevent infinite zooming
        self.scale_factor = max(self.MIN_ZOOM, min(self.scale_factor, self.MAX_ZOOM))

        # Adjust camera offset to zoom towards the mouse cursor
        scale_ratio = self.scale_factor / old_scale
        self.camera_offset_x = mouse_x - (mouse_x - self.camera_offset_x) * scale_ratio
        self.camera_offset_y = mouse_y - (mouse_y - self.camera_offset_y) * scale_ratio

        self._tile_width = self.ISO_BASE_TILE_WIDTH * self.scale_factor
        self._tile_height = self.ISO_BASE_TILE_HEIGHT * self.scale_factor
        self.update_map_texture()

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
        self.screen.fill((0, 0, 0))  # Fill the "void" with black

    def _draw_ground(self):
        """
        Draws the tiled grass texture ONLY within the isometric battlefield boundaries.
        """
        if not self.scaled_grass:
            return

        # 1. Define the battlefield corner points in screen coordinates
        corners = [self.world_to_screen(0, 0), self.world_to_screen(self.battlefield.width, 0), self.world_to_screen(self.battlefield.width, self.battlefield.height), self.world_to_screen(0, self.battlefield.height)]

        # 2. Create a clipping region for the diamond shape
        # We use a polygon mask to ensure grass doesn't bleed into the black void
        tile_w = self.scaled_grass.get_width()
        tile_h = self.scaled_grass.get_height()

        # Calculate bounding box of the diamond to optimize tiling loops
        min_x = min(p[0] for p in corners)
        max_x = max(p[0] for p in corners)
        min_y = min(p[1] for p in corners)
        max_y = max(p[1] for p in corners)

        # We create a temporary surface to act as a mask
        mask_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        pygame.draw.polygon(mask_surf, (255, 255, 255, 255), corners)

        # Calculate offset to keep texture pinned to world space
        offset_x = int(self.camera_offset_x) % tile_w
        offset_y = int(self.camera_offset_y) % tile_h

        # Tile only within the bounding box of the battlefield
        for x in range(int(min_x // tile_w * tile_w) + offset_x - tile_w, int(max_x) + tile_w, tile_w):
            for y in range(int(min_y // tile_h * tile_h) + offset_y - tile_h, int(max_y) + tile_h, tile_h):
                self.screen.blit(self.scaled_grass, (x, y))

        # Black out everything outside the diamond (the "void")
        # We do this by creating a surface with a hole in it
        void_mask = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        void_mask.fill((0, 0, 0, 255))
        pygame.draw.polygon(void_mask, (0, 0, 0, 0), corners)  # Cut the diamond out
        self.screen.blit(void_mask, (0, 0))

        # Optional: Draw a subtle border around the map
        pygame.draw.polygon(self.screen, (50, 50, 50), corners, 2)

    def world_to_minimap(self, world_x: float, world_y: float, left: tuple[float, float], top: tuple[float, float], diamond_width: int, diamond_height: int):
        # Normalize world coordinates (0 to 1)
        norm_x = world_x / self.battlefield.width
        norm_y = world_y / self.battlefield.height

        horizontal = (norm_x + (1 - norm_y)) / 2

        vertical = (norm_x + norm_y) / 2

        # Map to diamond on minimap
        map_x = left[0] + horizontal * diamond_width
        map_y = top[1] + vertical * diamond_height

        return int(map_x), int(map_y)

    def _draw_minimap(self, battlefield: Battlefield):
        """
        Draws a minimap showing the entire battlefield and unit positions.
        """
        minimap_x, minimap_y = self.minimap_position

        # Create minimap surface with extra space for the diamond shape
        minimap_surface = pygame.Surface((self.minimap_size, self.minimap_size), pygame.SRCALPHA)
        minimap_surface.fill((0, 0, 0, 0))

        # Calculate diamond dimensions
        diamond_width = self.minimap_size
        diamond_height = self.minimap_size // 2

        # Center the diamond in the minimap surface
        center_x = self.minimap_size // 2
        center_y = self.minimap_size // 2

        # Diamond corner points
        top = (center_x, center_y - diamond_height // 2)
        right = (center_x + diamond_width // 2, center_y)
        bottom = (center_x, center_y + diamond_height // 2)
        left = (center_x - diamond_width // 2, center_y)

        # Draw the minimap background
        bg_rect = pygame.Rect(0, top[1], self.minimap_size, self.minimap_size // 2)
        pygame.draw.rect(minimap_surface, (201, 152, 104), bg_rect)

        diamond_points = [top, right, bottom, left]
        if self.grass_source:
            # Create a temporary surface for the textured diamond
            tex_surface = pygame.Surface((diamond_width, diamond_height), pygame.SRCALPHA)

            # Scale a portion of the grass source to the diamond's size
            crop_size = min(self.grass_source.get_size())
            sub_grass = self.grass_source.subsurface((0, 0, crop_size, crop_size))
            scaled_grass = pygame.transform.scale(sub_grass, (diamond_width, diamond_height))

            # Create a mask in the shape of a diamond
            mask_surface = pygame.Surface((diamond_width, diamond_height), pygame.SRCALPHA)
            mask_surface.fill((0, 0, 0, 0))
            # Local diamond points relative to the tex_surface
            local_diamond = [(diamond_width // 2, 0), (diamond_width, diamond_height // 2), (diamond_width // 2, diamond_height), (0, diamond_height // 2)]
            pygame.draw.polygon(mask_surface, (255, 255, 255, 255), local_diamond)

            # Blit the grass onto the mask using BLEND_RGBA_MIN to "cut out" the diamond shape
            tex_surface.blit(scaled_grass, (0, 0))
            tex_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            # Blit the resulting textured diamond onto the minimap
            minimap_surface.blit(tex_surface, (0, top[1]))
        else:
            # Fallback to solid color if texture is missing
            pygame.draw.polygon(minimap_surface, (107, 142, 35), diamond_points)
        # Draw diamond border
        pygame.draw.polygon(minimap_surface, (154, 133, 90), diamond_points, 5)

        # Draw units as colored dots
        all_units = battlefield.get_all_units()
        for unit in all_units:
            if unit.is_alive():
                unit_x, unit_y = self.world_to_minimap(unit.position[0], unit.position[1], left, top, diamond_width, diamond_height)

                color = self.colors.get(unit.owner, (200, 200, 200))
                pygame.draw.circle(minimap_surface, color, (unit_x, unit_y), 3)

        # Find the world coordinates of the screen center
        sum_coords = (self.screen_height / 2 - self.camera_offset_y) / (self._tile_height / 2)
        diff_coords = (self.screen_width / 2 - self.camera_offset_x) / (self._tile_width / 2)
        camera_center_world_x = (sum_coords + diff_coords) / 2
        camera_center_world_y = (sum_coords - diff_coords) / 2

        # Get the screen center point on the minimap
        cam_x, cam_y = self.world_to_minimap(camera_center_world_x, camera_center_world_y, left, top, diamond_width, diamond_height)

        # Calculate rectangle dimensions relative to the minimap scale
        rect_w = int(self.minimap_size * 0.3 * (self.screen_width / (self.battlefield.width * self._tile_width)))
        rect_h = int((self.minimap_size // 2) * 0.3 * (self.screen_height / (self.battlefield.height * self._tile_height)))

        camera_rect = pygame.Rect(0, 0, rect_w, rect_h)
        camera_rect.center = (cam_x, cam_y)

        pygame.draw.rect(minimap_surface, (255, 255, 255), camera_rect, 1)

        # Blit minimap to screen
        self.screen.blit(minimap_surface, (minimap_x, minimap_y))

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

    def _draw_game_over(self):
        # Darken the battlefield
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Results Box (Main Parchment Container)
        w, h = 800, 520
        x, y = (self.screen_width - w) // 2, (self.screen_height - h) // 2
        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, w, h), border_radius=12)
        pygame.draw.rect(self.screen, (201, 152, 104), (x, y, w, h), 3, border_radius=12)

        # Title
        title_font = pygame.font.SysFont("Inter", 40, bold=True)
        title_surf = title_font.render("BATTLE SUMMARY", True, (201, 152, 104))
        self.screen.blit(title_surf, (x + (w - title_surf.get_width()) // 2, y + 30))

        # Data processing
        survivors = {0: [], 1: []}
        for u in self.battlefield.get_all_units():
            if u.is_alive():
                survivors[u.owner].append(u)

        # Draw Centered Columns with Borders
        center_x = x + w // 2
        col_width = 280
        col_height = 220
        spacing = 30

        for p_id in [0, 1]:
            color = self.colors[p_id]
            gen = self.battlefield.generals[p_id]
            units = survivors[p_id]
            hp = sum(u.hp for u in units)

            # Position the column box
            if p_id == 0:
                col_x = center_x - col_width - spacing
            else:
                col_x = center_x + spacing

            col_y = y + 100

            # Fill the column background slightly differently to pop
            pygame.draw.rect(self.screen, (40, 40, 40), (col_x, col_y, col_width, col_height), border_radius=8)
            # Draw the colored border (2px thickness)
            pygame.draw.rect(self.screen, color, (col_x, col_y, col_width, col_height), 2, border_radius=8)

            # Text positions inside the column
            text_x = col_x + 20
            curr_y = col_y + 20

            # Header
            header_surf = self.font.render(f"{gen.name}", True, color)
            self.screen.blit(header_surf, (text_x, curr_y))
            curr_y += 60

            # Stats
            stat_font = pygame.font.SysFont("Inter", 22, bold=True)
            lines = [f"Survivors: {len(units)}", f"Total HP: {hp:.1f}", f"Avg HP: {(hp / len(units)) if units else 0.0:.1f}"]
            for line in lines:
                self.screen.blit(stat_font.render(line, True, (220, 220, 220)), (text_x, curr_y))
                curr_y += 40

        # Split-Color Victory Banner (centered below columns)
        banner_font = pygame.font.SysFont("Inter", 38, bold=True)

        if len(survivors[0]) > 0 and len(survivors[1]) == 0:
            prefix, winner_name, winner_color = "VICTORY FOR ", self.battlefield.generals[0].name.upper(), self.colors[0]
        elif len(survivors[1]) > 0 and len(survivors[0]) == 0:
            prefix, winner_name, winner_color = "VICTORY FOR ", self.battlefield.generals[1].name.upper(), self.colors[1]
        else:
            prefix, winner_name, winner_color = "DRAW - MUTUAL DESTRUCTION", "", (255, 255, 255)

        prefix_surf = banner_font.render(prefix, True, (255, 255, 255))
        winner_surf = banner_font.render(winner_name, True, winner_color)
        excl_surf = banner_font.render("!", True, (255, 255, 255))

        total_msg_width = prefix_surf.get_width() + winner_surf.get_width() + (excl_surf.get_width() if winner_name else 0)
        msg_x = x + (w - total_msg_width) // 2
        msg_y = y + h - 130

        self.screen.blit(prefix_surf, (msg_x, msg_y))
        self.screen.blit(winner_surf, (msg_x + prefix_surf.get_width(), msg_y))
        if winner_name:
            self.screen.blit(excl_surf, (msg_x + prefix_surf.get_width() + winner_surf.get_width(), msg_y))

        # Bottom Hint
        hint_surf = pygame.font.SysFont("Inter", 18).render("PRESS ESCAPE TO EXIT", True, (120, 120, 120))
        self.screen.blit(hint_surf, (x + (w - hint_surf.get_width()) // 2, y + h - 45))

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
        self._draw_ground()

        # --- Y-SORTING (PAINTER'S ALGORITHM) ---
        # Get all units and sort them by their world Y-coordinate.
        # This ensures objects further "back" (smaller Y) are drawn first.
        all_units = battlefield.get_all_units()
        sorted_units = sorted(all_units, key=lambda u: u.position[1])

        for unit in sorted_units:
            if unit.is_alive():
                self._draw_unit(unit)

        # Draw minimap
        self._draw_minimap(battlefield)

        # Display status text
        status_str = f"Tick: {tick_count} | Speed: x{speed:.1f}"
        if paused:
            status_str += " [PAUSED]"

        tick_text = self.font.render(status_str, True, (255, 255, 255))
        self.screen.blit(tick_text, (10, 10))

        # we draw the game over screen if the battle is over
        if battlefield.is_battle_over():
            self._draw_game_over()

        pygame.display.flip()

    def finish(self):
        """
        Cleans up and quits Pygame.
        """
        print("Visualizer shutting down.")
        pygame.quit()
