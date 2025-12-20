from src.engine.battlefield import Battlefield
from src.units.unit_base import Unit
import os
import webbrowser


class HTMLSnapshot:
    def __init__(self, battlefield: Battlefield):
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
        ai_status: list[str] = []
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

        html_content = f"""<!DOCTYPE html>
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
        text-wrap: nowrap;
      }}

      thead {{
        padding-bottom: 1rem;
        height: 2.5rem;
        text-align: left;
        vertical-align: middle;
        text-wrap: nowrap;
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
      }}

      .table-wrapper {{
        width: 90%;
        overflow-x: scroll;
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

        @media (width <= 40rem) {{
            grid-template-columns: repeat(1, 1fr);
        }}

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

      .theme-icon-wrapper {{
        width: 1.5rem;
        height: 1.5rem;
        place-self: end;
        cursor: pointer;
      }}
              
      ::-webkit-scrollbar {{
        width: 0.5rem;
        height: 0.5rem;
        }}

        ::-webkit-scrollbar-track {{
         background: transparent;
        }}

        ::-webkit-scrollbar-thumb {{
        background: rgb(163 163 163 );
         border-radius: 0.25rem;
        }}

        ::-webkit-scrollbar-thumb:hover {{
          background: rgb(212 212 212 );
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
        <header><div class="theme-icon-wrapper" role="button"></div></header>
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
            const handleCollapsible = () => {{
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
            }};
            handleCollapsible();

            const themeIconWrapper = document.querySelector(".theme-icon-wrapper");

            let isDarkMode = document.documentElement.classList.contains("dark");

            const sunIconSvg = `<svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="lucide lucide-sun-icon lucide-sun theme-icon"
                >
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2" />
                  <path d="M12 20v2" />
                  <path d="m4.93 4.93 1.41 1.41" />
                  <path d="m17.66 17.66 1.41 1.41" />
                  <path d="M2 12h2" />
                  <path d="M20 12h2" />
                  <path d="m6.34 17.66-1.41 1.41" />
                  <path d="m19.07 4.93-1.41 1.41" />
                </svg>`;
            const moonIconSvg = `<svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="lucide lucide-moon-icon lucide-moon theme-icon"
                >
                  <path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401" />
                </svg>`;

            themeIconWrapper.innerHTML = isDarkMode ? sunIconSvg : moonIconSvg;

            themeIconWrapper.addEventListener("click", () => {{
              document.documentElement.classList[isDarkMode ? "remove" : "add"](
                "dark"
              );
              isDarkMode = document.documentElement.classList.contains("dark");

              themeIconWrapper.innerHTML = isDarkMode ? sunIconSvg : moonIconSvg;
            }});

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
        webbrowser.open(f"file://{full_path_for_browser}")

    @staticmethod
    def save_tournament_report(data):
        """Sauvegarde le rapport de tournoi."""
        FOLDER_NAME = "temp"
        FILE_NAME = "tournament_report.html"
        os.makedirs(FOLDER_NAME, exist_ok=True)
        full_file_path = os.path.join(FOLDER_NAME, FILE_NAME)

        html_content = HTMLSnapshot.generate_html_report_tournament(data)

        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        full_path_for_browser = os.path.abspath(full_file_path)
        webbrowser.open(f"file://{full_path_for_browser}")

    @staticmethod
    def _format_unit_order(unit: Unit):
        if not unit.current_order:
            return "Idle"
        order_type = unit.current_order["type"]
        if order_type == "move_to":
            target = unit.current_order["target"]
            return f"Move To: ({target[0]:.1f}, {target[1]:.1f})"
        elif order_type == "attack_unit":
            target_unit = unit.current_order["target"]
            return f"Attack Unit {target_unit.id} ({target_unit.name})"
        elif order_type == "attack_move":
            target = unit.current_order["target"]
            return f"Attack Move: ({target[0]:.1f}, {target[1]:.1f})"
        return str(unit.current_order)

    @staticmethod
    def generate_html_report_tournament(data):
        """
        Génère un rapport HTML.
        V5 : Couleurs positionnelles strictes (Bleu/Rouge) pour noms et scores.
             Alignement titre à gauche.
        """

        # On utilise des couleurs bien lisibles sur fond sombre et clair
        COLOR_P1 = "oklch(0.65 0.18 240)"  # Bleu (Ligne / Gauche)
        COLOR_P2 = "oklch(0.63 0.22 30)"  # Rouge (Colonne / Droite)

        report_content = ""

        for scen, matrix in data.items():
            opponents = set()
            for p1, res in matrix.items():
                opponents.add(p1)
                opponents.update(res.keys())
            sorted_opps = sorted(list(opponents))

            # Separate trackers for column-wise (Red) and row-wise (Blue) victories
            col_total_victories = {opp: 0 for opp in sorted_opps}
            row_total_victories = {opp: 0 for opp in sorted_opps}

            # 2. Construction du Header (COLONNES = JOUEUR 2 = ROUGE)
            headers = ""
            for opp in sorted_opps:
                headers += f"<th><span class='general-name' style='color:{COLOR_P2};'>{opp}</span></th>"
            headers += "<th>TOTAL</th>"

            # 3. Construction des Lignes
            table_rows = ""
            total_rounds_display = ""

            for gen_main in sorted_opps:
                cells = ""
                current_row_blue_wins = 0

                for gen_opp in sorted_opps:
                    cell_content = "<span style='color:var(--muted-foreground); opacity:0.3'>--</span>"

                    w_main, w_opp, draws, rounds = 0, 0, 0, 0
                    has_match = False

                    # Récupération des données
                    if gen_main in matrix and gen_opp in matrix[gen_main]:
                        res = matrix[gen_main][gen_opp]
                        w_main, w_opp, draws = res[0], res[1], res["draw"]
                        has_match = True
                    elif gen_opp in matrix and gen_main in matrix[gen_opp]:
                        res = matrix[gen_opp][gen_main]
                        w_main, w_opp, draws = res[1], res[0], res["draw"]
                        has_match = True

                    if has_match:
                        # Logic: gen_main is Blue (Row), gen_opp is Red (Col)
                        current_row_blue_wins += w_main
                        col_total_victories[gen_opp] += w_opp

                        rounds = w_main + w_opp + draws
                        if not total_rounds_display:
                            total_rounds_display = f"(N={rounds})"

                        # Mise en gras du vainqueur
                        style_main = "font-weight:bold" if w_main > w_opp else ""
                        style_opp = "font-weight:bold" if w_opp > w_main else ""

                        # SCORE : BLEU (P1) - ROUGE (P2)
                        cell_content = f"""
                        <div class="score-cell">
                            <span style='color:{COLOR_P1}; {style_main}'>{w_main}</span>
                            <span class="separator">-</span>
                            <span style='color:{COLOR_P2}; {style_opp}'>{w_opp}</span>
                            <span class="draw-count">({draws})</span>
                        </div>
                        """

                    cells += f"<td>{cell_content}</td>"

                # End of row: Add the Blue Total for this row general
                row_total_victories[gen_main] = current_row_blue_wins
                cells += f"<td><b>{current_row_blue_wins}</b></td>"
                # Première colonne (LIGNE = JOUEUR 1 = BLEU)
                table_rows += f"<tr><td><span class='general-name' style='color:{COLOR_P1};'>{gen_main}</span></td>{cells}</tr>"
            
            # 3. Construction du Footer (TOTAL ROW - Red Victories)
            footer_cells = ""
            for opp in sorted_opps:
                footer_cells += f"<td><b>{col_total_victories[opp]}</b></td>"
            
            # Grand Total (Bottom Right)
            footer_cells += "<td> <span style='color:var(--muted-foreground)'> -- </span></td>"
            table_rows += f"<tr><td><b>Total Victoires</b></td>{footer_cells}</tr>"

            report_content += f"""
            <section>
                <div class="scenario-header">
                    <h2 class="scenario-title">Scenario: {scen}</h2>
                    <span class="round-count">{total_rounds_display}</span>
                </div>
                <div class="table-wrapper-wrapper">
                  <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th></th>
                                {headers}
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>                
                  </div>
                </div>
            </section>
            """

        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>Tournament Report</title>
            <link href="https://fonts.googleapis.com/css?family=Inter:400,700"
              rel="stylesheet" 
            />
            <style>
                :root {{
                    --background: oklch(1 0 0);
                    --foreground: oklch(0.145 0 0);
                    --muted: oklch(0.97 0 0);
                    --muted-foreground: oklch(0.556 0 0);
                    --border: oklch(0.922 0 0);
                }}

                .dark {{
                    --background: oklch(0.145 0 0);
                    --foreground: oklch(0.985 0 0);
                    --muted: oklch(0.269 0 0);
                    --muted-foreground: oklch(0.708 0 0);
                    --border: oklch(0.269 0 0);
                }}

                body{{ 
                    background-color: var(--background); 
                    color: var(--foreground);
                    font-family: 'Inter', sans-serif; 
                    margin:0;
                    padding: 2rem;
                }}
                
                .main-title {{
                    text-align: center;                    
                }}
                
                .scenario-header {{ 
                    display: flex;
                    align-items: center;
                    justify-content: start;
                    gap: 1rem;
                    width: 90%;
                    place-self: center;
                    padding-bottom: 1rem;
                }}

                .scenario-title {{ 
                    margin: 0;
                    font-size: 1.5rem;
                }}

                .round-count {{ 
                    color: var(--muted-foreground);
                    font-size: 1rem; 
                    font-weight: normal;
                }}

                .table-wrapper-wrapper {{
                    width: 90%;
                    overflow-x: scroll;
                    place-self:center;
                    padding-bottom: 0.5rem;
                }}

                .table-wrapper {{
                    box-shadow: 0 4px 6px -1px oklch(0 0 0 / 10%);
                    width: 98%;
                    border: 1px solid var(--border);
                    border-radius: 0.5rem;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    text-align: center;
                }}

                th:first-child {{
                    border-top-left-radius: 0.3rem;
                }}

                th:last-child{{
                    border-top-right-radius: 0.3rem
                }}

                th, td {{ 
                    padding: 1rem;
                    border-bottom: 1px solid var(--border);
                }}
                
                tr:last-child > td{{
                    border-bottom: 0px;
                }}

                th {{ 
                    background-color: var(--muted);
                    font-weight: bold;
                    text-transform: uppercase;
                    font-size: 0.85rem; 
                    letter-spacing: 0.05em;

                    &:first-child{{
                        border-right: 1px solid var(--border);                    
                    }}
                }}
                
                td:first-child {{ 
                    border-right: 1px solid var(--border);
                }}

                .general-name {{ 
                    font-weight: bold;
                }}
                
                .score-cell {{ 
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                    font-variant-numeric: tabular-nums;
                    font-size: 1.1em; 
                }}

                .separator {{ 
                    color: var(--muted-foreground);
                    opacity: 0.5;
                }}

                .draw-count {{ 
                    color: var(--muted-foreground);
                    font-size: 0.85em;
                    margin-left: 0.25rem;
                }}

                section{{
                    padding-top: 1rem;
                    padding-bottom: 1rem;
                }}

                .theme-icon-wrapper {{ 
                    position: absolute;
                    top: 1rem;
                    right: 1rem;
                    cursor: pointer;
                    padding: 0.5rem;
                    border-radius: 50%;
                    background: var(--muted); 
                }}

                .theme-icon {{ 
                  width: 1.5rem;
                  height: 1.5rem;
                }}

                ::-webkit-scrollbar{{
                  width: 0.5rem;
                  height: 0.5rem;
                }}

                ::-webkit-scrollbar-track{{
                  background: transparent;
                }}

                ::-webkit-scrollbar-thumb{{
                  background: oklch(0.7155 0 0);
                  border-radius: 0.25rem;
                }}

                ::-webkit-scrollbar-thumb:hover{{
                  background: oklch(0.8699 0 0);
                }}

            </style>
            <script>
              const getThemePreference = () => {{
                if (typeof localStorage !== "undefined" && localStorage.getItem("theme")) return localStorage.getItem("theme");
                return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
              }};
              const isDark = getThemePreference() === "dark";
              document.documentElement.classList[isDark ? "add" : "remove"]("dark");
            </script>
        </head>
        <body>
            <div class="theme-icon-wrapper">
                <svg id="moon" style="display:none" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
                <svg id="sun" style="display:none" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
            </div>
            
            <h1 class="main-title">Tournament Report</h1>
            {report_content}
            
            <script defer>
                const wrapper = document.querySelector(".theme-icon-wrapper");
                const moon = document.getElementById("moon");
                const sun = document.getElementById("sun");

                const updateIcon =  () => {{
                    const isDark = document.documentElement.classList.contains("dark");
                    moon.style.display = isDark ? "none" : "block";
                    sun.style.display = isDark ? "block" : "none";
                }}

                updateIcon();

                wrapper.addEventListener("click", () => {{
                    const isDark = document.documentElement.classList.contains("dark");
                    document.documentElement.classList[isDark ? "remove" : "add"]("dark");
                    localStorage.setItem("theme", !isDark ? "dark" : "light");
                    updateIcon();
                }});

            </script>
        </body>
        </html>
        """
        return html
