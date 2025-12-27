import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import re

# --- KONFIGURATION (Landscape, High-Res, Folder) ---
MENSA_URL = "https://www.studierendenwerk-kassel.de/speiseplaene/zentralmensa-arnold-bode-strasse"
OUTPUT_DIR = "images"  # WICHTIG: Unterordner
FONT_PATH = "Futura.ttc" 
IMG_WIDTH = 1448
IMG_HEIGHT = 1072
FONT_SIZE_HEADLINE = 65
FONT_SIZE_TEXT = 42

DAYS_MAPPING = {
    "Montag": "montag.png",
    "Dienstag": "dienstag.png",
    "Mittwoch": "mittwoch.png",
    "Donnerstag": "donnerstag.png",
    "Freitag": "freitag.png",
    "Samstag": "samstag.png"
}

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        return ImageFont.load_default()

def create_image(day_name, dishes, filename):
    img = Image.new('L', (IMG_WIDTH, IMG_HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    font_head = get_font(FONT_SIZE_HEADLINE)
    font_text = get_font(FONT_SIZE_TEXT)

    # Header
    draw.text((50, 40), f"Mensa: {day_name}", font=font_head, fill=0)
    draw.line((50, 130, IMG_WIDTH - 50, 130), fill=0, width=5)
    
    y_pos = 160
    if not dishes:
        draw.text((50, y_pos), "Keine Daten / Geschlossen", font=font_text, fill=0)
    else:
        for dish in dishes:
            cat_text = f"[{dish['category']}]"
            draw.text((50, y_pos), cat_text, font=font_text, fill=0)
            
            if dish['price']:
                price_bbox = draw.textbbox((0, 0), dish['price'], font=font_text)
                price_width = price_bbox[2] - price_bbox[0]
                draw.text((IMG_WIDTH - 50 - price_width, y_pos), dish['price'], font=font_text, fill=0)
            
            y_pos += 60
            
            full_text = dish['meal']
            words = full_text.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                if len(test_line) * 22 < (IMG_WIDTH - 100):
                    line = test_line
                else:
                    draw.text((80, y_pos), line, font=font_text, fill=0)
                    y_pos += 55
                    line = word + " "
            draw.text((80, y_pos), line, font=font_text, fill=0)
            y_pos += 100 
            
            if y_pos > IMG_HEIGHT - 60:
                break 

    path = os.path.join(OUTPUT_DIR, filename)
    img.save(path)
    print(f"Erstellt: {path}")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("Rufe Mensa-Daten ab...")
    try:
        response = requests.get(MENSA_URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    week_data = {k: [] for k in DAYS_MAPPING.keys()}

    accordions = soup.select(".accordion__item")
    for item in accordions:
        btn = item.select_one(".accordion__button")
        if not btn: continue
        header_text = btn.get_text(strip=True)
        
        current_day = None
        for day in DAYS_MAPPING.keys():
            if day in header_text:
                current_day = day
                break
        
        if current_day:
            content = item.select_one(".accordion__content")
            if not content: continue
            rows = content.select(".speiseplan__offer")
            if not rows: rows = content.select("tr")

            for row in rows:
                cat_el = row.select_one(".speiseplan__offer-type")
                meal_el = row.select_one(".speiseplan__offer-description") 
                price_el = row.select_one(".speiseplan__offer-price")

                category = cat_el.get_text(strip=True) if cat_el else "Gericht"
                meal = meal_el.get_text(strip=True) if meal_el else ""
                price = price_el.get_text(strip=True) if price_el else ""

                if "Salat" in category or "Salat" in meal: continue
                meal_clean = re.sub(r'\s*\(\s*\d+(?:\s*,\s*\d+)*\s*\)', '', meal)

                week_data[current_day].append({
                    "category": category,
                    "meal": meal_clean,
                    "price": price
                })

    for day_name, filename in DAYS_MAPPING.items():
        create_image(day_name, week_data.get(day_name, []), filename)

if __name__ == "__main__":
    main()
