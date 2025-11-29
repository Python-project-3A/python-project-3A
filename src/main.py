import argparse

from src.cli.cli import CLIVisualizer
from src.engine.battlefield import Battlefield
from src.engine.simulation import Simulation
from src.general.braindead import GeneralBraindead
from src.general.daft import GeneralDaft
from src.units.pikeman import Pikeman


# --- gestion des arguments ---------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="AoE-like RTS simulation CLI")

    parser.add_argument("--width", type=int, default=40, help="Largeur de la map")
    parser.add_argument("--height", type=int, default=20, help="Hauteur de la map")
    parser.add_argument("--ticks", type=int, default=500, help="Nombre de ticks max")
    parser.add_argument("--speed", type=float, default=0.1, help="Durée entre ticks (secondes)")
    parser.add_argument("--no-visual", action="store_true", help="Désactive l'affichage CLI")

    # Général arguments
    parser.add_argument("--general0", type=str, default="daft", choices=["braindead", "daft"], help="Type de général pour le joueur 0")
    parser.add_argument("--general1", type=str, default="braindead", choices=["braindead", "daft"], help="Type de général pour le joueur 1")

    # Army size
    parser.add_argument("--units", type=int, default=10, help="Nombre d'unités par équipe")

    return parser.parse_args()


def create_general(general_type: str, player_id: int):
    """Factory pour créer un général selon son type"""
    if general_type == "braindead":
        return GeneralBraindead(player_id)
    elif general_type == "daft":
        return GeneralDaft(player_id)
    else:
        raise ValueError(f"Type de général inconnu: {general_type}")


def spawn_army(battlefield, owner: int, num_units: int, start_x: float, start_y: float):
    """Spawn une armée pour un joueur"""
    for i in range(num_units):
        # Disposition en colonne
        x = start_x
        y = start_y + (i * 1.5)  # Espacement vertical

        # Factory pour créer l'unité
        def make_pikeman():
            return Pikeman(owner=owner, x=x, y=y)

        battlefield.spawn_unit(make_pikeman, x, y, owner=owner)


def print_battle_result(battlefield):
    """Affiche le résultat de la bataille"""
    print("\n" + "=" * 60)
    print("=== RÉSULTAT DE LA BATAILLE ===")
    print("=" * 60)

    # Compter les survivants par équipe
    survivors_by_owner = {}
    for unit in battlefield.get_all_units():
        if unit.is_alive():
            if unit.owner not in survivors_by_owner:
                survivors_by_owner[unit.owner] = []
            survivors_by_owner[unit.owner].append(unit)

    # Afficher les stats
    for owner_id in [0, 1]:
        general = battlefield.generals[owner_id]
        survivors = survivors_by_owner.get(owner_id, [])

        print(f"\n🎖️  {general.name} (Joueur {owner_id}):")
        print(f"   Survivants: {len(survivors)} unités")

        if survivors:
            total_hp = sum(u.hp for u in survivors)
            avg_hp = total_hp / len(survivors)
            print(f"   HP total: {total_hp:.1f}")
            print(f"   HP moyen: {avg_hp:.1f}")

    # Déterminer le vainqueur
    print("\n" + "-" * 60)
    if len(survivors_by_owner) == 0:
        print("⚔️  MATCH NUL - Toutes les unités sont mortes!")
    elif len(survivors_by_owner) == 1:
        winner_id = list(survivors_by_owner.keys())[0]
        winner_general = battlefield.generals[winner_id]
        print(f"🏆  VICTOIRE pour {winner_general.name} (Joueur {winner_id})!")
    else:
        # Les deux ont des survivants, celui avec le plus gagne
        counts = {owner: len(units) for owner, units in survivors_by_owner.items()}
        winner_id = max(counts, key=counts.get)
        winner_general = battlefield.generals[winner_id]
        print(f"🏆  VICTOIRE TACTIQUE pour {winner_general.name} (Joueur {winner_id})!")

    print("=" * 60 + "\n")


# --- MAIN ----------------------------------------------------------
def main():
    args = parse_args()

    print("=" * 60)
    print("=== DÉMARRAGE SIMULATION ===")
    print("=" * 60)

    # Créer le battlefield
    bf = Battlefield(args.width, args.height)

    # Créer les généraux
    general_0 = create_general(args.general0, player_id=0)
    general_1 = create_general(args.general1, player_id=1)

    bf.generals = [general_0, general_1]

    print(f"\n⚔️  Bataille: {general_0.name} VS {general_1.name}")
    print(f"📍 Carte: {args.width}x{args.height}")
    print(f"👥 Armées: {args.units} unités par équipe")
    print(f"⏱️  Vitesse: {args.speed}s par tick\n")

    # Spawn les armées
    # Équipe 0 à gauche
    spawn_army(bf, owner=0, num_units=args.units, start_x=5.0, start_y=5.0)

    # Équipe 1 à droite
    spawn_army(bf, owner=1, num_units=args.units, start_x=args.width - 10.0, start_y=5.0)

    # Créer le visualizer
    visualizer = None
    if not args.no_visual:
        visualizer = CLIVisualizer(args.width, args.height)

    # Créer et lancer la simulation
    sim = Simulation(game_map=bf.game_map, generals=bf.generals, battlefield=bf, tick_duration=args.speed)

    print("🎬 Début de la bataille...\n")
    sim.run(max_ticks=args.ticks, visualizer=visualizer)

    # Afficher le résultat
    print_battle_result(bf)

    # Snapshot final (optionnel, pour debug)
    if args.no_visual:
        print("\n=== SNAPSHOT FINALE (DEBUG) ===")
        snapshot = bf.snapshot()
        print(f"Unités restantes: {len(snapshot['units'])}")
        for u in snapshot["units"]:
            if u["hp"] > 0:
                print(f"  - {u['type']} #{u['id']} (owner={u['owner']}): {u['hp']} HP à {u['position']}")


if __name__ == "__main__":
    main()

# Commandes de test:
# python -m src.main --ticks 500 --general0 daft --general1 braindead
# python -m src.main --ticks 500 --general0 braindead --general1 braindead --units 15
# python -m src.main --ticks 1000 --general0 daft --general1 daft --no-visual
