class Unit : 
    def __init__(self,name,team,x,y,hp,armor,damage,attack_range,attack_cooldown,speed):
        self.name = name 
        self.team = team
        self.x = x
        self.y = y
        self.hp = hp
        self.armor = armor
        self.damage = damage
        self.attack_range = attack_range
        self.attack_cooldown = attack_cooldown
        self.speed = speed

    def is_alive(self):
        return self.hp > 0
    
    def take_damage(self, attack_damage):
        take = max(0, attack_damage - self.armor)
        self.hp -= take
        if not self.is_alive():
            pass



class Crossbowman(Unit):
    def __init__(self,team,x,y):
        super().__init__(
            name="Crossbowman",
            team=team,
            x=x,
            y=y,
            hp=35,
            armor=0,
            damage=5,
            attack_range=5,
            attack_cooldown=2,
            speed=0.96,
        )

class Knight(Unit):
    def __init__(self,team,x,y):
        super().__init__(
            name="Knight",
            team=team,
            x=x,
            y=y,
            hp=100,
            armor=2,
            damage=10,
            attack_range=0,
            attack_cooldown=1.8,
            speed=1.35,
        )

class Pikeman(Unit):
    def __init__(self,team,x,y):
        super().__init__(
            name="Pikeman",
            team=team,
            x=x,
            y=y,
            hp=55,
            armor=0,
            damage=4,
            attack_range=0,
            attack_cooldown=3,
            speed=1,
        )