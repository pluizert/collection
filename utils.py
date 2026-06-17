import os
import sqlite3
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

DB_FILE = "lego_inventory.db"
IMAGE_DIR = "images"

# Zorg ervoor dat de afbeeldingenmap bestaat
os.makedirs(IMAGE_DIR, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lego_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_number TEXT NOT NULL,
            name TEXT,
            purchase_date TEXT,
            purchase_price REAL,
            image_path TEXT,
            quantity INTEGER DEFAULT 1,
            retail_price REAL DEFAULT 0.0,
            current_price REAL DEFAULT 0.0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Migraties: Controleer of kolommen bestaan, zo niet, voeg ze toe
    alterations = {
        "quantity": "INTEGER DEFAULT 1",
        "retail_price": "REAL DEFAULT 0.0",
        "current_price": "REAL DEFAULT 0.0"
    }
    
    for col, col_type in alterations.items():
        try:
            cursor.execute(f"SELECT {col} FROM lego_sets LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(f"ALTER TABLE lego_sets ADD COLUMN {col} {col_type}")
            
    # Maak gebruikers tabel aan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin'
        )
    """)
    
    # Controleer of er ten minste één gebruiker is, zo niet, voeg admin toe
    cursor.execute("SELECT COUNT(*) as count FROM users")
    count = cursor.fetchone()["count"]
    if count == 0:
        # Haal het initiële wachtwoord op uit omgevingsvariabelen of Streamlit Secrets om hardcoding te vermijden
        initial_password = "Lego2026"
        try:
            import streamlit as st
            if "ADMIN_PASSWORD" in st.secrets:
                initial_password = st.secrets["ADMIN_PASSWORD"]
        except Exception:
            pass
        
        import os
        initial_password = os.environ.get("ADMIN_PASSWORD", initial_password)
        
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', ?, 'admin')", (initial_password,))
        
    conn.commit()
    conn.close()

def create_user(username, password, role='admin'):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def update_user(user_id, username, password, role='admin'):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET username = ?, password = ?, role = ? WHERE id = ?", (username, password, role, user_id))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY username ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def verify_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def clear_database():
    """Wist alle sets en afbeeldingen uit de database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lego_sets")
    conn.commit()
    conn.close()
    
    # Verwijder ook alle lokale afbeeldingen
    if os.path.exists(IMAGE_DIR):
        for f in os.listdir(IMAGE_DIR):
            file_path = os.path.join(IMAGE_DIR, f)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Kon afbeelding niet verwijderen: {e}")
    return True

def clean_set_number(set_num):
    """Zorgt ervoor dat het setnummer schoon is (bijv. '75192' of '75192-1')"""
    if not set_num or pd.isna(set_num):
        return ""
    # Verwijder whitespace en zet om naar string
    num_str = str(set_num).strip().split('.')[0] # Haal eventuele .0 weg van Excel import
    # Match alleen cijfers en eventueel een suffix (bijv. -1)
    match = re.match(r'^(\d+)(-\d+)?$', num_str)
    if match:
        base = match.group(1)
        suffix = match.group(2) if match.group(2) else "-1"
        return f"{base}{suffix}"
    return num_str

def parse_brickset_prices(rrp_text, current_val_text):
    """Parses RRP and Current value text into Euro float values"""
    retail_price = 0.0
    current_price = 0.0
    
    # Parse RRP for Euro symbol €
    if rrp_text:
        match_eu = re.search(r'(?:€\s*|€)(\d+(?:[.,]\d+)?)', rrp_text)
        if match_eu:
            retail_price = float(match_eu.group(1).replace(',', '.'))
        else:
            # Fallback naar dollar of pond
            match_any = re.search(r'(?:\$|£)(\d+(?:[.,]\d+)?)', rrp_text)
            if match_any:
                retail_price = float(match_any.group(1).replace(',', '.'))

    # Parse Current value for New price
    if current_val_text:
        match_new_eu = re.search(r'New:\s*~?\s*€\s*(\d+(?:[.,]\d+)?)', current_val_text)
        if match_new_eu:
            current_price = float(match_new_eu.group(1).replace(',', '.'))
        else:
            # Fallback naar Dollar of Pond
            match_new_any = re.search(r'New:\s*~?\s*(?:\$|£)?\s*(\d+(?:[.,]\d+)?)', current_val_text)
            if match_new_any:
                current_price = float(match_new_any.group(1).replace(',', '.'))
                
    return retail_price, current_price

import time
from collections import Counter

# Sessie aanmaken om cookies vast te houden (helpt tegen rate-limiting blokkades)
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7"
})

def fetch_lego_details_and_image(set_num):
    """
    Probeert de naam, afbeelding, adviesprijs (retail_price) en huidige prijs van de Lego set te downloaden van Brickset.
    Slaat de afbeelding lokaal op.
    Returns: (set_name, local_image_path, retail_price, current_price)
    """
    clean_num = clean_set_number(set_num)
    if not clean_num:
        return "Onbekende set", None, 0.0, 0.0

    brickset_num = clean_num if "-" in clean_num else f"{clean_num}-1"
    base_num = clean_num.split("-")[0]

    set_name = f"Lego Set {base_num}"
    local_image_path = os.path.join(IMAGE_DIR, f"{base_num}.jpg").replace('\\', '/')
    retail_price = 0.0
    current_price = 0.0

    url = f"https://brickset.com/sets/{brickset_num}"
    try:
        # Vermijd Brickset rate limits door even te wachten
        time.sleep(2.0)
        response = session.get(url, timeout=15)
        
        # Als we toch geblokkeerd worden (Rate Limit / 429), wacht dan 20 seconden en probeer opnieuw!
        if response.status_code == 429:
            time.sleep(25)
            response = session.get(url, timeout=15)
            
        if response.status_code == 200:
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Probeer eerst via de metadata tabel (<dl>) details op te halen
                dl = soup.find("dl")
                if dl:
                    dts = dl.find_all("dt")
                    dds = dl.find_all("dd")
                    rrp_text = ""
                    current_val_text = ""
                    for dt, dd in zip(dts, dds):
                        label = dt.get_text().strip().lower()
                        value = dd.get_text().strip()
                        if label == "name":
                            set_name = value
                        elif "rrp" in label:
                            rrp_text = value
                        elif "current value" in label:
                            current_val_text = value
                    
                    retail_price, current_price = parse_brickset_prices(rrp_text, current_val_text)
                
                # Als naam niet in de tabel stond, gebruik dan de h1 tag
                if set_name == f"Lego Set {base_num}":
                    h1_tag = soup.find("h1")
                    if h1_tag:
                        title_text = h1_tag.get_text().strip()
                        if ":" in title_text:
                            set_name = title_text.split(":", 1)[1].strip()
                        else:
                            set_name = title_text
                
                # Vind de afbeelding
                img_tag = soup.find("div", class_="featureimage")
                if img_tag and img_tag.find("img"):
                    img_url = img_tag.find("img")["src"]
                else:
                    img_tag = soup.find("img", src=re.compile(r"/sets/images/"))
                    img_url = img_tag["src"] if img_tag else None

                if img_url and not os.path.exists(local_image_path):
                    img_resp = session.get(img_url, timeout=10)
                    if img_resp.status_code == 200:
                        with open(local_image_path, "wb") as f:
                            f.write(img_resp.content)
            except Exception as e:
                print(f"Fout bij BeautifulSoup parsing: {e}")
    except Exception as e:
        print(f"Fout bij ophalen van {url}: {e}")

    # Zoek naar prijzen op meerdere websites (Brickwatch als aggregatie van Bol.com, Amazon, etc.)
    # Dit geeft vaak de meest realistische huidige "Nieuw" winkelwaarde
    try:
        bw_url = f"https://www.brickwatch.net/nl-NL/set/{base_num}/a.html"
        bw_resp = session.get(bw_url, timeout=10)
        if bw_resp.status_code == 200:
            bw_soup = BeautifulSoup(bw_resp.text, 'html.parser')
            
            best_bw_price = None
            
            # Methode 1: Zoek naar de "Koop nu" knop (vaak de laagste/beste prijs)
            btn = bw_soup.find(lambda tag: tag.name == 'a' and 'btn-warning' in tag.get('class', []) and '€' in tag.text)
            if btn:
                m = re.search(r'€\s*(\d{1,4}[.,]\d{2})', btn.text)
                if m:
                    best_bw_price = float(m.group(1).replace(',', '.'))
            
            # Methode 2: Zoek in de paginatitel ("Nu € XX,XX")
            if not best_bw_price:
                title = bw_soup.find('title')
                if title:
                    m = re.search(r'Nu\s*€\s*(\d{1,4}[.,]\d{2})', title.text)
                    if m:
                        best_bw_price = float(m.group(1).replace(',', '.'))
            
            # Methode 3: Fallback naar laagste aannemelijke prijs
            bw_text = bw_soup.get_text()
            matches = re.findall(r'€\s*(\d{1,4}[.,]\d{2})', bw_text)
            bw_prices = []
            for m in matches:
                val = float(m.replace(',', '.'))
                # Negeer verzendkosten (vaak heel klein) en onwaarschijnlijke extremen
                if val > 5.0 and val < 2000.0:
                    bw_prices.append(val)
            
            if bw_prices:
                if not best_bw_price:
                    best_bw_price = min(bw_prices)
                    
                # Als we nog geen RRP hadden, kunnen we de hoogste gevonden prijs op Brickwatch nemen als indicatie
                if retail_price == 0.0:
                    retail_price = max(bw_prices)

            # Gebruik de gevonden beste Brickwatch prijs
            if best_bw_price and best_bw_price > 0:
                current_price = best_bw_price

    except Exception as e:
        print(f"Fout bij ophalen van Brickwatch: {e}")

    # Fallback: Als we echt geen current_price hebben kunnen vinden (Brickset en Brickwatch gaven niets of 0),
    # maar we hebben wel een retail_price, dan gebruiken we de retail_price als aanname.
    if current_price == 0.0 and retail_price > 0.0:
        current_price = retail_price

    # Fallback 1: Directe Brickset CDN URL proberen voor de afbeelding
    if not os.path.exists(local_image_path):
        cdn_urls = [
            f"https://images.brickset.com/sets/images/{base_num}-1.jpg",
            f"https://images.brickset.com/sets/images/{base_num}.jpg",
            f"https://images.brickset.com/sets/Additional_images/{base_num}/img_0001.jpg"
        ]
        
        for cdn_url in cdn_urls:
            try:
                img_resp = session.get(cdn_url, timeout=5)
                if img_resp.status_code == 200:
                    with open(local_image_path, "wb") as f:
                        f.write(img_resp.content)
                    break
            except Exception as e:
                print(f"Fout bij downloaden van {cdn_url}: {e}")

    return set_name, (local_image_path if os.path.exists(local_image_path) else None), retail_price, current_price

# Database bewerkingen
def add_lego_set(set_number, name=None, purchase_date=None, purchase_price=None, image_path=None, quantity=1, retail_price=None, current_price=None):
    clean_num = clean_set_number(set_number)
    base_num = clean_num.split("-")[0] if "-" in clean_num else clean_num
    
    if not base_num or not base_num.isdigit():
        return False
        
    # Als er geen naam, afbeelding, of prijzen zijn meegegeven, probeer deze op te halen
    if not name or not image_path or retail_price is None or current_price is None:
        fetched_name, fetched_img, fetched_retail, fetched_current = fetch_lego_details_and_image(clean_num)
        if not name:
            name = fetched_name
        if not image_path:
            image_path = fetched_img
        if retail_price is None:
            retail_price = fetched_retail
        if current_price is None:
            current_price = fetched_current

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lego_sets (set_number, name, purchase_date, purchase_price, image_path, quantity, retail_price, current_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (base_num, name, purchase_date, purchase_price, image_path, quantity, retail_price, current_price))
    conn.commit()
    conn.close()
    return True

def get_all_sets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lego_sets ORDER BY purchase_date DESC, added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_set(set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Haal eerst de afbeeldingslocatie op om eventueel te verwijderen
    cursor.execute("SELECT image_path, set_number FROM lego_sets WHERE id = ?", (set_id,))
    row = cursor.fetchone()
    if row:
        image_path = row["image_path"]
        
        # Verwijder record uit database
        cursor.execute("DELETE FROM lego_sets WHERE id = ?", (set_id,))
        conn.commit()
        
        # Controleer of andere records nog dezelfde afbeelding gebruiken
        cursor.execute("SELECT COUNT(*) as count FROM lego_sets WHERE image_path = ?", (image_path,))
        count_row = cursor.fetchone()
        if count_row and count_row["count"] == 0 and image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f"Kon afbeelding {image_path} niet verwijderen: {e}")
                
    conn.close()
    return True

def update_set(set_id, set_number, name, purchase_date, purchase_price, quantity=1, retail_price=0.0, current_price=0.0):
    clean_num = clean_set_number(set_number)
    base_num = clean_num.split("-")[0] if "-" in clean_num else clean_num
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Controleer of afbeelding veranderd moet worden
    cursor.execute("SELECT set_number, image_path, retail_price, current_price FROM lego_sets WHERE id = ?", (set_id,))
    row = cursor.fetchone()
    image_path = row["image_path"] if row else None
    
    if row and row["set_number"] != base_num:
        _, fetched_img, fetched_retail, fetched_current = fetch_lego_details_and_image(clean_num)
        if fetched_img:
            image_path = fetched_img
        if fetched_retail:
            retail_price = fetched_retail
        if fetched_current:
            current_price = fetched_current
            
    cursor.execute("""
        UPDATE lego_sets
        SET set_number = ?, name = ?, purchase_date = ?, purchase_price = ?, image_path = ?, quantity = ?, retail_price = ?, current_price = ?
        WHERE id = ?
    """, (base_num, name, purchase_date, purchase_price, image_path, quantity, retail_price, current_price, set_id))
    conn.commit()
    conn.close()
    return True

def refresh_all_prices():
    """Haalt voor alle sets in de DB de nieuwste marktprijzen en namen op"""
    sets = get_all_sets()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for s in sets:
        name, _, rrp, current = fetch_lego_details_and_image(s["set_number"])
        
        # Update alleen de naam als deze momenteel de standaard 'Lego Set XXX' is. 
        # Anders behouden we ALTIJD de naam die de gebruiker in Excel had staan of zelf heeft bewerkt!
        current_name_in_db = s["name"]
        if current_name_in_db and current_name_in_db.startswith("Lego Set "):
            final_name = name if name and name != f"Lego Set {s['set_number']}" else current_name_in_db
        else:
            final_name = current_name_in_db
        
        cursor.execute("""
            UPDATE lego_sets
            SET name = ?, retail_price = ?, current_price = ?
            WHERE id = ?
        """, (final_name, rrp, current, s["id"]))
            
    conn.commit()
    conn.close()
    return True

def import_excel_or_csv(file_path_or_buffer, col_mapping, sheet_name=None):
    """
    Importeert Excel of CSV bestand.
    col_mapping: dict met sleutels 'set_number', 'purchase_date', 'purchase_price', 'name', 'quantity'
    """
    # Lees bestand
    if hasattr(file_path_or_buffer, 'name') and file_path_or_buffer.name.endswith('.csv'):
        df = pd.read_csv(file_path_or_buffer)
    else:
        if sheet_name:
            df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path_or_buffer)
    
    success_count = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Haal gegevens op basis van mapping
            set_num_col = col_mapping['set_number']
            set_num_raw = row[set_num_col] if set_num_col in row else None
            
            # Sla lege rijen of niet-numerieke / ongeldige setnummers over
            if pd.isna(set_num_raw):
                continue
                
            set_num_str = str(set_num_raw).strip().split('.')[0]
            # Als het setnummer geen cijfers bevat, is het waarschijnlijk een lege rij of een samenvatting (bijv. 'Totaal')
            if not re.match(r'^\d+$', set_num_str):
                continue
            
            # Prijs
            price_col = col_mapping['purchase_price']
            price_raw = row[price_col] if price_col in row else 0.0
            try:
                purchase_price = float(price_raw) if not pd.isna(price_raw) else 0.0
            except ValueError:
                purchase_price = 0.0
                
            # Datum
            date_col = col_mapping['purchase_date']
            date_raw = row[date_col] if date_col in row else None
            purchase_date = None
            if date_raw and not pd.isna(date_raw):
                if isinstance(date_raw, datetime):
                    purchase_date = date_raw.strftime('%Y-%m-%d')
                elif isinstance(date_raw, pd.Timestamp):
                    purchase_date = date_raw.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_raw).strip()
                    # Probeer diverse formats
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S'):
                        try:
                            # Haal eventuele tijd eraf
                            if ' ' in date_str:
                                date_str = date_str.split(' ')[0]
                            purchase_date = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            pass
                    if not purchase_date:
                        purchase_date = datetime.today().strftime('%Y-%m-%d')
            else:
                purchase_date = datetime.today().strftime('%Y-%m-%d')
                
            # Naam (optioneel)
            name = None
            name_col = col_mapping.get('name')
            if name_col and name_col in row and not pd.isna(row[name_col]):
                name = str(row[name_col]).strip()
                
            # Aantal / Quantity (optioneel)
            quantity = 1
            qty_col = col_mapping.get('quantity')
            if qty_col and qty_col in row and not pd.isna(row[qty_col]):
                try:
                    quantity = int(float(row[qty_col]))
                except ValueError:
                    quantity = 1
                
            # Voeg toe aan database
            add_lego_set(
                set_number=set_num_str,
                name=name,
                purchase_date=purchase_date,
                purchase_price=purchase_price,
                quantity=quantity
            )
            success_count += 1
        except Exception as e:
            errors.append(f"Rij {idx + 2}: {str(e)}")
            
    return success_count, errors
