from .unit_base import Unit


class Crossbowman(Unit):
    def __init__(self, owner: int, x: float, y: float, r: float, max_hp: int, armor: int, damage: int, attack_range: float, attack_cooldown: float, vision_range:float, speed: float, name: str = "Crossbowman"):
        super().__init__(name=name, owner=owner, x=x, y=y, r=r, max_hp=max_hp, armor=armor, damage=damage, attack_range=attack_range, attack_cooldown=attack_cooldown, vision_range=vision_range ,speed=speed)

    def __repr__(self):
        return f"<Crossbowman id={self.id} owner={self.owner} pos={self.position} max_hp={self.max_hp}>"