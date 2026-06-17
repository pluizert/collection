import requests
import re
from bs4 import BeautifulSoup
from collections import Counter

def scrape_ddg_prices(set_num):
    url = f"https://html.duckduckgo.com/html/?q=lego+{set_num}+kopen"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text()
        
        # Zoek alle euro prijzen, bijv. €39.99, € 39,99, 39.99
        prices = []
        # Matches € 39,99 of €39.99 of EUR 39.99
        matches = re.findall(r'(?:€|EUR)\s*(\d{1,4}[.,]\d{2})', text)
        for m in matches:
            val = float(m.replace(',', '.'))
            if val > 1.0: # Negeer hele kleine bedragen
                prices.append(val)
                
        if prices:
            # Neem degene die het vaakst voorkomt
            most_common = Counter(prices).most_common(1)[0][0]
            print(f"Gevonden prijzen voor {set_num}: {prices}")
            print(f"Meest voorkomende: {most_common}")
            return most_common
    return 0.0

scrape_ddg_prices("75386")
scrape_ddg_prices("75394")
