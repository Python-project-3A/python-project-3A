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

