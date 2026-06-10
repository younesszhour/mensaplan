import requests
from bs4 import BeautifulSoup
import os
import re
import io
import shutil
from PIL import Image
from playwright.sync_api import sync_playwright

# --- KONFIGURATION ---
MENSA_URL = "https://www.studierendenwerk-kassel.de/speiseplaene/zentralmensa-arnold-bode-strasse"
OUTPUT_DIR = "images"

DAYS_MAPPING = {
    "Montag": "montag.png",
    "Dienstag": "dienstag.png",
    "Mittwoch": "mittwoch.png",
    "Donnerstag": "donnerstag.png",
    "Freitag": "freitag.png",
    "Samstag": "samstag.png"
}

def create_image(day_name, dishes, filename):
    # HTML-Template im Querformat (1448x1072) für optimale Textbreite
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500&display=swap');
            
            body {{
                margin: 0;
                padding: 0;
                width: 1448px;
                height: 1072px;
                background-color: #ffffff;
                color: #000000;
                font-family: 'Outfit', -apple-system, sans-serif;
                display: flex;
                flex-direction: column;
                box-sizing: border-box;
            }}
            
            .header-container {{
                padding: 60px 80px 20px 80px;
            }}
            
            h1 {{
                font-size: 56px;
                font-weight: 500;
                margin: 0 0 20px 0;
                color: #000000;
            }}
            
            .divider {{
                height: 6px;
                background-color: #000000;
                width: 100%;
            }}
            
            .content {{
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: space-evenly;
                padding: 10px 80px 60px 80px;
            }}
            
            .dish-block {{
                display: flex;
                flex-direction: column;
            }}
            
            .label {{
                font-size: 32px;
                font-weight: 300;
                color: #666666;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 12px;
            }}
            
            .meal-text {{
                font-size: 48px;
                font-weight: 400;
                line-height: 1.4;
                margin: 0;
            }}
            
            .empty-message {{
                font-size: 46px;
                font-weight: 400;
                text-align: center;
                margin-top: 150px;
                color: #333333;
            }}
        </style>
    </head>
    <body>
        <div class="header-container">
            <h1>Zentralmensa {day_name}</h1>
            <div class="divider"></div>
        </div>
        <div class="content">
    """
    
    if not dishes:
        html_content += '<div class="empty-message">Keine Daten oder geschlossen.</div>'
    else:
        for i, dish in enumerate(dishes[:3]):
            html_content += f"""
            <div class="dish-block">
                <div class="label">Essen {i+1}</div>
                <p class="meal-text">{dish['meal']}</p>
            </div>
            """
            
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1448, "height": 1072})
        page.set_content(html_content)
        page.evaluate("document.fonts.ready")
        screenshot_bytes = page.screenshot(type="png")
        browser.close()
        
        # In-Memory Rotation um 90 Grad für den hochkant Framebuffer
        img = Image.open(io.BytesIO(screenshot_bytes))
        img_rotated = img.rotate(90, expand=True)
        img_grayscale = img_rotated.convert("L")
        output_path = os.path.join(OUTPUT_DIR, filename)
        img_grayscale.save(output_path)
        print(f"Erstellt (Playwright + Rotation + Grayscale): {output_path}")

def create_weekend_image():
    filename = "wochenende.png"
    template_path = "wochenende_template.png"
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    if os.path.exists(template_path):
        shutil.copy(template_path, output_path)
        print(f"Kopiert (Wochenende-Template): {output_path}")
        return
        
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500&display=swap');
            
            body {
                margin: 0;
                padding: 0;
                width: 1448px;
                height: 1072px;
                background-color: #ffffff;
                color: #000000;
                font-family: 'Outfit', -apple-system, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                box-sizing: border-box;
            }
            
            h1 {
                font-size: 64px;
                font-weight: 400;
                margin: 0;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <h1>Schönes Wochenende!</h1>
    </body>
    </html>
    """
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1448, "height": 1072})
        page.set_content(html_content)
        page.evaluate("document.fonts.ready")
        screenshot_bytes = page.screenshot(type="png")
        browser.close()
        
        # In-Memory Rotation um 90 Grad für den hochkant Framebuffer
        img = Image.open(io.BytesIO(screenshot_bytes))
        img_rotated = img.rotate(90, expand=True)
        img_grayscale = img_rotated.convert("L")
        img_grayscale.save(output_path)
        print(f"Erstellt (Playwright-Fallback + Grayscale): {output_path}")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("Rufe Mensa-Daten ab...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(MENSA_URL, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler bei Web-Anfrage: {e}")
        import sys
        sys.exit(1)
    else:
        soup = BeautifulSoup(response.text, 'html.parser')
        week_data = {k: [] for k in DAYS_MAPPING.keys()}

        # ITERIERE DURCH DIE TAGE
        for day_name in DAYS_MAPPING.keys():
            day_div = soup.find("div", class_=f"tab_{day_name}")
            
            if not day_div:
                continue

            items = day_div.find_all("li")
            
            for item in items:
                headline = item.find("h5")
                if headline and "Salat" in headline.get_text():
                    continue

                p_essen = item.find("p", class_="essen")
                if not p_essen:
                    continue
                
                strong_tag = p_essen.find("strong")
                if strong_tag:
                    meal_text = strong_tag.get_text(strip=True)
                    meal_clean = re.sub(r'\s*\(\s*\d+.*\)', '', meal_text)
                    # Redundanten Beilagen-Zusatz entfernen
                    meal_clean = re.sub(r',?\s*dazu eine frei wählbare Beilage aus der Vitrine', '', meal_clean, flags=re.IGNORECASE)
                    meal_clean = meal_clean.strip()
                    
                    if meal_clean:
                         week_data[day_name].append({ "meal": meal_clean })

        # Bilder generieren
        for day_name, filename in DAYS_MAPPING.items():
            create_image(day_name, week_data.get(day_name, []), filename)

    create_weekend_image()

if __name__ == "__main__":
    main()
