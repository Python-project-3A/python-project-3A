
import math
def create_lanchester_scenario(unit_type: str, count_p0: int, count_p1: int) -> dict:
    """
    Génère un scénario Lanchester dynamiquement
    """

    scenario_data = {
    "name": f"Lanchester {unit_type} ({count_p0} vs {count_p1})",
        "description": "Lanchester Law verification",
        "map": {
            "width": 120,
            "height": 120
        },
        "armies": [
            # JOUEUR 0
            {
                "player_id": 0,
                "general": "DAFT", 
                "units": [
                    {
                        "type": unit_type,
                        "count": count_p0,
                        "formation": "block",#lanchester
                        "start_x": 20,
                        "start_y": 15,
                        "spacing": 1.5
                    }
                ]
            },
            #JOUEUR 1
            {
                "player_id": 1,
                "general": "DAFT",
                "units": [
                    {
                        "type": unit_type,
                        "count": count_p1, 
                        "formation": "block", #lanchester
                        "start_x": 20,
                        "start_y": 30,
                        "spacing": 1.5
                    }
                ]
            }
        ]
    }
    
    return scenario_data