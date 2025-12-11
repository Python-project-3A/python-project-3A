# src/utils/input_provider.py
import sys
import os

# NE PAS ESSAYER DE GERER les "is not defined" => Normal car ils sont dans un else et python les importe ssi nécessaire. NE BUG PAS.

# Détection OS
if os.name == "nt":
    import msvcrt
else:
    import select
    import tty
    import termios
    import fcntl


# Codes des touches F11 et F12 pour différents environnements
# MSVCRT (Windows)
WINDOWS_F11_CODE = b"\x85"  # 133
WINDOWS_F12_CODE = b"\x86"  # 134

# Séquences XTERM/Linux (les plus courantes)
UNIX_F11_SEQUENCE = "\x1b[23~"
UNIX_F12_SEQUENCE = "\x1b[24~"


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

    # src/utils/input_provider.py (Mise à jour de la méthode get_key)

    def get_key(self):
        """Renvoie la touche pressée ou None."""
        if self.os_type == "nt":
            if msvcrt.kbhit():
                key = msvcrt.getch()

                # \x00 (0) ou \xe0 (224) indiquent le début d'une touche spéciale
                if key in (b"\x00", b"\xe0"):
                    # Lire le deuxième octet (le code étendu)
                    extended_key = msvcrt.getch()

                    if extended_key == WINDOWS_F11_CODE:
                        return "F11"
                    if extended_key == WINDOWS_F12_CODE:
                        return "F12"

                    # On ignore toutes les autres touches spéciales (flèches, autres F-keys)
                    return None
                else:
                    # Caractère simple
                    try:
                        # Ajout : Gérer la touche ESC sur Windows si elle est lue comme un caractère simple
                        if key == b"\x1b":
                            return "esc"
                        return key.decode().lower()
                    except UnicodeDecodeError:
                        return None
            return None
        else:
            # Linux / Mac
            # Vérifie si des données sont prêtes à être lues sur l'entrée standard (fd 0)
            # Un timeout de 0 signifie une vérification non bloquante
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                char = sys.stdin.read(1)

                if char == "\x1b":  # Début d'une séquence
                    # Logique pour lire la séquence complète SANS bloquer le terminal.
                    fd = sys.stdin.fileno()
                    old_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_fl | os.O_NONBLOCK)

                    # Lecture des octets restants (max 5)
                    rest = ""
                    try:
                        rest = sys.stdin.read(5)
                    except BlockingIOError:
                        pass

                    # Rétablit le mode bloquant par défaut
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_fl)

                    sequence = char + rest

                    if sequence == UNIX_F11_SEQUENCE:
                        return "F11"
                    elif sequence == UNIX_F12_SEQUENCE:
                        return "F12"

                    # NOUVELLE LOGIQUE POUR GÉRER L'ESCAPE SIMPLE :
                    # Si la séquence est uniquement '\x1b', cela signifie que l'utilisateur
                    # a appuyé sur ESC et que ce n'était pas le début d'une séquence F-key.
                    if sequence == "\x1b":
                        return "esc"

                    # Si c'est une autre séquence (Flèches, F-keys non mappés), on retourne simplement None
                    return None

                # Caractère simple
                return char.lower()
            return None
