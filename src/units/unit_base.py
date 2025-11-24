import math
import time

class Unit : 
    def __init__(self,name,team,x,y,height,width,hp,armor,damage,attack_range,
                 attack_cooldown,speed):
        self.name = name 
        self.team = team
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        self.hp = hp
        self.armor = armor
        self.damage = damage
        self.attack_range = attack_range
        self.attack_cooldown = attack_cooldown
        self.speed = speed
        self.time_since_last_attack = 0.0

    def is_alive(self):
        """return True si l'unité est encore en vie """
        return self.hp > 0
    
    def take_damage(self, attack_damage):   

        """ -calcul les degats subis apres une attaque 
            -les soustrais aux hp
            -indique si la troupe est encore en vie apres l'attaque """
        
        take = max(0, attack_damage - self.armor)
        self.hp -= take
        if not self.is_alive():
            pass

    def to_dict(self):
        """
        retourne un dictionnaire qui associe chaque nom d'attribut à sa valeur actuelle
        peut être utile pour le save/load et la partie statistique plus tard
        """
        return {
            "name": self.name,
            "team": self.team,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "hp": self.hp,
            "armor": self.armor,
            "damage": self.damage,
            "attack_range": self.attack_range,
            "attack_cooldown": self.attack_cooldown,
            "speed": self.speed,
        }

    def dist_to(self, other: "Unit") -> float:
        """
        calcule et retourne la distance entre les centres de deux unités
        je pense que l'utilité est évidente
        """
        return math.dist((self.x, self.y), (other.x, other.y))


    def edge_dist_to(self, other: "Unit") -> float:
        """
        différent de dist_to, retourne la différence de la distance entre les centres de
        deux unités et la somme de leur rayons
        nécessaire pour déterminer si l'unité cible est dans l'attack range étant donné
        que ce dernier commence à partir du rayon de l'unité et non pas de son centre
        """
        center_dist = self.dist_to(other)
        self_radius = 0.5 * math.hypot(self.width, self.height)
        target_radius = 0.5 * math.hypot(other.width, other.height)
        return max(0.0, center_dist - (self_radius + target_radius))

    def move_towards(self, target: "Unit", dt: float) -> bool:
        """
        déplace l'unité d'un pas vers l'unité cible
        dépend de la vitesse de notre unité et du temps passé (dt)
        dt: secondes par tick
        retourne True si l'unité cible est dans notre attack_range
        retourne False sinon
        """
        edge_dist = self.edge_dist_to(target)

        if edge_dist <= self.attack_range or self.speed <= 0 or dt <= 0:
            return True
        
        dist = self.dist_to(target)
        if dist == 0:
            return True
        
        step = min(self.speed * dt, edge_dist)
        if step <= 0:
            return True
        
        dx = target.x - self.x
        dy = target.y - self.y
        self.x +=  dx / dist * step
        self.y += dy / dist * step
        return False
    
    def move_to(self, x: float, y: float, dt: float) -> bool:
        """
        déplace l'unité d'un pas vers une position (x, y)
        mêmes spécifications que move_towards
        """
        dist = math.dist((self.x, self.y), (x, y))
        
        step = min(self.speed * dt, dist)
        if step <= 0:
            return True
        
        dx = x - self.x
        dy = y - self.y
        self.x +=  dx / dist * step
        self.y += dy / dist * step
        return False

    def can_attack(self, other: "Unit") -> bool:
        """
        vérifie si les deux unités sont assez proches (selon attack range) 
        pour que l'une des unité puisse attaquer (self)
        """
        if(self.edge_dist_to(other)<=self.attack_range):
            return True
        else:
            return False

    def attack(self, other: "Unit"):
        """
        Attaque une unité si elle est à portée et que le cooldown est terminé.
        Modifie la vie de la cible et met à jour le temps de la dernière attaque.
        """
        current_time=time.time()

        if not self.can_attack(other):
            return False
        
        if current_time-self.time_since_last_attack <= self.attack_cooldown:
            return False
        
        damage=max(0,self.damage - other.armor)
        other.hp -= damage
        other.hp = max(0,other.hp) #pour ne pas avoir d'hp < 0


        self.time_since_last_attack = current_time
        
        return True
    
    def choose_target(self, enemies):
        living_enemies = [e for e in enemies if e.is_alive()]
        if not living_enemies:
            return None
        return min(living_enemies, key=lambda e: self.distance_to(e))
