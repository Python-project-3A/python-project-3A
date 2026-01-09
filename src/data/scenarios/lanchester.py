
def create_lanchester_scenario(unit_type: str, n: int) -> dict:
    """
    Génère un scénario Lanchester dynamiquement
    """
    map_width = 60 #max(50, int(n * 2))
    map_height = 40
    
    start_x_p0 = map_width * 0.25
    start_x_p1 = map_width * 0.75      
    mid_y = map_height / 2

    scenario_data = {
        "name": f"Lanchester Simulation ({unit_type})",
        "description": f"Testing Lanchester Laws: {n} vs {2*n}",
        "map": {
            "width": map_width,
            "height": map_height
        },
        "armies": [
            # JOUEUR 0
            {
                "player_id": 0,
                "general": "generalsmart", 
                "units": [
                    {
                        "type": unit_type,
                        "count": n,
                        "formation": "block",
                        "start_x": 20, #start_x_p0,
                        "start_y": 15, #mid_y,
                        "spacing": 1.5
                    }
                ]
            },
            #JOUEUR 1
            {
                "player_id": 1,
                "general": "generalsmart",
                "units": [
                    {
                        "type": unit_type,
                        "count": n * 2, 
                        "formation": "block",
                        "start_x": 40, #start_x_p1,
                        "start_y": 15, #mid_y,
                        "spacing": -1.5 # construction mirroir
                    }
                ]
            }
        ]
    }
    
    return scenario_data