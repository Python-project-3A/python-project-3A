import json
import os
from typing import Dict, Any

def load_unit_stats(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Charge les statistiques d'unité depuis un fichier JSON.
    Retourne un dictionnaire où la clé est le nom de l'unité et la valeur ses stats.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Le fichier de statistiques n'a pas été trouvé : {file_path}")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    return data