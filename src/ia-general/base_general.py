from abc import ABC, abstractmethod
# ↑ On importe des outils du module `abc` ("Abstract Base Classes").
#   - ABC : base pour déclarer une classe abstraite (on ne l'instancie pas directement).
#   - abstractmethod : décorateur pour forcer l'implémentation d'une méthode par les sous-classes.

class BaseGeneral(ABC):
    """
    Classe de base pour toutes les IA (les "généraux").
    On écrit ici le contrat que toutes les IA doivent respecter.
    """

    def __init__(self, player_id, army, game_map):
        # constructeur : appelé quand on crée une instance d'une IA.
        # player_id : identifiant du joueur (int ou str), permet de savoir "qui" commande.
        # army : objet représentant l'armée (doit contenir la liste des unités).
        # game_map : référence à la carte / map pour que l'IA puisse la consulter si besoin.
        self.player_id = player_id
        # on conserve l'id du joueur dans l'objet (utile pour filtrer ennemis/alliés)
        self.army = army
        # on conserve l'armée (typiquement, army.units est la liste des unités)
        self.map = game_map
        # on conserve la carte (peut fournir info d'élévation, obstacles, etc.)

    @abstractmethod
    def decide(self, game_state):
        """
        Méthode abstraite — doit être implémentée par chaque IA concrète.
        - game_state : objet qui résume l'état actuel de la simulation (unités,
          positions, temps, etc.)
        Retour attendu : une liste d'ordres. Chaque ordre est typiquement un tuple
        (unit, action, target) — exemple : (knight_1, 'attack', enemy_unit_5)
        """
        pass
        # Le `pass` n'est là que pour la forme ; python exige un corps.
        # Mais comme la méthode est décorée par @abstractmethod, toute classe
        # fille devra la redéfinir, sinon Python empêchera l'instanciation.
