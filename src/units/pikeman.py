from src.units.unit_base import Unit


class Pikeman(Unit):
    def __init__(self, team, x, y):
        super().__init__(name="Pikeman", team=team, x=x, y=y, r=0.5, hp=55, armor=0, damage=4, attack_range=0, attack_cooldown=3, speed=1)
