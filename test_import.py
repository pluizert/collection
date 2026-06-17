import os
from utils import init_db, import_excel_or_csv, get_all_sets

def run_test():
    print("Test starten...")
    
    # Initialiseer DB
    init_db()
    print("Database geïnitialiseerd.")
    
    # Kolom mapping
    col_mapping = {
        'set_number': 'Set Nummer',
        'name': 'Naam',
        'purchase_price': 'Aankoopprijs',
        'purchase_date': 'Aankoopdatum'
    }
    
    excel_file = "lego_sets_voorbeeld.xlsx"
    if not os.path.exists(excel_file):
        print("Fout: Voorbeeld excel-bestand niet gevonden!")
        return
        
    print(f"Excel bestand {excel_file} wordt geïmporteerd...")
    success_count, errors = import_excel_or_csv(excel_file, col_mapping)
    
    print(f"Import voltooid: {success_count} sets succesvol, {len(errors)} fouten.")
    
    all_sets = get_all_sets()
    print(f"Aantal sets nu in database: {len(all_sets)}")
    
    for idx, s in enumerate(all_sets):
        print(f"Set {idx + 1}: Num: {s['set_number']}, Naam: {s['name']}, Prijs: €{s['purchase_price']}, Datum: {s['purchase_date']}, Afbeelding pad: {s['image_path']}")
        if s['image_path']:
            print(f"  -> Afbeelding bestaat lokaal: {os.path.exists(s['image_path'])}")

if __name__ == "__main__":
    run_test()
