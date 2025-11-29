import math


class Pikeman:
    _next_id = 0

    def __init__(self, owner: int, x: float, y: float):
        self.id = Pikeman._next_id
        Pikeman._next_id += 1

        # Identity
        self.name = "Pikeman"
        self.owner = owner

        # Position
        self.position = (float(x), float(y))

        # Physical
        self.width = 0.8
        self.height = 0.8

        # Combat stats (from AoE2)
        self.hp = 55
        self.max_hp = 55
        self.armor = 0
        self.damage = 4
        self.attack_range = 0.5  # Melee
        self.attack_cooldown = 3.0  # seconds
        self.speed = 1.0  # tiles per second

        # State
        self.time_since_last_attack = 0.0
        self.current_order = None
        self.current_target = None

    def is_alive(self) -> bool:
        return self.hp > 0

    def dist_to(self, other) -> float:
        x, y = self.position
        ox, oy = other.position
        return math.dist((x, y), (ox, oy))

    def edge_dist_to(self, other) -> float:
        center_dist = self.dist_to(other)
        self_radius = 0.5 * math.hypot(self.width, self.height)
        target_radius = 0.5 * math.hypot(other.width, other.height)
        return max(0.0, center_dist - (self_radius + target_radius))

    def can_attack(self, other) -> bool:
        return self.edge_dist_to(other) <= self.attack_range

    def dist_to_point(self, point: tuple[float, float]) -> float:
        x, y = self.position
        px, py = point
        return math.dist((x, y), (px, py))

    def __repr__(self):
        return f"<Pikeman id={self.id} owner={self.owner} pos={self.position} hp={self.hp}>"
