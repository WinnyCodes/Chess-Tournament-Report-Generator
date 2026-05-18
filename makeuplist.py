import re
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import defaultdict


# --------------------------------------------------
# MAKE-UP PATTERN
# --------------------------------------------------
MAKEUP_PATTERN = r"[\[\(]\s*make[\s-]?up\s*[\]\)]"


# --------------------------------------------------
# CLEAN NAME
# --------------------------------------------------
def clean_name(name):

    name = name.lower().strip()

    # remove make-up tags
    name = re.sub(MAKEUP_PATTERN, "", name, flags=re.IGNORECASE)

    # remove any other bracketed tags
    name = re.sub(r"[\[\(].*?[\]\)]", "", name)

    # normalize commas
    name = re.sub(r"\s*,\s*", ",", name)

    # convert "last, first" → "first last"
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        if len(parts) == 2:
            name = f"{parts[1]} {parts[0]}"

    # normalize spaces
    name = re.sub(r"\s+", " ", name)

    return name.title().strip()


# --------------------------------------------------
# DETECT MAKE-UP
# --------------------------------------------------
def is_makeup(name):

    return bool(
        re.search(MAKEUP_PATTERN, name, flags=re.IGNORECASE)
    )


# --------------------------------------------------
# CLEAN FILE NAME
# --------------------------------------------------
def clean_filename(path):

    name = os.path.basename(path)

    return re.sub(
        r"\.html?$",
        "",
        name,
        flags=re.IGNORECASE
    )


# --------------------------------------------------
# PARSE FILES
# --------------------------------------------------
def parse_files(files):

    # player -> stream -> makeup bool
    attendance = defaultdict(dict)

    for file_name in files:

        stream = clean_filename(file_name)

        with open(file_name, encoding="utf-8") as f:
            lines = f.readlines()

        in_table = False

        for line in lines:

            line = line.strip()

            # start parsing after crosstable
            if "Cross Table" in line:
                in_table = True
                continue

            if not in_table:
                continue

            # stop at footer
            if "Swiss Perfect" in line:
                break

            parts = line.split()

            # first token must be board number
            if not parts or not parts[0].isdigit():
                continue

            # --------------------------------------
            # EXTRACT PLAYER NAME
            # --------------------------------------
            name_parts = []

            for p in parts[1:]:

                # stop when numeric tournament data starts
                if p.replace('.', '', 1).isdigit():
                    break

                name_parts.append(p)

            if not name_parts:
                continue

            raw_name = " ".join(name_parts)

            player = clean_name(raw_name)

            if not player:
                continue

            attendance[player][stream] = {
                "makeup": is_makeup(raw_name)
            }

    return attendance


# --------------------------------------------------
# GENERATE HTML
# --------------------------------------------------
def generate_html(attendance):

    html = """
<html>
<head>
<title>Make-Up Attendance Report</title>

<style>

body {
    font-family: Arial;
    padding: 20px;
    background: white;
}

h1 {
    text-align: center;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

th, td {
    border: 1px solid #cccccc;
    padding: 8px;
    text-align: left;
    vertical-align: top;
}

th {
    background: #f0f0f0;
}

tr:nth-child(even) {
    background: #fafafa;
}

.student {
    font-weight: bold;
    font-size: 15px;
}

.makeup {
    color: #c00000;
    font-weight: bold;
}

.normal {
    color: #008000;
}

</style>
</head>

<body>

<h1>📋 Make-Up Attendance Report</h1>

<table>

<tr>
<th>Student</th>
<th>Streams Attended</th>
<th>Make-Up Streams</th>
</tr>
"""

    found = False

    for player in sorted(attendance.keys()):

        streams = attendance[player]

        # only show students in multiple streams
        if len(streams) < 2:
            continue

        found = True

        stream_display = []
        makeup_streams = []

        for stream, data in sorted(streams.items()):

            if data["makeup"]:

                stream_display.append(
                    f"<span class='makeup'>{stream} (make-up)</span>"
                )

                makeup_streams.append(stream)

            else:

                stream_display.append(
                    f"<span class='normal'>{stream}</span>"
                )

        makeup_text = (
            "<br>".join(makeup_streams)
            if makeup_streams
            else "-"
        )

        html += f"""
<tr>
<td class="student">{player}</td>
<td>{'<br>'.join(stream_display)}</td>
<td>{makeup_text}</td>
</tr>
"""

    if not found:

        html += """
<tr>
<td colspan="3">
No students attended multiple streams.
</td>
</tr>
"""

    html += """
</table>

<br><br>

<p>
Students listed here appeared in more than one tournament stream.
</p>

<p>
Streams marked in red were explicitly tagged as make-up sessions.
</p>

</body>
</html>
"""

    return html


# --------------------------------------------------
# MAIN APP
# --------------------------------------------------
def run_app():

    root = tk.Tk()
    root.withdraw()

    files = filedialog.askopenfilenames(
        title="Select tournament HTML files",
        filetypes=[("HTML files", "*.htm *.html")]
    )

    if not files:
        return

    attendance = parse_files(files)

    html = generate_html(attendance)

    try:

        # save beside the script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        output_file = os.path.join(
            script_dir,
            "makeup_report.html"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        print("Saved to:", output_file)

        messagebox.showinfo(
            "Done",
            f"Report generated:\n{output_file}"
        )

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )


# --------------------------------------------------
if __name__ == "__main__":
    run_app()