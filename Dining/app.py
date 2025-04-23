from flask import Flask, render_template
import requests
import pdfplumber
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

def get_menu_data():
    url = "https://westtown.myschoolapp.com/ftpimages/1579/download/download_3308593.pdf?_=1726155235069"
    response = requests.get(url)
    pdf_file = BytesIO(response.content)
    
    menu_data = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages):
            table = page.extract_table()
            if table:
                for row in table:
                    menu_data.append(row)
    
    return menu_data

def get_todays_menu():
    menu_data = get_menu_data()
    current_day = datetime.now().weekday()  # Monday is 0, Sunday is 6
    
    # Adjust for the PDF's day mapping
    day = current_day + 1  # Add 1 to match the PDF's day mapping
    
    day_menu = []
    for i in range(1, len(menu_data)):
        if day < len(menu_data[i]):
            day_menu.append(menu_data[i][day])
    
    return day_menu

@app.route('/')
def index():
    menu = get_todays_menu()
    now = datetime.now()
    return render_template('index.html', menu=menu, now=now)

if __name__ == '__main__':
    app.run(debug=True) 