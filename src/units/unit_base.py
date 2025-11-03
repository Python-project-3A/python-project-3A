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
        self.time_since_attack = 0.0

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

    """
    retourne un dictionnaire qui associe chaque nom d'attribut à sa valeur actuelle
    peut être utile pour le save/load et la partie statistique plus tard
    """
    def to_dict(self):
        return

    """
    calcule et retourne la distance entre deux unités
    je pense que l'utilité est évidente
    """
    def dist_to(self, other: "Unit") -> float:
        return

    """
    un peu compliqué, déplace l'unité vers les coordonnées de l'unité cible
    dépend de la vitesse de notre unité et du temps passé (dt)
    dt: secondes par tick (vu que c'est pas un mouvement instantané)
    retourne True si l'unité atteint la position cible (différence de 1 entre les x et y)
    retourne False sinon
    """
    def move_towards(self, target_x: int, target_y: int, dt: float) -> bool:
        return

    """
    vérifie si les deux unités sont assez proches (donc dans l'attack range) pour attaquer
    """
    def can_attack(self, other: "Unit") -> bool:
        return

    """
    attaquer une unité si on est assez proche
    faut se rappeler qu'on un un délai entre les attaques (attack_cooldown)
    modifie l'attribut time_since_last_attack
    """
    def attack(self, other: "Unit"):
        return