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
IMG_WIDTH = 1448
IMG_HEIGHT = 1072

FONT_SIZE_HEADER_MAIN = 60
FONT_SIZE_LABEL = 35
FONT_SIZE_TEXT = 52
LINE_SPACING = 12

# Layout-Konfiguration
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
    # Wir nehmen maximal die ersten 3 Gerichte
    dishes_to_draw = dishes[:3]
    num_dishes = len(dishes_to_draw)
    
    # Hilfsfunktion zum Speichern (inkl. Rotation für Kindle)
    def save_rotated(image_obj, fname):
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

    # --- LAYOUT LOGIK ---
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
    img = Image.new('L', (IMG_WIDTH, IMG_HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    font_main = get_font(FONT_SIZE_HEADER_MAIN)
    text = "Schönes Wochenende!"
    
    bbox = font_main.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    draw.text(((IMG_WIDTH - w)/2, (IMG_HEIGHT - h)/2), text, font=font_main, fill=0)
    
    img_rotated = img.rotate(90, expand=True)
    path = os.path.join(OUTPUT_DIR, filename)
    img_rotated.save(path)
    print(f"Erstellt (rotiert): {path}")

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
        # Wir machen weiter, damit ggf. leere Bilder erzeugt werden, statt abzustürzen
    else:
        soup = BeautifulSoup(response.text, 'html.parser')
        week_data = {k: [] for k in DAYS_MAPPING.keys()}

        # ITERIERE DURCH DIE TAGE
        for day_name in DAYS_MAPPING.keys():
            # Neue Struktur: <div class="tab_Donnerstag ...">
            # Wir suchen nach einem div, dessen Klasse "tab_Wochentag" enthält
            day_div = soup.find("div", class_=f"tab_{day_name}")
            
            if not day_div:
                continue

            # Suche alle Einträge (li) in diesem Tag
            items = day_div.find_all("li")
            
            for item in items:
                # 1. Prüfen, ob es Salat ist (im <h5> steht oft 'Salate')
                headline = item.find("h5")
                if headline and "Salat" in headline.get_text():
                    continue

                # 2. Das Gericht steht in <p class="essen"> -> <strong>
                p_essen = item.find("p", class_="essen")
                if not p_essen:
                    continue
                
                # Wir wollen nur den Text im <strong> Tag, da die Allergene im <sup> Tag daneben stehen
                strong_tag = p_essen.find("strong")
                if strong_tag:
                    meal_text = strong_tag.get_text(strip=True)
                    # Bereinigung von evtl. verbliebenen Klammern/Nummern, falls Struktur abweicht
                    # (Im aktuellen HTML ist das sauber getrennt, aber sicher ist sicher)
                    meal_clean = re.sub(r'\s*\(\s*\d+.*\)', '', meal_text)
                    
                    if meal_clean:
                         week_data[day_name].append({ "meal": meal_clean })

        # Bilder generieren
        for day_name, filename in DAYS_MAPPING.items():
            create_image(day_name, week_data.get(day_name, []), filename)

    create_weekend_image()

if __name__ == "__main__":
    main()
