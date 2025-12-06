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

        # AI Status Generation
        ai_status:list[str] = []
        for general in self.battlefield.generals:
            ai_status.append(f"""
            <div class="general-section-content-item">
              <h3>{general.name} (Player {general.player_id})</h3>
              <div class="general-section-data">
                <p>
                    <span style="color: var(--secondary-foreground)">
                        Type:
                    </span>
                    <span style="color: var(--muted-foreground)">
                        {general.__class__.__name__}
                    </span>
                </p>
                <p>
                    <span style="color: var(--secondary-foreground)">
                        Units Controlled:
                    </span>
                    <span style="color: var(--muted-foreground)">
                        {len(self.battlefield.units_by_owner(general.player_id))}
                    </span>
                </p>
              </div>
            </div>
            """)
        ai_section = "".join(ai_status)

        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Battlefield Snapshot - Tick {tick_count}</title>
        <link
            href="https://fonts.googleapis.com/css?family=Inter"
            rel="stylesheet"
        />
        <style>
      :root {{
        --background: oklch(1 0 0);
        --foreground: oklch(0.145 0 0);
        --card: oklch(1 0 0);
        --card-foreground: oklch(0.145 0 0);
        --primary: oklch(0.205 0 0);
        --primary-foreground: oklch(0.985 0 0);
        --secondary: oklch(0.97 0 0);
        --secondary-foreground: oklch(0.205 0 0);
        --muted: oklch(0.97 0 0);
        --muted-foreground: oklch(0.556 0 0);
        --accent: oklch(0.97 0 0);
        --accent-foreground: oklch(0.205 0 0);
        --border: oklch(0.922 0 0);
        --input: oklch(0.922 0 0);
        --ring: oklch(0.708 0 0);
        --radius: 0.625rem;
      }}

      .dark {{
        --background: oklch(0.145 0 0);
        --foreground: oklch(0.985 0 0);
        --card: oklch(0.145 0 0);
        --card-foreground: oklch(0.985 0 0);
        --primary: oklch(0.985 0 0);
        --primary-foreground: oklch(0.205 0 0);
        --secondary: oklch(0.269 0 0);
        --secondary-foreground: oklch(0.985 0 0);
        --muted: oklch(0.269 0 0);
        --muted-foreground: oklch(0.708 0 0);
        --accent: oklch(0.269 0 0);
        --accent-foreground: oklch(0.985 0 0);
        --border: oklch(0.269 0 0);
        --input: oklch(0.269 0 0);
        --ring: oklch(0.439 0 0);
      }}

      .main-title {{
        font-size: 2.5rem;
        margin: 0;
        padding-top: 1rem;
        padding-bottom: 1rem;
        place-self: center;
        width: 90%;
      }}

      .battlefield-details {{
        place-self: center;
        width: 80%;
      }}

      tbody tr:last-child {{
        border-bottom: 0;
      }}

      tr {{
        border-bottom: 1px solid var(--border);
        &:hover {{
          background-color: var(--muted);
        }}
      }}

      td {{
        padding: 0.6rem;
        text-align: left;
      }}

      thead {{
        padding-bottom: 1rem;
        height: 2.5rem;
        text-align: left;
        vertical-align: middle;
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
        place-self: center;
      }}

      .table-wrapper {{
        width: 90%;
      }}

      .stats-section {{
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        gap: 0.5rem;
        width: 90%;
        place-self: center;
      }}

      .stats-section-header {{
        text-align: left;
        padding: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: start;
        gap: 1rem;
        width: 90%;
        font-weight: 900;
      }}

      .collapsible-icon {{
        cursor: pointer;
        border-radius: 50%;
        padding: 0.25rem;
        border: 1px solid var(--primary);
      }}

      .general-section-content {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        width: 90%;
        gap: 1rem;
      }}

      .general-section-content-item {{
        border: 1px solid var(--border);
        background-color: var(--card);
        color: var(--secondary-foreground);
        border-radius: 0.5rem;
        padding: 1.5rem;

        &:hover {{
          border: 1px solid var(--secondary-foreground);
        }}
      }}

      .general-section-data {{
        padding-top: 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }}

      .map-section-content {{
        width: 90%;
      }}

      p,
      h3 {{
        margin: 0;
      }}
        </style>
    <script>
      const getThemePreference = () => {{
        if (
          typeof localStorage !== "undefined" &&
          localStorage.getItem("theme")
        ) {{
          return localStorage.getItem("theme");
        }}
        return window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
      }};
      const isDark = getThemePreference() === "dark";
      document.documentElement.classList[isDark ? "add" : "remove"]("dark");

      if (typeof localStorage !== "undefined") {{
        const observer = new MutationObserver(() => {{
          const isDark = document.documentElement.classList.contains("dark");
          localStorage.setItem("theme", isDark ? "dark" : "light");
        }});
        observer.observe(document.documentElement, {{
          attributes: true,
          attributeFilter: ["class"],
        }});
      }}
    </script>
    </head>
    <body
    style="
      background-color: var(--background);
      color: var(--foreground);
      font-family: Inter;
    "
    >
        <h1 class="main-title">Battlefield Snapshot</h1>
        <div class="battlefield-details" style="font-size: 18px">
            <p>
                <span style="font-weight: bold">Tick:</span>
                {tick_count}
            </p>
            <p>
                <span style="font-weight: bold">Battlefield size:</span>
                {snapshot["width"]}*{snapshot["height"]}
            </p>
        </div>

        <section class="stats-section">
            <div class="stats-section-header">
                <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="lucide lucide-chevron-down-icon lucide-chevron-down collapsible-icon open"
                >
                <path d="m6 9 6 6 6-6" />
                </svg>
                <p>Units & Statistics</p>
            </div>
            <div class="table-wrapper collapsible-element">
                <table>
                    <thead>
                        <tr>
                            <th>Id</th>
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

                  </table
            </div>
        </section>

        <section class="stats-section">
            <div class="stats-section-header">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="lucide lucide-chevron-down-icon lucide-chevron-down collapsible-icon open"
                >
                    <path d="m6 9 6 6 6-6" />
                </svg>

                <p>General Status</p>
            </div>
            <div class="general-section-content">
                {ai_section}
            </div>
        </section>


        <section class="stats-section">
            <div class="stats-section-header">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="lucide lucide-chevron-down-icon lucide-chevron-down collapsible-icon open"
                >
                    <path d="m6 9 6 6 6-6" />
                </svg>

                <p>Map Details</p>
            </div>

            <div class="map-section-content">
                <p style="font-size: 1.2rem">Total Tiles: {snapshot["width"] * snapshot["height"]}</p>
            </div>
        </section>
        
        <script defer>
            (() => {{
                const collapsibleIcons = document.querySelectorAll(".collapsible-icon");
                const collapsibleElements = document.querySelectorAll(
                ".collapsible-element"
                );

                collapsibleIcons.forEach((entry) => {{
                entry.addEventListener("click", (e) => {{
                    if (entry.classList.contains("open")) {{
                    entry.classList.remove("open");
                    entry.innerHTML =
                        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-right-icon lucide-chevron-right close"><path d="m9 18 6-6-6-6"/></svg>';
                    entry.classList.add("close");

                    entry.parentElement.nextElementSibling.style.display = "none";
                    }} else if (entry.classList.contains("close")) {{
                    entry.classList.remove("close");
                    entry.classList.add("open");
                    entry.innerHTML =
                        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down collapsible-icon open"><path d="m6 9 6 6 6-6" /></svg>';
                    entry.classList.add("open");

                    entry.parentElement.nextElementSibling.style.display = "grid";
                    }}
                }});
                }});
            }})();
        </script>

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
