from .unit_base import Unit


class Knight(Unit):
    def __init__(self, owner: int, x: float, y: float, height: float, width: float, hp: int, armor: int, damage: int, attack_range: float, attack_cooldown: float, speed: float, name: str = "Knight"):
        super().__init__(name=name, owner=owner, x=x, y=y, height=height, width=width, hp=hp, armor=armor, damage=damage, attack_range=attack_range, attack_cooldown=attack_cooldown, speed=speed)

    def __repr__(self):
        return f"<Knight id={self.id} owner={self.owner} pos={self.position} hp={self.hp}>"
