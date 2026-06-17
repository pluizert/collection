import re

def parse_brickset_fields(rrp_text, current_val_text):
    retail_price = 0.0
    current_price = 0.0
    
    # Parse RRP for Euro symbol €
    if rrp_text:
        # Zoek bijv. naar €39.99 of 39.99€ of 39,99€
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
        # Meestal: "New: ~€24" of "New: ~790" of "New: ~$790"
        # We zoeken specifiek naar New: ~€... of New: ~$ ...
        # Match "New:" gevolgd door eventuele spaties, ~, en dan € of $ en getallen
        match_new_eu = re.search(r'New:\s*~?\s*€\s*(\d+(?:[.,]\d+)?)', current_val_text)
        if match_new_eu:
            current_price = float(match_new_eu.group(1).replace(',', '.'))
        else:
            # Fallback naar Dollar of Pond
            match_new_any = re.search(r'New:\s*~?\s*(?:\$|£)?\s*(\d+(?:[.,]\d+)?)', current_val_text)
            if match_new_any:
                current_price = float(match_new_any.group(1).replace(',', '.'))
                
    # Fallback: Als we geen current_price hebben maar wel retail_price, of vice versa
    if current_price == 0.0 and retail_price > 0.0:
        current_price = retail_price
        
    return retail_price, current_price

# Test cases
print(parse_brickset_fields("£34.99, $39.99, €39.99", "New: ~€24\n                Used: ~€21"))
print(parse_brickset_fields("£734.99, $849.99, 849.99€", "New: ~$790\nUsed: ~$630"))
print(parse_brickset_fields("€149.99", None))
