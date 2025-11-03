# src/ia-general/daft.py

from .base_general import BaseGeneral
# ↑ On importe la classe de base qu’on a faite dans base-general.py
#   Ça permet d’hériter de toute la structure commune.

class MajorDaft(BaseGeneral):
    """
    LOGIQUE DE L'IA "MAJOR DAFT":
    IA "simple" : toutes les unités attaquent l'ennemi le plus proche.
    Si aucune cible n'est dans le viseur, elles restent immobiles.
    """

    def decide(self, game_state):
        """
        Cette fonction est appelée à chaque tour par le moteur du jeu.
        Elle renvoie une liste d'ordres : (unité, action, cible)
        """
        orders = []
        # On prépare une liste vide qui contiendra les ordres pour toutes les unités.

        enemies = game_state.get_all_enemies(self.player_id)
        # On récupère la liste de toutes les unités ennemies sur la carte.
        # Cette fonction doit être définie dans le moteur (comme pour Braindead).
        
        if not enemies:
            # Si aucun ennemi n'existe (ex : partie terminée), on ne fait rien.
            return []

        for unit in self.army.units:
            # On parcourt chaque unité de l’armée commandée par DAFT.

            # On choisit ici la cible la plus proche.
            # Cela suppose que chaque unité possède une méthode distance_to(autre_unité)
            target = min(enemies, key=lambda e: unit.distance_to(e))
            # `min(..., key=...)` renvoie l'élément qui minimise la distance.
            # Donc : on choisit l'ennemi le plus proche comme cible.

            # On ajoute l’ordre "attaque cette cible"
            orders.append((unit, "attack", target))
            # Dans le moteur, cet ordre sera interprété comme "va vers l'ennemi et attaque-le".

        return orders
        # On renvoie la liste complète des ordres.
