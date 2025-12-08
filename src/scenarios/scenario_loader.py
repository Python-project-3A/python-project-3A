from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.battlefield import Battlefield

from src.units.knight import Knight
from src.units.pikeman import Pikeman
from src.units.unit_base import Unit




class ScenarioLoader:
    """Loads and spawns scenarios from JSON files"""

    # Map string names to classes   
    UNIT_CLASSES = {
        "Pikeman": Pikeman,
        "Knight": Knight,
        # Add more later
        # "Crossbowman": Crossbowman,
        # "LongSwordsman": LongSwordsman,
    }

    # Cache for unit stats
    _unit_stats_cache = None

    @staticmethod
    def get_scenarios_path() -> Path:
        """Get path to scenarios directory"""
        return Path(__file__).parent.parent / "data" / "scenarios"

    @staticmethod
    def get_units_stats_path() -> Path:
        """Get path to units.json"""
        return Path(__file__).parent.parent / "data" / "units.json"

    @staticmethod
    def load_unit_stats() -> dict:
        """Load unit stats from JSON (cached)"""
        if ScenarioLoader._unit_stats_cache is None:
            stats_file = ScenarioLoader.get_units_stats_path()
            with open(stats_file) as f:
                ScenarioLoader._unit_stats_cache = json.load(f)
        return ScenarioLoader._unit_stats_cache

    @staticmethod
    def list_available_scenarios() -> list[str]:
        """List all available scenario files"""
        scenarios_dir = ScenarioLoader.get_scenarios_path()
        if not scenarios_dir.exists():
            return []
        return [f.stem for f in scenarios_dir.glob("*.json")]

    @staticmethod
    def load_scenario(scenario_name: str) -> dict:
        """Load scenario from JSON file"""
        scenarios_dir = ScenarioLoader.get_scenarios_path()
        scenario_file = scenarios_dir / f"{scenario_name}.json"

        if not scenario_file.exists():
            raise FileNotFoundError(f"Scenario '{scenario_name}' not found. Available: {ScenarioLoader.list_available_scenarios()}")

        with open(scenario_file) as f:
            return json.load(f)

    @staticmethod
    def create_unit_from_stats(unit_type: str, owner: int, x: float, y: float):
        """
        Crée une unité et lui injecte TOUTES les stats du JSON dynamiquement.
        """
        all_stats = ScenarioLoader.load_unit_stats()

        if unit_type not in all_stats:
            # Fallback utile si le JSON est mal formé ou incomplet
            raise ValueError(f"Unknown unit type: {unit_type}")

        stats = all_stats[unit_type]

        # Récupération de la classe (Pikeman, Knight...) ou Unit par défaut
        cls = ScenarioLoader.UNIT_CLASSES.get(unit_type, Unit)

        # 1. Instanciation "Sécurisée" :
        # On utilise .get(key, 0) pour fournir des valeurs par défaut au constructeur __init__
        # car tes nouvelles unités n'ont plus de clé "damage" ou "armor" simple.
        unit = cls(
            name=unit_type,
            owner=owner,
            x=x,
            y=y,
            r=stats.get("r", 0.4),
            hp=stats.get("hp", 10),
            armor=stats.get("armor", 0),    # Valeur bidon pour satisfaire __init__
            damage=stats.get("damage", 0),  # Valeur bidon pour satisfaire __init__
            attack_range=stats.get("attack_range", 1.0),
            vision_range=stats.get("vision_range", 5.0),
            attack_cooldown=stats.get("attack_cooldown", 2.0),
            speed=stats.get("speed", 1.0),
        )

        # 2. Injection Dynamique (Magie Python) :
        # C'est ici qu'on ajoute unit.damage_cavalry, unit.armor_pierce, etc.
        # sans avoir besoin de les déclarer dans le __init__ de la classe.
        for key, value in stats.items():
            setattr(unit, key, value)

        return unit

    @staticmethod
    def spawn_scenario(scenario_data: dict, battlefield: Battlefield, general_overrides: dict[int, str] | None = None) -> dict[int, str]:
        general_overrides = general_overrides or {}
        general_types = {}

        for army in scenario_data["armies"]:
            player_id = army["player_id"]
            
            # Gestion de l'override du général (ex: via ligne de commande)
            general_type = general_overrides.get(player_id, army.get("general"))
            general_types[player_id] = general_type

            for unit_group in army["units"]:
                unit_type = unit_group["type"]
                count = unit_group["count"]
                formation = unit_group.get("formation", "column")
                start_x = unit_group["start_x"]
                start_y = unit_group["start_y"]
                spacing = unit_group.get("spacing", 1.0) # 1.0 est plus standard pour éviter les trous

                # Calcul des positions
                positions = ScenarioLoader._calculate_formation(formation, count, start_x, start_y, spacing)

                for x, y in positions:
                    # Fonction interne pour "capturer" les valeurs de x, y, unit_type et owner
                    # C'est nécessaire car battlefield.spawn_unit attend une fonction (factory)
                    def make_unit(u_type=unit_type, owner=player_id, px=x, py=y):
                        return ScenarioLoader.create_unit_from_stats(u_type, owner, px, py)

                    battlefield.spawn_unit(make_unit, x, y, owner=player_id)

        return general_types

    @staticmethod
    def _calculate_formation(formation: str, count: int, start_x: float, start_y: float, spacing: float) -> list[tuple[float, float]]:
        """Calculate unit positions for different formations"""
        positions = []

        if formation == "column":
            # Vertical column
            for i in range(count):
                positions.append((start_x, start_y + i * spacing))

        elif formation == "line":
            # Horizontal line
            for i in range(count):
                positions.append((start_x + i * spacing, start_y))

        elif formation == "block":
            # Rectangular block
            import math

            cols = math.ceil(math.sqrt(count))
            for i in range(count):
                row = i // cols
                col = i % cols
                positions.append((start_x + col * spacing, start_y + row * spacing))

        elif formation == "wedge":
            # V-formation
            for i in range(count):
                row = i // 2
                side = 1 if i % 2 == 0 else -1
                positions.append((start_x + side * row * spacing * 0.7, start_y + row * spacing))

        else:
            # Default to column
            for i in range(count):
                positions.append((start_x, start_y + i * spacing))

        return positions
