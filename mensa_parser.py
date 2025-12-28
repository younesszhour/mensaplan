import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import os
import re

# --- KONFIGURATION ---
MENSA_URL = "https://www.studierendenwerk-kassel.de/speiseplaene/zentralmensa-arnold-bode-strasse"
OUTPUT_DIR = "images"
FONT_PATH = "Futura.ttc"

# AUFLÖSUNG & LAYOUT (Final)
# Wir entwerfen im Querformat (1448x1072), drehen es aber am Ende für den Kindle (1072x1448)
IMG_WIDTH = 1448
IMG_HEIGHT = 1072

FONT_SIZE_HEADER_MAIN = 60
FONT_SIZE_LABEL = 35
FONT_SIZE_TEXT = 52
LINE_SPACING = 12

# Layout-Konfiguration (Final)
DRAWING_AREA_TOP = 150 
DRAWING_AREA_BOTTOM = IMG_HEIGHT - 100
MAX_GAP = 90 
MIN_GAP = 15 

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

def calculate_wrapped_lines(text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        if width < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)
    return lines

def create_image(day_name, dishes, filename):
    img = Image.new('L', (IMG_WIDTH, IMG_HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    
    font_main = get_font(FONT_SIZE_HEADER_MAIN)
    font_label = get_font(FONT_SIZE_LABEL)
    font_text = get_font(FONT_SIZE_TEXT)

    # --- HEADER ---
    header_text = f"Zentralmensa {day_name}"
    draw.text((50, 40), header_text, font=font_main, fill=0)
    draw.line((50, 120, IMG_WIDTH - 50, 120), fill=0, width=6)
    
    # --- DATEN VORBEREITEN ---
    dishes_to_draw = dishes[:3]
    num_dishes = len(dishes_to_draw)
    
    # Hilfsfunktion zum Speichern (inkl. Rotation)
    def save_rotated(image_obj, fname):
        # 90 Grad drehen für Kindle Display (Portrait -> Landscape View)
        # expand=True tauscht Breite/Höhe (wird 1072x1448)
        img_rotated = image_obj.rotate(90, expand=True)
        path = os.path.join(OUTPUT_DIR, fname)
        img_rotated.save(path)
        print(f"Erstellt (rotiert): {path}")

    if not num_dishes:
        draw.text((50, 160), "Keine Daten oder geschlossen.", font=font_text, fill=0)
        save_rotated(img, filename)
        return

    block_heights = []
    wrapped_texts = [] 

    for dish in dishes_to_draw:
        h = FONT_SIZE_LABEL + 10 
        lines = calculate_wrapped_lines(dish['meal'], font_text, IMG_WIDTH - 100)
        wrapped_texts.append(lines)
        text_h = len(lines) * FONT_SIZE_TEXT + (len(lines)-1) * LINE_SPACING
        h += text_h
        block_heights.append(h)

    # --- LAYOUT LOGIK (Final) ---
    total_content_height = sum(block_heights)
    num_gaps = num_dishes - 1
    available_h = DRAWING_AREA_BOTTOM - DRAWING_AREA_TOP
    
    if num_gaps > 0:
        theoretical_gap = (available_h - total_content_height) / num_gaps
    else:
        theoretical_gap = 0

    if theoretical_gap > MAX_GAP:
        used_gap = MAX_GAP
        final_block_height = total_content_height + (num_gaps * used_gap)
        start_y = DRAWING_AREA_TOP + (available_h - final_block_height) / 2
    else:
        used_gap = max(MIN_GAP, theoretical_gap)
        start_y = DRAWING_AREA_TOP

    # --- ZEICHNEN ---
    current_y = start_y
    for i, dish in enumerate(dishes_to_draw):
        label = f"Essen {i+1}"
        draw.text((50, current_y), label, font=font_label, fill=0)
        current_y += (FONT_SIZE_LABEL + 10)
        
        lines = wrapped_texts[i]
        for line in lines:
            draw.text((50, current_y), line, font=font_text, fill=0)
            current_y += (FONT_SIZE_TEXT + LINE_SPACING)
        
        if i < num_dishes - 1:
            current_y += used_gap

    save_rotated(img, filename)

def create_weekend_image():
    filename = "wochenende.png"
    # Hinweis: Hier überschreiben wir nicht, wenn es existiert, 
    # aber für Layout-Tests solltest du das "if exists" vielleicht kurz rausnehmen
    # oder die Datei auf dem Server löschen.
    
    img = Image.new('L', (IMG_WIDTH, IMG_HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    font_main = get_font(FONT_SIZE_HEADER_MAIN)
    text = "Schönes Wochenende!"
    
    bbox = font_main.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    draw.text(((IMG_WIDTH - w)/2, (IMG_HEIGHT - h)/2), text, font=font_main, fill=0)
    
    # Drehen und Speichern
    img_rotated = img.rotate(90, expand=True)
    path = os.path.join(OUTPUT_DIR, filename)
    img_rotated.save(path)
    print(f"Erstellt (rotiert): {path}")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("Rufe Mensa-Daten ab...")
    try:
        response = requests.get(MENSA_URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Fehler: {e}")
    else:
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
                    meal_el = row.select_one(".speiseplan__offer-description") 
                    cat_el = row.select_one(".speiseplan__offer-type")
                    category = cat_el.get_text(strip=True) if cat_el else ""
                    if "Salat" in category: continue 
                    if meal_el:
                        meal = meal_el.get_text(strip=True)
                        meal_clean = re.sub(r'\s*\(\s*\d+(?:\s*,\s*\d+)*\s*\)', '', meal)
                        week_data[current_day].append({ "meal": meal_clean })

        for day_name, filename in DAYS_MAPPING.items():
            create_image(day_name, week_data.get(day_name, []), filename)

    create_weekend_image()

if __name__ == "__main__":
    main()
