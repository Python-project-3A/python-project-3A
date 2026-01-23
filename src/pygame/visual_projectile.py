from math import hypot

from src.units.unit_base import Unit


class VisualProjectile:
    def __init__(self, start_pos: tuple[float, float], target_unit: Unit, speed=0.4):
        self.current_pos = list(start_pos)
        self.target_unit = target_unit
        self.speed = speed
        self.is_active = True

    def update(self):
        target_pos = self.target_unit.position
        dx = target_pos[0] - self.current_pos[0]
        dy = target_pos[1] - self.current_pos[1]
        dist = hypot(dx, dy)

        if dist < 0.2:  # Arrived
            self.is_active = False
            return

        self.current_pos[0] += (dx / dist) * self.speed
        self.current_pos[1] += (dy / dist) * self.speed
