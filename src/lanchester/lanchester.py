
import math
def create_lanchester_scenario(unit_type: str, count_p0: int, count_p1: int) -> dict:
    """
    Génère un scénario Lanchester dynamiquement
    """
    total_units = count_p0 + count_p1
    map_size = max(60, int((total_units ** 0.5) * 2.0) + 10)
    start_x_p0 = map_size * 0.2
    start_x_p1 = map_size * 0.8      
    mid_y = map_size / 2

    rows_p2 = math.ceil(math.sqrt(count_p1))
    offset_p2 = (rows_p2 * 1.5) / 2 # On estime la hauteur du bloc
    start_y_p2 = mid_y + offset_p2

    scenario_data = {
    "name": f"Lanchester {unit_type} ({count_p0} vs {count_p1})",
        "description": "Lanchester Law verification",
        "map": {
            "width": map_size,
            "height": map_size
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
                        "formation": "block",
                        "start_x": start_x_p0,
                        "start_y": mid_y,
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
                        "formation": "block",
                        "start_x": start_x_p1,
                        "start_y": start_y_p2,
                        "spacing": -1.5 # construction mirroir
                    }
                ]
            }
        ]
    }
    
    return scenario_data