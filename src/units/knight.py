from unit_base import Unit


class Knight(Unit):
    def __init__(self,team,x,y):
        super().__init__(
            name="Knight",
            team=team,
            x=x,
            y=y,
            width=1,
            height=2,
            hp=100,
            armor=2,
            damage=10,
            attack_range=0,
            attack_cooldown=1.8,
            speed=1.35,
        )