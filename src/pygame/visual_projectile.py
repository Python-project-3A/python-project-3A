from math import hypot

from src.units.unit_base import Unit


class VisualProjectile:
    def __init__(self, start_pos: tuple[float, float], target_unit: Unit, speed=0.4):
        self.current_pos = list(start_pos)
        self.target_unit = target_unit
        self.speed = speed
        self.is_active = True

        self.impact_point = list(target_unit.position)
        self.is_grounded = False
        self.ground_timer = 2.0  # Wait for 2 secs on the ground before dispawning

    def update(self, dt):
        if self.is_grounded:
            self.ground_timer -= dt
            if self.ground_timer <= 0:
                self.is_active = False
            return

        dx = self.impact_point[0] - self.current_pos[0]
        dy = self.impact_point[1] - self.current_pos[1]
        dist = hypot(dx, dy)

        # Move at constant speed
        step = self.speed
        if dist <= step:
            self.current_pos = self.impact_point
            self.is_grounded = True  # Don't kill yet, just stop moving
        else:
            self.current_pos[0] += (dx / dist) * step
            self.current_pos[1] += (dy / dist) * step
