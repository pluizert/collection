import requests
from bs4 import BeautifulSoup
import re

url = "https://www.brickwatch.net/nl-NL/set/75386/a.html"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
print(resp.status_code)
if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, 'html.parser')
    text = soup.get_text()
    matches = re.findall(r'€\s*(\d{1,4}[.,]\d{2})', text)
    print("Prijzen:", matches)
