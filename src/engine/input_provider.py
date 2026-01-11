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
WINDOWS_F9_CODE = b"\x83"
WINDOWS_F11_CODE = b"\x85"
WINDOWS_F12_CODE = b"\x86"

# Séquences XTERM/Linux
UNIX_F9_SEQUENCE = "\x1b[20~"
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
        self.last_key_was_shifted = False  # Track if last key press had shift

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

    def is_shift_pressed(self):
        """
        Terminal mode doesn't easily detect shift state.
        """
        return self.last_key_was_shifted

    def get_key(self):
        """Renvoie la touche pressée ou None."""
        # Reset shift state by default
        self.last_key_was_shifted = False

        if self.os_type == "nt":
            if msvcrt.kbhit():
                key = msvcrt.getch()

                # \x00 (0) ou \xe0 (224) indiquent le début d'une touche spéciale
                if key in (b"\x00", b"\xe0"):
                    # Lire le deuxième octet (le code étendu)
                    extended_key = msvcrt.getch()

                    if extended_key == WINDOWS_F9_CODE:
                        return "F9"
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
                            return "escape"
                        decoded = key.decode()

                        # Check if uppercase letter (indicates Shift was pressed)
                        if decoded.isupper() and decoded.isalpha():
                            self.last_key_was_shifted = True

                        return decoded.lower()
                    except UnicodeDecodeError:
                        return None
            return None
        else:
            # Linux / Mac
            # Vérifie si des données sont prêtes à être lues sur l'entrée standard (fd 0), un timeout de 0 signifie une vérification non bloquante
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                char = sys.stdin.read(1)

                if char == "\t":
                    return "tab"

                if char == "\x1b":  # Début d'une séquence
                    fd = sys.stdin.fileno()
                    old_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_fl | os.O_NONBLOCK)

                    # Petit délai pour recevoir la séquence complète
                    import time

                    time.sleep(0.02)

                    rest = ""
                    try:
                        rest = sys.stdin.read(10)  # Buffer augmenté
                    except BlockingIOError:
                        pass

                    fcntl.fcntl(fd, fcntl.F_SETFL, old_fl)

                    sequence = char + rest

                    if sequence == UNIX_F9_SEQUENCE:
                        return "F9"
                    if sequence == UNIX_F11_SEQUENCE:
                        return "F11"
                    elif sequence == UNIX_F12_SEQUENCE:
                        return "F12"
                    elif sequence == "\x1b":
                        return "escape"

                    # Autres séquences ignorées
                    return None

                # Caractère simple - check if uppercase (Shift pressed)
                if char.isupper() and char.isalpha():
                    self.last_key_was_shifted = True

                # Caractère simple
                return char.lower()
            return None
