from .unit_base import Unit


class Pikeman(Unit):
    def __init__(self, owner: int, x: float, y: float, r: float, max_hp: int, armor: int, damage: int, attack_range: float, attack_cooldown: float, speed: float, name: str = "Pikeman"):
        super().__init__(name=name, owner=owner, x=x, y=y, r=r, max_hp=max_hp, armor=armor, damage=damage, attack_range=attack_range, attack_cooldown=attack_cooldown, speed=speed)

    def __repr__(self):
        return f"<Pikeman id={self.id} owner={self.owner} pos={self.position} hp={self.hp}>"
