import sys

import pygame

from src.engine.battlefield import Battlefield
from src.map.game_map import GameMap
from src.units.unit_base import Unit

class PygameVisualizer:
    def __init__(self, width: int, height: int, tile_size: int = 32):
        pygame.init()

        self.tile_size = tile_size
        self.screen_width = width * self.tile_size
        self.screen_height = height * self.tile_size
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Age of Empires 2 - Simulation")
        self.clock = pygame.time.Clock()
        self.running = True
    
    def get_key(self):
        """
        Gère TOUS les événements Pygame une seule fois par tick.
        Renvoie 'p' ou 'q' si ces touches sont pressées.
        Met self.running à False si la fenêtre est fermée.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    return "p"
                if event.key == pygame.K_q:
                    self.running = False # On veut que 'q' quitte immédiatement
                    return "q"
        return None

    def render(self, battlefield: Battlefield, tick_count: int):
        """
        Dessine l'état actuel du champ de bataille
        Cette méthode sera appelée à chaque tick de la simulation
        """
        if not self.running:
            return
        
        # 1. Remplir l'arrière-plan
        self.screen.fill((0, 0, 0)) # Noir

        # 2. Dessiner la carte
        self._draw_map(battlefield.game_map)

        # 3. Dessiner les unités
        self._draw_units(battlefield.get_all_units())

        # 4. Mettre à jour l'affichage
        pygame.display.flip()
        self.clock.tick(30)

    def _draw_map(self, game_map: GameMap):
        """Dessine les tuiles de la carte"""
        for x in range(game_map.width):
            for y in range(game_map.height):
                # Pour l'instant, on dessine juste des carrés de couleur
                color = (34, 139, 34) # Vert pour l'herbe
                pygame.draw.rect(self.screen, color, (x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size))
    
    def _draw_units(self, units: list[Unit]):
        """Dessine toutes les unités"""
        for unit in units:
            if unit.is_alive():
                # Dessiner un cercle pour chaque unité
                center_x = int(unit.position[0] * self.tile_size + self.tile_size / 2)
                center_y = int(unit.position[1] * self.tile_size + self.tile_size / 2)

                # Couleur différente selon le propriétaire de l'unité
                if unit.owner == 0:
                    color = (255, 0, 0) # Rouge
                else:
                    color = (0, 0, 255) # Bleu

                pygame.draw.circle(self.screen, color, (center_x, center_y), int(self.tile_size / 3))
    
    def finish(self):
        """Nettoie Pygame à la fin de la simulation"""
        pygame.quit()
        # sys.exit() est un peu brutal, on le retire pour laisser le programme se terminer proprement.