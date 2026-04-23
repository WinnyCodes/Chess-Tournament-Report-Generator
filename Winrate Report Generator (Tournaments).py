import re
import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from collections import defaultdict

# --------------------------------------------------
# CLEAN NAME
# --------------------------------------------------
def clean_name(name):
    name = name.lower().strip()

    # remove [make-up] or (make-up)
    name = re.sub(r"[\[\(]\s*make[\s-]?up\s*[\]\)]", "", name, flags=re.IGNORECASE)

    # remove other tags
    name = re.sub(r"[\[\(].*?[\]\)]", "", name)

    # normalize commas
    name = re.sub(r"\s*,\s*", ",", name)

    # convert "last, first" → "first last"
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        if len(parts) == 2:
            name = f"{parts[1]} {parts[0]}"

    name = re.sub(r"\s+", " ", name)

    return name.title().strip()


# --------------------------------------------------
def format_score(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def clean_filename(path):
    name = os.path.basename(path)
    return re.sub(r"\.html?$", "", name, flags=re.IGNORECASE)


# --------------------------------------------------
# PARSE FILES
# --------------------------------------------------
def parse_files(files):

    players = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "games": 0}))

    for file_name in files:
        with open(file_name, encoding="utf-8") as f:
            lines = f.readlines()

        in_table = False

        for line in lines:
            line = line.strip()

            if "Cross Table" in line:
                in_table = True
                continue

            if not in_table:
                continue

            if "Swiss Perfect" in line:
                break

            parts = line.split()

            if not parts or not parts[0].isdigit():
                continue

            name_parts = []
            for p in parts[1:]:
                if p.replace('.', '', 1).isdigit():
                    break
                name_parts.append(p)

            if not name_parts:
                continue

            name = clean_name(" ".join(name_parts))

            rounds = re.findall(r"(\d+|½):([WLD]?)", line)

            for score, result in rounds:
                if result == "" or score == "0":
                    continue

                players[name][file_name]["games"] += 1

                if result == "W":
                    players[name][file_name]["wins"] += 1
                elif result == "D":
                    players[name][file_name]["wins"] += 0.5

    return players


# --------------------------------------------------
# TROPHIES (POINTS ONLY)
# --------------------------------------------------
def get_trophy_winners(players, files, limit):

    trophy_data = []
    excluded = set()

    for cls in files:

        ranking = []

        for name, classes in players.items():

            data = classes.get(cls, {"wins": 0, "games": 0})
            points = data["wins"]
            games = data["games"]

            if games == 0:
                continue

            ranking.append((points, games, name))

        ranking.sort(key=lambda x: (x[0], x[1]), reverse=True)

        top = ranking[:limit]
        trophy_data.append((cls, top))

        for _, _, name in top:
            excluded.add(name)

    return trophy_data, excluded


# --------------------------------------------------
# HIGH % AWARDS (GLOBAL LOGIC FIXED)
# --------------------------------------------------
def get_stream_winners(players, files, excluded, min_games):

    # -----------------------------
    # GLOBAL STATS (once only)
    # -----------------------------
    global_stats = {}

    for name, classes in players.items():

        total_w = 0
        total_g = 0

        for f in files:
            data = classes.get(f, {"wins": 0, "games": 0})
            total_w += data["wins"]
            total_g += data["games"]

        if total_g >= min_games:
            global_stats[name] = (total_w, total_g, (total_w / total_g) * 100)

    stream_results = []

    # -----------------------------
    # PER STREAM RANKING
    # -----------------------------
    for cls in files:

        stream_candidates = []

        for name, (w, g, wr) in global_stats.items():

            if name in excluded:
                continue

            # must have played THIS stream
            stream_games = players[name][cls]["games"]
            if stream_games == 0:
                continue

            stream_candidates.append((wr, w, g, name))

        # sort by GLOBAL winrate
        stream_candidates.sort(reverse=True)

        if not stream_candidates:
            stream_results.append((cls, [], 0))
            continue

        best_wr = stream_candidates[0][0]

        winners = [
            (name, wr, w, g)
            for wr, w, g, name in stream_candidates
            if wr == best_wr
        ]

        stream_results.append((cls, winners, best_wr))

    return stream_results


# --------------------------------------------------
# GENERATE HTML
# --------------------------------------------------
def generate_html(players, files, title, min_games, trophy_count):

    eligible = []
    ineligible = []

    for name, classes in players.items():

        total_wins = 0
        total_games = 0
        class_cells = []

        best_games = -1
        best_wr = -1
        best_indices = []

        for i, cls in enumerate(files):

            data = classes.get(cls, {"wins": 0, "games": 0})
            w = data["wins"]
            g = data["games"]

            wr = (w / g * 100) if g > 0 else 0

            if g > best_games:
                best_games = g
                best_wr = wr
                best_indices = [i]
            elif g == best_games and g > 0:
                if wr > best_wr:
                    best_wr = wr
                    best_indices = [i]
                elif wr == best_wr:
                    best_indices.append(i)

        for i, cls in enumerate(files):

            data = classes.get(cls, {"wins": 0, "games": 0})
            w = data["wins"]
            g = data["games"]

            total_wins += w
            total_games += g

            if g == 0:
                class_cells.append("")
                continue

            wr = (w / g) * 100
            symbol = " *" if i in best_indices else ""

            class_cells.append(f"{format_score(w)}/{g} ({wr:.1f}%){symbol}")

        total_wr = (total_wins / total_games * 100) if total_games else 0

        row = (name.title(), total_wins, total_games, total_wr, class_cells)

        if total_games >= min_games:
            eligible.append(row)
        else:
            ineligible.append(row)

    eligible.sort(key=lambda x: (x[3], x[2]), reverse=True)
    ineligible.sort(key=lambda x: (x[3], x[2]), reverse=True)

    trophy_data, excluded = get_trophy_winners(players, files, trophy_count)
    stream_winners = get_stream_winners(players, files, excluded, min_games)

    # --------------------------------------------------
    html = f"""
<html>
<head>
<title>{title}</title>

<style>
body {{ font-family: Arial; padding: 20px; }}
h1 {{ text-align: center; }}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    margin-bottom: 25px;
}}

th, td {{
    border: 1px solid #ccc;
    padding: 6px;
    text-align: center;
}}

tr:nth-child(even) {{ background: #fafafa; }}

.name {{
    text-align: left;
    font-weight: bold;
    font-size: 16px;
    width: 240px;
}}
</style>

</head>
<body>

<h1>🏆 {title}</h1>
"""

    # --------------------------------------------------
    # WINRATE LEADERBOARD
    # --------------------------------------------------
    html += "<h2>📊 Winrate Leaderboard</h2><table><tr><th>#</th><th>Name</th><th>Win %</th><th>Total Wins</th><th>Games</th>"

    for cls in files:
        html += f"<th>{clean_filename(cls)}</th>"

    html += "</tr>"

    rank = 1
    for name, wins, games, wr, cells in eligible:

        html += f"<tr><td>{rank}</td><td class='name'>{name}</td><td>{wr:.1f}%</td><td>{format_score(wins)}</td><td>{games}</td>"

        for c in cells:
            html += f"<td>{c}</td>"

        html += "</tr>"
        rank += 1

    html += "</table>"

    # --------------------------------------------------
    # INELIGIBLE
    # --------------------------------------------------
    html += "<h2>📋 Ineligible Players</h2><table><tr><th>#</th><th>Name</th><th>Win %</th><th>Total Wins</th><th>Games</th></tr>"

    rank = 1
    for name, wins, games, wr, cells in ineligible:
        html += f"<tr><td>{rank}</td><td class='name'>{name}</td><td>{wr:.1f}%</td><td>{format_score(wins)}</td><td>{games}</td></tr>"
        rank += 1

    html += "</table>"

    # --------------------------------------------------
    # TROPHIES
    # --------------------------------------------------
    html += "<h2>🏆 Tournament Trophies</h2><table><tr><th>Stream</th><th>Rank</th><th>Player</th><th>Score</th></tr>"

    for cls, top in trophy_data:
        stream = clean_filename(cls)
        rank = 1
        for points, games, name in top:
            html += f"<tr><td>{stream}</td><td>{rank}</td><td>{name}</td><td>{format_score(points)}/{games}</td></tr>"
            rank += 1

    html += "</table>"

    # --------------------------------------------------
    # HIGH %
    # --------------------------------------------------
    html += "<h2>🎯 High Percentage Awards</h2><table><tr><th>Stream</th><th>Top Player(s)</th></tr>"

    for cls, winners, wr in stream_winners:

        if not winners:
            continue

        names = "<br>".join([
            f"{n} — {format_score(w)}/{g} ({wr2:.1f}%)"
            for n, wr2, w, g in winners
        ])

        html += f"<tr><td>{clean_filename(cls)}</td><td>{names}</td></tr>"

    html += f"""
</table>

<br><br>

<p style="text-align:center;">
Players must play at least <b>{min_games}</b> games to appear on the leaderboard.
</p>

<p style="text-align:center; font-size:12px; color:#555;">
* = Primary stream (most games played; tie-break by winrate)
</p>

</body>
</html>
"""

    return html


# --------------------------------------------------
def run_app():

    root = tk.Tk()
    root.withdraw()

    title = simpledialog.askstring("Tournament Name", "Enter report name:")
    min_games = simpledialog.askinteger("Minimum Games", "Enter minimum games required:", minvalue=1, initialvalue=7)

    trophy_count = simpledialog.askinteger(
        "Trophies Per Stream",
        "How many top scorer trophies per stream?",
        minvalue=1,
        initialvalue=5
    )

    files = filedialog.askopenfilenames(title="Select tournament files", filetypes=[("HTML files", "*.htm *.html")])

    players = parse_files(files)
    html = generate_html(players, files, title, min_games, trophy_count)

    output_file = title.replace(" ", "_") + ".html"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    messagebox.showinfo("Done", f"Report generated:\n{output_file}")


if __name__ == "__main__":
    run_app()