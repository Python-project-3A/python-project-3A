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
        return

    def move_towards(self, target: "Unit", dt: float) -> bool:
        """
        un peu compliqué, déplace l'unité vers les coordonnées de l'unité cible
        dépend de la vitesse de notre unité et du temps passé (dt)
        dt: secondes par tick (vu que c'est pas un mouvement instantané)
        retourne True si l'unité atteint la position cible (diff de 1 entre les x et y)
        retourne False sinon
        """
        return

    def can_attack(self, other: "Unit") -> bool:
        """
        vérifie si les deux unités sont assez proches (selon attack range) pour attaquer
        """
        return

    def attack(self, other: "Unit"):
        """
        attaquer une unité si on est assez proche
        faut se rappeler qu'on un un délai entre les attaques (attack_cooldown)
        modifie l'attribut time_since_last_attack
        """
        return
    
    def choose_target(self, enemies):
        living_enemies = [e for e in enemies if e.is_alive()]
        if not living_enemies:
            return None
        return min(living_enemies, key=lambda e: self.distance_to(e))
