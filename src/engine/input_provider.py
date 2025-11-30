# src/utils/input_provider.py
import sys
import os

# Détection OS
if os.name == "nt":
    import msvcrt
else:
    import select
    import tty
    import termios


class ConsoleInputProvider:
    """
    Gère les entrées clavier de manière non bloquante et Cross-Platform.
    Utilise le protocole Context Manager (with ...) pour nettoyer le terminal Linux automatiquement.
    """

    def __init__(self):
        self.os_type = os.name
        self.old_settings = None

    def __enter__(self):
        """Appelé quand on fait 'with provider:'"""
        if self.os_type != "nt":
            try:
                self.fd = sys.stdin.fileno()
                self.old_settings = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)
            except termios.error:
                pass  # Probablement pas un vrai terminal (IDE, Pipe)
        return self

    def __exit__(self, type, value, traceback):
        """Appelé automatiquement à la fin, même en cas de crash."""
        if self.os_type != "nt" and self.old_settings:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def get_key(self):
        """Renvoie la touche pressée ou None."""
        if self.os_type == "nt":
            if msvcrt.kbhit():
                try:
                    return msvcrt.getch().decode().lower()
                except UnicodeDecodeError:
                    return None
        else:
            # Linux / Mac
            # Vérifie si des données sont prêtes à être lues sur l'entrée standard (fd 0)
            # Un timeout de 0 signifie une vérification non bloquante
            dr, dw, de = select.select([sys.stdin], [], [], 0)
            if dr:
                return sys.stdin.read(1).lower()
        return None
