import time
from utils import fetch_lego_details_and_image

sets_to_test = [
    "75386", "75387", "75373", "75372", "75412", "75433", 
    "75354", "75393", "75391", "75348", "75437", "75449",
    "75436", "75411", "75379", "75400", "75401", "75333",
    "75349", "75389", "75394", "75356", "75439", "75444", "40917"
]

for s in sets_to_test:
    name, _, rrp, current = fetch_lego_details_and_image(s)
    print(f"Set: {s} | Naam: {name} | RRP: €{rrp} | Current: €{current}")
