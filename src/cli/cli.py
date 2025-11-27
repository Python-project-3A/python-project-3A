# src/cli/cli.py
import sys


class CLIVisualizer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.first_frame = True
        self.lines_printed = 0

    def render(self, battlefield, tick):
        # Effacer la frame précédente & remonter le curseur dans le terminal
        if not self.first_frame:
            sys.stdout.write(f"\033[{self.lines_printed}A")  # "\033[" = caractère d’échappement, A = curseur vers le haut -> pour réécrire sur la frame precedente
        else:
            self.first_frame = False

        # Construire la grille vide
        grille = [["." for _ in range(self.width)] for _ in range(self.height)]

        # récupérer les unités depuis le Battlefield
        # arrondir leur position flottante
        for unit in battlefield.get_all_units():
            if not unit.is_alive():
                continue

            x = int(unit.position[0])
            y = int(unit.position[1])

            # les afficher avec des symboles :
            if 0 <= x < self.width and 0 <= y < self.height:
                symbol = unit.name[0].upper()
                if unit.owner == 0:
                    symbol = f"\033[34m{symbol}\033[0m"  # bleu joueur 0
                if unit.owner == 1:
                    symbol = f"\033[91m{symbol}\033[0m"  # Rouge joueur 1

                if grille[y][x] == ".":
                    grille[y][x] = symbol
                else:
                    grille[y][x] = "*"

        # Affichage
        print(f"=== TICK {tick} ===")
        for ligne in grille:
            print(" ".join(ligne))  # .join concatenne une liste de chaînes de caractères en une seule chaîne.

        sys.stdout.flush()  # flush() = vider le tampon immédiatement => pas de retard => affichage rapide
        self.lines_printed = 1 + self.height  # Nombre de lignes affichées

    def finish(self):
        # Remonter à la fin proprement
        sys.stdout.write(f"\033[{self.lines_printed}B")
        sys.stdout.flush()
