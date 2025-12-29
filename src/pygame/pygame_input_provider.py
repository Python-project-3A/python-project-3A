import pygame


class PygameInputProvider:
    def __init__(self):
        """Initialise le provider sans démarrer pygame."""
        self.pygame_initialized = False

    def __enter__(self):
        """Appelé quand on fait 'with provider:'"""
        if not pygame.get_init():
            pygame.init()
            # Enable key repeat: (delay_ms, interval_ms)
            pygame.key.set_repeat(500, 50)
            self.pygame_initialized = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Appelé automatiquement à la fin, même en cas de crash."""
        if self.pygame_initialized:
            pygame.quit()
            self.pygame_initialized = False

    def get_key(self):
        """
        Processes Pygame events to get user input.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "escape"
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    return "zoom_in"
                elif event.y < 0:
                    return "zoom_out"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "escape"
                # Camera Movement Keys
                if event.key in (pygame.K_w, pygame.K_z):
                    return "w"  # z for AZERTY
                if event.key == pygame.K_s:
                    return "s"
                if event.key in (pygame.K_a, pygame.K_q):
                    return "a"  # q for AZERTY
                if event.key == pygame.K_d:
                    return "d"

                # Simulation Control Keys
                if event.key == pygame.K_p:
                    return "p"
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                    return "="
                if event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS or event.key == pygame.K_6:
                    return "-"
                if event.key == pygame.K_r:
                    return "r"
                if event.key == pygame.K_TAB:
                    return "tab"
                if event.key == pygame.K_F11:
                    return "F11"
                if event.key == pygame.K_F12:
                    return "F12"

        return None
