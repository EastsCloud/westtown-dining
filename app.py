from flask import Flask, render_template, request, redirect, url_for, session
import requests
import pdfplumber
from io import BytesIO
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secretkeyhahahaha"

PDF_URL = "https://westtown.myschoolapp.com/ftpimages/1579/download/download_3631449.pdf?_=1758060252872"

# processing pdf
def get_menu_data():
    try:
        resp = requests.get(PDF_URL, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

    pdf_file = BytesIO(resp.content)
    menu_data = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        menu_data.append(row)
    except Exception:
        return []
    return menu_data

def parse_menu_text(cell: str):
    if not cell:
        return []
    lines = [ln.strip(" -•\u2022") for ln in cell.splitlines()]
    return [ln for ln in lines if ln]

def structure_sections(day_menu_cells):
    index_map = {
        "breakfast": 0,
        "snack":     1,
        "lunch":     2,
        "salad":     3,
        "diy":       None,
        "dinner":    4,
    }
    sections = {}
    for sec, idx in index_map.items():
        if idx is None or idx >= len(day_menu_cells):
            sections[sec] = []
        else:
            sections[sec] = parse_menu_text(day_menu_cells[idx])
    return sections

def empty_sections():
    return {
        "breakfast": [],
        "snack": [],
        "lunch": [],
        "salad": [],
        "diy": [],
        "dinner": [],
    }

# -------------- Date helpers --------------

def get_current_week_bounds(today=None):
    """
    Return (monday, sunday) date objects for the week containing 'today'.
    Monday..Sunday inclusive.
    """
    if today is None:
        today = datetime.now().date()
    wd = today.weekday()  # Mon=0..Sun=6
    monday = today - timedelta(days=wd)
    sunday = monday + timedelta(days=6)
    return monday, sunday

def clamp_to_current_week(date_obj):
    """
    If date_obj is outside this week's Monday..Sunday, return False.
    Otherwise True.
    """
    monday, sunday = get_current_week_bounds()
    return monday <= date_obj <= sunday

def compute_header_labels(for_date):
    """
    Return (weekday_name, shortday, date_str) for the header based on for_date.
    """
    dt = datetime.combine(for_date, datetime.min.time())
    weekday = dt.strftime("%A")           # "Wednesday"
    shortday = dt.strftime("%a").upper()  # "WED"
    date_str = dt.strftime("%m/%d")       # "09/17"
    return weekday, shortday, date_str

# -------------- Menu assembly for a given date --------------

def get_sections_for_date(date_obj):
    """
    If date is within the current week and Mon–Fri, return parsed sections.
    Otherwise return empty sections (so UI shows 'No data').
    """
    # Only allow current week's dates
    if not clamp_to_current_week(date_obj):
        return empty_sections()

    weekday = date_obj.weekday()  # Mon=0..Sun=6

    # PDF only has Mon–Fri columns (1..5). Show 'No data' on Sat/Sun.
    if weekday > 6:
        return empty_sections()

    # Column mapping: PDF columns: 0 = labels, 1..5 = Mon..Fri
    pdf_col = weekday + 1

    menu_data = get_menu_data()
    if not menu_data:
        return empty_sections()

    # Build the vertical slice for this column (skip header row at index 0)
    day_menu_cells = []
    for r in range(1, len(menu_data)):
        row = menu_data[r]
        if pdf_col < len(row):
            day_menu_cells.append(row[pdf_col])
        else:
            day_menu_cells.append("")

    return structure_sections(day_menu_cells)

# -------------- Routing --------------

@app.route('/', methods=['GET', 'POST'])
def index():
    # Initialize selected_date in session as "today" if not set
    if "selected_date" not in session:
        session["selected_date"] = datetime.now().date().isoformat()

    # Button actions adjust selected_date day-by-day (no wraparound)
    if request.method == 'POST':
        action = request.form.get("action")
        try:
            current = datetime.fromisoformat(session["selected_date"]).date()
        except Exception:
            current = datetime.now().date()

        if action == "back":
            current = current - timedelta(days=1)
        elif action == "forward":
            current = current + timedelta(days=1)
        elif action == "refresh":
            current = datetime.now().date()

        session["selected_date"] = current.isoformat()
        return redirect(url_for('index'))  # PRG pattern to avoid resubmits

    # Load selected_date and compute header/menu
    try:
        selected_date = datetime.fromisoformat(session["selected_date"]).date()
    except Exception:
        selected_date = datetime.now().date()
        session["selected_date"] = selected_date.isoformat()

    sections = get_sections_for_date(selected_date)
    weekday, shortday, date_str = compute_header_labels(selected_date)
    weekday_up = weekday.upper()

    # You still can use 'now' elsewhere in the template
    now = datetime.now()

    return render_template(
        'index.html',
        menu=sections,
        now=now,
        weekday=weekday,
        weekday_up=weekday_up,
        shortday=shortday,
        date_str=date_str,
        target_date=selected_date,
    )

if __name__ == '__main__':
    app.run(debug=True)

