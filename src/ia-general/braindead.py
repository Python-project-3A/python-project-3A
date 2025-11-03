from .base_general import BaseGeneral 
# ↑ On importe la classe de base définie dans .base_general.

class CaptainBraindead(BaseGeneral):
    """
    LOGIQUE DE L'IA "CAPTAIN BRAINDEAD":
    la classe CaptainBraindead hérite de la classe mère BaseGeneral.
    C'est une IA dite "minimale/basique" : chaque unité attaque si elle voit un ennemi dans son
    champ de vision, sinon elle reste inactive.      
    """

    def decide(self, game_state):
        # Méthode appelée par le moteur à chaque tour.
        # Elle doit renvoyer une liste d'ordres.
        orders = []
        # on crée une liste vide qui contiendra les ordres à retourner à la fin.
        for unit in self.army.units:
            # Pour chaque unité de l'armée contrôlée par ce général.
            # On suppose que `self.army.units` est une liste d'objets unité.
            visible_enemies = game_state.get_visible_enemies(unit)
            # On demande au game_state la liste des ennemis visibles par cette unité.
            # -> visible_enemies doit être une liste (possiblement vide).
            if visible_enemies:
                # Si la liste n'est pas vide, l'unité voit au moins un ennemi.
                target = visible_enemies[0]
                # Ici on choisit **simplement** le premier ennemi visible comme cible.
                # On pourrait choisir le plus proche, le plus faible, etc. (amélioration possible pour plus tard).
                orders.append((unit, "attack", target))
                # On ajoute à la liste d'ordres : attaquer cette cible.
            else:
                # Aucun ennemi visible → aucune action agressive.
                orders.append((unit, "idle", None))
                # "idle" signifie rester sur place et ne rien faire.
        return orders
        # On renvoie tous les ordres pour ce tour.
