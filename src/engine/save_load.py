from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.simulation import Simulation
    from src.engine.battlefield import Battlefield
    from src.units.unit_base import Unit
    from src.general.general_base import BaseGeneral

from src.units.unit_base import Unit
from src.scenarios.scenario_loader import ScenarioLoader  # Pour la factory d'unité
from src.general.braindead import GeneralBraindead
from src.general.daft import GeneralDaft

# Liste des classes de généraux
GENERAL_CLASSES = {
    "GeneralBraindead": GeneralBraindead,
    "GeneralDaft": GeneralDaft,
    # Ajoutez d'autres classes de généraux ici
}


def get_save_dir() -> Path:
    """Retourne le dossier où les sauvegardes sont stockées."""
    return Path(__file__).parent.parent / "data" / "saves"


# --- serialisation/désérialisation des unités ---


def serialize_order(order: dict | None) -> dict | None:
    """Convertit un ordre (Unit/Position) en format sérialisable (ID/Position)."""
    if not order:
        return None

    # L'ordre 'attack_unit' contient une référence à une Unit, que l'on remplace par son id.
    if order["type"] == "attack_unit" or order["type"] == "pathing_attack_unit":
        if hasattr(order["target"], "id"):
            return {"type": order["type"], "target_id": order["target"].id}
        else:
            # Si la cible est invalide au moment de la sauvegarde, on clear l'ordre
            return None

    # 'move_to' et 'attack_move' ont une position sérialisable.
    return order


def deserialize_order(data: dict, battlefield: Battlefield) -> dict | None:
    """Convertit un ordre sérialisé (id/Position) en format utilisable (Unit/Position)."""
    if not data:
        return None

    order_type = data["type"]

    if order_type == "attack_unit" or order_type == "pathing_attack_unit":
        target_id = data.get("target_id")
        target_unit = battlefield.find_unit(target_id)
        if target_unit:
            return {"type": order_type, "target": target_unit}
        else:
            # La cible n'existe plus (morte ou retirée)
            return None

    # 'move_to' et 'attack_move' n'ont pas de changements (juste la position)
    if order_type == "move_to" or order_type == "attack_move":
        return data.copy()

    return None


def serialize_unit(unit: Unit) -> dict:
    """Sérialise une unité en dictionnaire JSON."""
    data = unit.to_dict()  # Utilise la méthode to_dict() existante

    # Ajout des données de l'unité spécifiques à la simulation
    data["id"] = unit.id
    data["reload_timer"] = unit.reload_timer

    # L'ordre doit être sérialisé pour remplacer l'objet 'Unit' par son 'ID'
    data["current_order"] = serialize_order(unit.current_order)

    # Les stats dynamiquement ajoutées (damage_cavalry, armor_pierce, etc.)
    # ne sont pas sérialisées car elles seront restaurées par ScenarioLoader.create_unit_from_stats

    return data


def deserialize_unit(data: dict, battlefield: Battlefield) -> Unit:
    """Désérialise une unité à partir des données JSON."""

    # 1. Recréer l'unité avec toutes ses stats (y compris les stats dynamiques)
    # On utilise la méthode du ScenarioLoader pour être sûr de récupérer toutes les propriétés
    unit = ScenarioLoader.create_unit_from_stats(unit_type=data["name"], owner=data["owner"], x=data["position"][0], y=data["position"][1])

    # 2. Restaurer l'état dynamique de l'unité
    unit.id = data["id"]
    unit.position = tuple(data["position"])
    unit.hp = data["hp"]
    unit.reload_timer = data["reload_timer"]

    # On ajoute l'unité au Battlefield avant de désérialiser l'ordre
    # car l'ordre pourrait faire référence à cette même unité si elle se cible elle-même
    battlefield.add_existing_unit(unit)

    # 3. Restaurer l'ordre (doit se faire après avoir ajouté les unités au battlefield)
    unit.current_order = deserialize_order(data.get("current_order"), battlefield)

    return unit


# --- sérialisation/désérialisation des généraux ---


def serialize_general(general: BaseGeneral) -> dict:
    """Sérialise un général."""
    return general.to_dict()


def deserialize_general(data: dict) -> BaseGeneral:
    """Désérialise un général ."""
    general_class = GENERAL_CLASSES.get(data["class"])
    if not general_class:
        raise ValueError(f"Unknown general class: {data['class']}")

    general = general_class(data["player_id"])
    general.name = data["name"]

    return general


# --- sérialisation/désérialisation du battlefield et de la simulation ---


def serialize_simulation(simulation: Simulation) -> dict:
    """Sérialise l'état complet du jeu."""

    battlefield_data = {"width": simulation.battlefield.width, "height": simulation.battlefield.height, "next_unit_id": simulation.battlefield.next_unit_id, "units": [serialize_unit(u) for u in simulation.battlefield.get_all_units()]}

    return {"battlefield": battlefield_data, "simulation": simulation.to_dict(), "format_version": 1}


def deserialize_simulation(data: dict) -> Simulation:
    """Désérialise l'état complet du jeu et retourne un objet Simulation."""
    from src.engine.simulation import Simulation
    from src.map.game_map import GameMap
    from src.engine.battlefield import Battlefield

    # 1. Désérialisation du Battlefield (sans les unités pour l'instant)
    bf_data = data["battlefield"]
    width = bf_data["width"]
    height = bf_data["height"]

    # La GameMap est recréée car elle n'a pas d'état complexe qui doit être sérialisé ici
    game_map = GameMap(width, height)
    game_map.init_map()  # Nécessaire pour initialiser les tuiles

    battlefield = Battlefield(width, height)
    battlefield.game_map = game_map
    battlefield.next_unit_id = bf_data["next_unit_id"]

    # 2. Désérialisation des Généraux (qui seront assignés au Battlefield et à la Simulation)
    generals = [deserialize_general(g) for g in data["simulation"]["generals"]]
    battlefield.generals = generals

    # 3. Création de l'objet Simulation
    sim_data = data["simulation"]
    simulation = Simulation(game_map, generals, battlefield)
    simulation.tick_count = sim_data["tick_count"]

    # 4. Désérialisation des Unités (DOIT se faire APRÈS la création du Battlefield/Simulation)
    for unit_data in bf_data["units"]:
        # La fonction de désérialisation ajoute l'unité au battlefield
        deserialize_unit(unit_data, battlefield)

    return simulation


# --- fonctions de sauvegarde et chargement ---


def save_game(simulation: Simulation):
    """
    Sauvegarde l'état actuel de la simulation dans un fichier JSON.
    Le nom du fichier est généré avec un horodatage (save_YYYYMMDD_HHMMSS.json).
    """

    # Générer l'horodatage
    now = datetime.datetime.now()
    # Format: YYYYMMDD_HHMMSS
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    filename = f"save_{timestamp}.json"

    save_dir = get_save_dir()
    save_dir.mkdir(parents=True, exist_ok=True)  # Créer le dossier s'il n'existe pas

    save_file = save_dir / filename

    data = serialize_simulation(simulation)

    with open(save_file, "w") as f:
        # Indent pour la lisibilité
        json.dump(data, f, indent=4)


def load_game(filename: str | None  = None) -> Simulation:
    """Charge l'état du jeu à partir d'un fichier JSON
    Si 'filename' est None (non spécifié), charge la sauvegarde la plus récente
    dans le répertoire de sauvegarde.
    """
    save_dir = get_save_dir()

    if filename is None:
        # 1. Lister tous les fichiers .json dans le répertoire de sauvegarde
        save_files = list(save_dir.glob("*.json"))

        if not save_files:
            raise FileNotFoundError(f"Aucune sauvegarde trouvée dans le repertoire de sauvegarde {save_dir}")
        
        # 2. Trier les fichiers par nom (le timestamp YYYYMMDD_HHMMSS assure le tri chronologique)
        latest_save_path = max(save_files)
        save_file = latest_save_path

    else:
        #charger le fichier de sauvegarde spécifié
        if not filename.lower().endswith(".json"):
            filename += ".json"

        save_file = save_dir / filename

    if not save_file.exists():
        raise FileNotFoundError(f"Fichier de sauvegarde non trouvé: {save_file}")

    with open(save_file) as f:
        data = json.load(f)

    simulation = deserialize_simulation(data)

    return simulation
