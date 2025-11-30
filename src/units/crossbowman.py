from unit_base import Unit


class Crossbowman(Unit):
    def __init__(self, team, x, y):
        super().__init__(name="Crossbowman", team=team, x=x, y=y, r=0.5, hp=35, armor=0, damage=5, attack_range=5, attack_cooldown=2, speed=0.96)
