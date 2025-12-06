from src.engine.battlefield import Battlefield
from src.units.unit_base import Unit
import os
import webbrowser


class HTMLSnapshot:
    def __init__(self, battlefield:Battlefield):
        self.battlefield = battlefield

    def generate_html_snapshot(self, tick_count: int):
        """
        Generates a static HTML page containing the battlefield and AI snapshot.
        """
        snapshot = self.battlefield.snapshot()
        
        unit_rows = []
        # Sort units by owner and then ID for better readability
        sorted_units = sorted(self.battlefield.get_all_units(), key=lambda u: (u.owner, u.id))
        
        for unit in sorted_units:
            status = "Alive" if unit.is_alive() else "Dead"
            order_desc = self._format_unit_order(unit)
            
            unit_rows.append(f"""
            <tr>
                <td>{unit.id}</td>
                <td>{unit.owner}</td>
                <td>{unit.name}</td>
                <td>{status}</td>
                <td>{unit.hp:.1f}</td>
                <td>({unit.position[0]:.1f}, {unit.position[1]:.1f})</td>
                <td>{order_desc}</td>
            </tr>
            """)
            
        unit_table = "".join(unit_rows)

        # --- AI Status Generation ---
        ai_status:list[str] = []
        for general in self.battlefield.generals:
            ai_status.append(f"""
            <div class="general-block">
                <h3>{general.name} (Player {general.player_id})</h3>
                <p><strong>Type:</strong> {general.__class__.__name__}</p>
                <p><strong>Units Controlled:</strong> {len(self.battlefield.units_by_owner(general.player_id))}</p>
                <p>
                    AIs are highly complex; detailed internal state is not exposed to the snapshot.<br>
                    Refer to unit tasks for active orders.
                </p>
            </div>
            """)
        ai_section = "".join(ai_status)

        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simulation Snapshot - Tick {tick_count}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
            h1 {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background-color: #007bff; color: white; cursor: pointer; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .section-header {{ background-color: #555; color: white; padding: 15px; margin-top: 30px; cursor: pointer; border-radius: 5px; }}
            .section-content {{ padding: 10px; border: 1px solid #ccc; border-top: none; background-color: white; }}
            .general-block {{ border: 1px solid #007bff; padding: 15px; margin-top: 15px; border-radius: 5px; background-color: #e6f2ff; }}
        </style>
        <script>
            // Simple script to toggle collapsible sections
            function toggleSection(id) {{
                const content = document.getElementById(id);
                if (content.style.display === "none") {{
                    content.style.display = "block";
                }} else {{
                    content.style.display = "none";
                }}
            }}
        </script>
    </head>
    <body>
        <h1>Simulation Snapshot</h1>
        <p><strong>Tick:</strong> {tick_count}</p>
        <p><strong>Battlefield Size:</strong> {snapshot["width"]}x{snapshot["height"]}</p>

        <div class="section-header" onclick="toggleSection('units-content')">Units & Statistics (Click to Toggle)</div>
        <div id="units-content" class="section-content">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Owner</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>HP</th>
                        <th>Position (x, y)</th>
                        <th>Current Task</th>
                    </tr>
                </thead>
                <tbody>
                    {unit_table}
                </tbody>
            </table>
        </div>

        <div class="section-header" onclick="toggleSection('ai-content')">AI/General Status (Click to Toggle)</div>
        <div id="ai-content" class="section-content" style="display: none;">
            {ai_section}
        </div>
        
    </body>
    </html>
    """
        return html_content
    
    def save_and_open_html_file(self, tick_count: int):
        FOLDER_NAME = "temp"
        FILE_NAME = "snapshot.html"
        
        # Ensure the directory exists
        os.makedirs(FOLDER_NAME, exist_ok=True) 

        # Construct the full path
        full_file_path = os.path.join(FOLDER_NAME, FILE_NAME)

        # Generate HTML snapshot
        html_content = self.generate_html_snapshot(tick_count)

        # Save the HTML content to the path
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        full_path_for_browser = os.path.abspath(full_file_path)
        webbrowser.open(f'file://{full_path_for_browser}')
        
    @staticmethod
    def _format_unit_order(unit:Unit):
        if not unit.current_order:
            return "Idle"
        order_type = unit.current_order["type"]
        if order_type == "move_to":
            target = unit.current_order['target']
            return f"Move To: ({target[0]:.1f}, {target[1]:.1f})"
        elif order_type == "attack_unit":
            target_unit = unit.current_order['target']
            return f"Attack Unit {target_unit.id} ({target_unit.name})"
        elif order_type == "attack_move":
            target = unit.current_order['target']
            return f"Attack Move: ({target[0]:.1f}, {target[1]:.1f})"
        return str(unit.current_order)
