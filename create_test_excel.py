import pandas as pd

# Maak een voorbeeld dataframe
data = {
    "Set Nummer": [75192, 10294, 21330, 10305, 10497],
    "Naam": ["Millennium Falcon", "Titanic", "Home Alone", "Lion Knights' Castle", "Galaxy Explorer"],
    "Aankoopprijs": [799.99, 649.99, 299.99, 399.99, 99.99],
    "Aankoopdatum": ["2026-01-10", "2026-02-14", "2026-03-01", "2026-04-20", "2026-05-05"]
}

df = pd.DataFrame(data)

# Sla op als Excel-bestand
excel_file = "lego_sets_voorbeeld.xlsx"
df.to_excel(excel_file, index=False)

print(f"Voorbeeld Excel-bestand is succesvol aangemaakt: {excel_file}")
