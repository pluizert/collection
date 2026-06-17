import streamlit as st
import pandas as pd
from datetime import datetime
import os
from PIL import Image

# Importeer hulpfuncties uit utils.py
from utils import (
    init_db,
    add_lego_set,
    get_all_sets,
    delete_set,
    update_set,
    import_excel_or_csv,
    clean_set_number,
    fetch_lego_details_and_image,
    refresh_all_prices,
    create_user,
    update_user,
    delete_user,
    get_all_users,
    verify_user
)

# Initialiseer database
init_db()

# Pagina instellingen
st.set_page_config(
    page_title="Lego Set Voorraadbeheer & Investeringen",
    page_icon="🧱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aangepaste styling voor een modern Lego-thema
st.markdown("""
    <style>
        .main-header {
            color: #E60012;
            font-family: 'Arial Black', Gadget, sans-serif;
            text-shadow: 2px 2px #FFD500;
            font-size: 40px;
            margin-bottom: 20px;
        }
        .lego-card {
            border: 2px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            background-color: #ffffff;
            transition: transform 0.2s;
        }
        .lego-card:hover {
            transform: scale(1.02);
            border-color: #E60012;
        }
        .stButton>button {
            border-radius: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Controleer of er een ingelogde gebruiker is in session state
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

is_admin = False
if st.session_state.logged_in_user is not None:
    is_admin = (st.session_state.logged_in_user['role'] == 'admin')

# Sidebar menu
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/2/24/LEGO_logo.svg", width=100)
st.sidebar.title("🧱 Lego Collector")

menu_options = ["📊 Dashboard", "🧱 Mijn Voorraad"]
if is_admin:
    menu_options += ["➕ Set Toevoegen", "📥 Excel Importeren", "👥 Gebruikersbeheer"]

menu = st.sidebar.radio(
    "Navigatie",
    menu_options
)

# Beheerdersmodus / Wachtwoordbeveiliging in de zijbalk via database
st.sidebar.markdown("---")
st.sidebar.subheader("🔒 Inloggen")

if st.session_state.logged_in_user is None:
    login_username = st.sidebar.text_input("Gebruikersnaam", key="login_username_input")
    login_password = st.sidebar.text_input("Wachtwoord", type="password", key="login_password_input")
    if st.sidebar.button("Inloggen"):
        user = verify_user(login_username, login_password)
        if user:
            st.session_state.logged_in_user = user
            st.sidebar.success(f"Welkom {user['username']}!")
            st.rerun()
        else:
            st.sidebar.error("Onjuiste gegevens!")
else:
    current_user = st.session_state.logged_in_user
    st.sidebar.write(f"Ingehelogd als: **{current_user['username']}** ({current_user['role']})")
    if st.sidebar.button("Uitloggen"):
        st.session_state.logged_in_user = None
        st.rerun()

# Beheerder opties in zijbalk (Alleen tonen als admin)
if is_admin:
    # Ververs knop in sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Ververs Marktprijzen", help="Haalt de allernieuwste huidige prijzen en namen op van Brickset"):
        with st.spinner("Prijzen ophalen van alle sets in je database..."):
            refresh_all_prices()
            st.sidebar.success("Marktprijzen succesvol bijgewerkt!")
            st.rerun()

    # Danger zone in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("<p style='color:red; font-weight:bold;'>⚠️ Danger Zone</p>", unsafe_allow_html=True)
    if st.sidebar.button("🗑️ Wis Volledige Database", help="Verwijdert alle Lego sets en afbeeldingen uit de database"):
        from utils import clear_database
        clear_database()
        st.sidebar.error("Database volledig gewist!")
        st.rerun()

# Functie om veilige weergave van afbeeldingen te garanderen
def get_lego_image_display(image_path):
    if image_path:
        # Vervang backslashes door forward slashes voor Linux/Online compatibiliteit
        normalized_path = image_path.replace('\\', '/')
        if os.path.exists(normalized_path):
            try:
                return Image.open(normalized_path)
            except Exception:
                pass
    # Standaard placeholder
    return "https://images.brickset.com/sets/images/75192-1.jpg" # Leuke Millennium Falcon als fallback

# --- DASHBOARD PAGE ---
if menu == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Mijn Lego Dashboard</h1>", unsafe_allow_html=True)
    
    sets = get_all_sets()
    
    if not sets:
        st.info("Je hebt nog geen Lego sets in je voorraad! Voeg handmatig een set toe of importeer een Excel-bestand.")
        
        # Leuke welkomstboodschap en instructie
        st.markdown("""
        ### Welkom bij je nieuwe Lego Voorraadbeheer App! 🧱
        
        Met deze applicatie kun je eenvoudig:
        1. **Excel/CSV bestanden importeren** met je huidige verzameling.
        2. **Setfoto's, namen en huidige marktprijzen automatisch laten ophalen** op basis van het setnummer.
        3. **Investeringsstatistieken inzien** zoals je totale winst/verlies en het rendement (ROI) van je verzameling!
        
        *Kies een optie in de zijbalk om aan de slag te gaan.*
        """)
    else:
        df = pd.DataFrame(sets)
        
        # Statistieken berekenen
        total_unique_sets = len(df)
        total_items = df['quantity'].sum()
        
        total_investment = (df['purchase_price'] * df['quantity']).sum()
        total_market_value = (df['current_price'] * df['quantity']).sum()
        total_profit = total_market_value - total_investment
        roi = (total_profit / total_investment * 100) if total_investment > 0 else 0.0
        
        # Zoek de duurste set (op basis van huidige marktprijs)
        max_idx = df['current_price'].idxmax()
        most_expensive_set = df.loc[max_idx]['name'] if max_idx in df.index else "Geen"
        most_expensive_price = df.loc[max_idx]['current_price'] if max_idx in df.index else 0.0
        
        # KPI Cards in kolommen
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Totaal Aantal Sets (Uniek / Totaal)", f"{total_unique_sets} uniek / {total_items} stuks")
        with col2:
            st.metric("Totale Aankoopprijs (Investering)", f"€ {total_investment:.2f}")
        with col3:
            st.metric(
                "Huidige Marktwaarde", 
                f"€ {total_market_value:.2f}",
                delta=f"€ {total_profit:.2f} ({roi:+.1f}%)"
            )
        with col4:
            st.metric("Duurste Set (Marktwaarde)", f"€ {most_expensive_price:.2f}", help=most_expensive_set)
            
        st.markdown("---")
        
        # Twee kolommen voor grafieken/overzichten
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("Laatste 5 Aankopen")
            latest_5 = df.head(5)[["set_number", "name", "purchase_date", "purchase_price", "current_price", "quantity"]].copy()
            latest_5["Totaal Aankoop"] = latest_5["purchase_price"] * latest_5["quantity"]
            latest_5["Totaal Waarde"] = latest_5["current_price"] * latest_5["quantity"]
            latest_5["Winst / Verlies"] = latest_5["Totaal Waarde"] - latest_5["Totaal Aankoop"]
            
            # Format overzichtelijke kolommen
            display_5 = latest_5[["set_number", "name", "purchase_date", "Totaal Aankoop", "Totaal Waarde", "Winst / Verlies"]].copy()
            display_5.columns = ["Setnummer", "Naam", "Aankoopdatum", "Investering (€)", "Marktwaarde (€)", "Winst/Verlies (€)"]
            
            st.dataframe(display_5, use_container_width=True, hide_index=True)
            
        with chart_col2:
            st.subheader("Aankoopwaarde vs Huidige Marktwaarde per Jaar")
            df['year'] = pd.to_datetime(df['purchase_date']).dt.year
            df['total_cost'] = df['purchase_price'] * df['quantity']
            df['total_value'] = df['current_price'] * df['quantity']
            
            yearly_stats = df.groupby('year')[['total_cost', 'total_value']].sum().reset_index()
            # Hernoem voor de grafieklegenda
            yearly_stats.columns = ["Jaar", "Investering (€)", "Huidige Marktwaarde (€)"]
            st.bar_chart(yearly_stats, x='Jaar', y=["Investering (€)", "Huidige Marktwaarde (€)"], color=["#FF0000", "#00FF00"])

# --- MIJN VOORRAAD PAGE ---
elif menu == "🧱 Mijn Voorraad":
    st.markdown("<h1 class='main-header'>🧱 Mijn Lego Voorraad</h1>", unsafe_allow_html=True)
    
    sets = get_all_sets()
    
    if not sets:
        st.info("Je hebt nog geen Lego sets in je voorraad. Voeg er een toe!")
    else:
        df = pd.DataFrame(sets)
        
        # Filteren en zoeken
        search_query = st.text_input("🔍 Zoek op setnummer of naam", "")
        
        if search_query:
            filtered_df = df[
                df['set_number'].str.contains(search_query, case=False, na=False) |
                df['name'].str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_df = df
            
        st.write(f"Toont {len(filtered_df)} van de {len(df)} sets")
        
        # Weergave opties: Galerij of Lijst
        view_mode = st.radio("Weergavemodus", ["🖼️ Galerij", "📋 Gedetailleerde Lijst"], horizontal=True)
        
        if view_mode == "🖼️ Galerij":
            # Grid layout voor sets
            cols_per_row = 4
            rows = [filtered_df[i:i + cols_per_row] for i in range(0, len(filtered_df), cols_per_row)]
            
            for row in rows:
                cols = st.columns(cols_per_row)
                for idx, (_, item) in enumerate(row.iterrows()):
                    with cols[idx]:
                        total_cost_item = item['purchase_price'] * item['quantity']
                        total_market_value_item = item['current_price'] * item['quantity']
                        profit_item = total_market_value_item - total_cost_item
                        roi_item = (profit_item / total_cost_item * 100) if total_cost_item > 0 else 0.0
                        
                        profit_color = "#00cc44" if profit_item >= 0 else "#ff3333"
                        
                        st.markdown(f"""
                        <div class="lego-card">
                            <h4 style="margin:0; color:#E60012;">{item['name']}</h4>
                            <p style="margin:5px 0; color:#666;">Set {item['set_number']}</p>
                            <p style="margin:0; font-size: 0.9em;">Aankoopprijs: € {item['purchase_price']:.2f} (x{item['quantity']})</p>
                            <p style="margin:0; font-size: 0.9em;">Huidige marktprijs: € {item['current_price']:.2f}</p>
                            <p style="margin:0; font-weight:bold; color:{profit_color};">
                                Rendement: € {profit_item:+.2f} ({roi_item:+.1f}%)
                            </p>
                            <p style="font-size:0.85em; margin:0; color:#888;">Gekocht: {item['purchase_date']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        img = get_lego_image_display(item['image_path'])
                        st.image(img, use_container_width=True)
                        
                        # Bewerk & Verwijder knoppen onder elke set card (alleen zichtbaar voor admins)
                        if is_admin:
                            with st.expander("Opties ⚙️"):
                                new_price = st.number_input("Aankoopprijs aanpassen", value=float(item['purchase_price']), key=f"p_{item['id']}")
                                new_current_price = st.number_input("Huidige marktprijs aanpassen", value=float(item['current_price']), key=f"cp_{item['id']}")
                                new_retail_price = st.number_input("Adviesprijs (RRP) aanpassen", value=float(item['retail_price']), key=f"rp_{item['id']}")
                                new_qty = st.number_input("Aantal aanpassen", value=int(item['quantity']), min_value=1, step=1, key=f"q_{item['id']}")
                                new_name = st.text_input("Naam aanpassen", value=item['name'], key=f"n_{item['id']}")
                                new_date = st.date_input("Datum aanpassen", value=datetime.strptime(item['purchase_date'], '%Y-%m-%d').date(), key=f"d_{item['id']}")
                                
                                col_upd, col_del = st.columns(2)
                                with col_upd:
                                    if st.button("Opslaan", key=f"save_{item['id']}"):
                                        update_set(item['id'], item['set_number'], new_name, new_date.strftime('%Y-%m-%d'), new_price, new_qty, new_retail_price, new_current_price)
                                        st.success("Opgeslagen!")
                                        st.rerun()
                                with col_del:
                                    if st.button("Verwijderen", key=f"del_{item['id']}"):
                                        delete_set(item['id'])
                                        st.warning("Set verwijderd!")
                                        st.rerun()
                                    
        else:
            # Gedetailleerde lijstweergave
            display_df = filtered_df[["id", "set_number", "name", "purchase_date", "purchase_price", "current_price", "quantity"]].copy()
            display_df["Totaal Aankoop (€)"] = display_df["purchase_price"] * display_df["quantity"]
            display_df["Totaal Marktwaarde (€)"] = display_df["current_price"] * display_df["quantity"]
            display_df["Winst/Verlies (€)"] = display_df["Totaal Marktwaarde (€)"] - display_df["Totaal Aankoop (€)"]
            
            st.dataframe(
                display_df.rename(
                    columns={
                        "set_number": "Setnummer",
                        "name": "Setnaam",
                        "purchase_date": "Aankoopdatum",
                        "purchase_price": "Aankoopprijs (€)",
                        "current_price": "Marktprijs p/s (€)",
                        "quantity": "Aantal"
                    }
                ),
                use_container_width=True,
                hide_index=True
            )
            
            # Acties via dropdown in sidebar of onder de lijst (alleen zichtbaar voor admins)
            if is_admin:
                st.subheader("Set Wijzigen of Verwijderen")
                selected_set_id = st.selectbox(
                    "Kies een set om te bewerken/verwijderen", 
                    options=filtered_df['id'].tolist(),
                    format_func=lambda x: f"Set {filtered_df[filtered_df['id'] == x]['set_number'].values[0]} - {filtered_df[filtered_df['id'] == x]['name'].values[0]}"
                )
                
                if selected_set_id:
                    set_to_edit = filtered_df[filtered_df['id'] == selected_set_id].iloc[0]
                    
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        edit_name = st.text_input("Setnaam", value=set_to_edit['name'], key="edit_name_list")
                        edit_num = st.text_input("Setnummer", value=set_to_edit['set_number'], key="edit_num_list")
                        edit_qty = st.number_input("Aantal stuks", value=int(set_to_edit['quantity']), min_value=1, step=1, key="edit_qty_list")
                    with edit_col2:
                        edit_price = st.number_input("Aankoopprijs p/s (€)", value=float(set_to_edit['purchase_price']), key="edit_price_list")
                        edit_current = st.number_input("Huidige marktprijs p/s (€)", value=float(set_to_edit['current_price']), key="edit_current_list")
                        edit_retail = st.number_input("Adviesprijs (RRP) (€)", value=float(set_to_edit['retail_price']), key="edit_retail_list")
                        edit_date = st.date_input("Aankoopdatum", value=datetime.strptime(set_to_edit['purchase_date'], '%Y-%m-%d').date(), key="edit_date_list")
                    
                    col_btn1, col_btn2 = st.columns([1, 5])
                    with col_btn1:
                        if st.button("Bijwerken", key="update_btn_list"):
                            update_set(selected_set_id, edit_num, edit_name, edit_date.strftime('%Y-%m-%d'), edit_price, edit_qty, edit_retail, edit_current)
                            st.success("Set succesvol bijgewerkt!")
                            st.rerun()
                    with col_btn2:
                        if st.button("Verwijder deze set", key="delete_btn_list", type="primary"):
                            delete_set(selected_set_id)
                            st.warning("Set succesvol verwijderd!")
                            st.rerun()

# --- SET TOEVOEGEN PAGE ---
elif menu == "➕ Set Toevoegen":
    st.markdown("<h1 class='main-header'>➕ Handmatig Lego Set Toevoegen</h1>", unsafe_allow_html=True)
    
    if not is_admin:
        st.warning("⚠️ Beheerdersmodus is niet actief. Voer het juiste wachtwoord in de zijbalk in om sets toe te voegen.")
    
    st.write("Vul de details van je Lego set in. De app probeert automatisch de officiële naam, foto en huidige marktprijzen op te halen!")
    
    with st.form("add_set_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            set_num = st.text_input("Setnummer (bijv. 75192 of 10294)", help="Voer alleen het nummer in, eventuele suffixes zoals -1 worden automatisch behandeld.")
            name = st.text_input("Setnaam (optioneel)", help="Laat leeg om deze automatisch te laten opzoeken op Brickset.")
            quantity = st.number_input("Aantal stuks", min_value=1, value=1, step=1)
            
        with col2:
            purchase_price = st.number_input("Aankoopprijs per stuk (€)", min_value=0.0, step=0.01, format="%.2f")
            purchase_date = st.date_input("Aankoopdatum", value=datetime.today().date())
            
        submitted = st.form_submit_button("Lego Set Toevoegen")
        
        if submitted:
            if not is_admin:
                st.error("Je moet ingelogd zijn als beheerder om sets toe te voegen!")
            elif not set_num:
                st.error("Setnummer is verplicht!")
            else:
                with st.spinner("Gegevens, afbeelding en prijzen ophalen..."):
                    success = add_lego_set(
                        set_number=set_num,
                        name=name if name.strip() else None,
                        purchase_date=purchase_date.strftime('%Y-%m-%d'),
                        purchase_price=purchase_price,
                        quantity=quantity
                    )
                    if success:
                        st.success(f"Set {set_num} ({quantity}x) succesvol toegevoegd aan je voorraad!")
                        st.balloons()
                    else:
                        st.error("Er is iets fout gegaan bij het toevoegen van de set.")

# --- EXCEL IMPORTEREN PAGE ---
elif menu == "📥 Excel Importeren":
    st.markdown("<h1 class='main-header'>📥 Excel / CSV Importeren</h1>", unsafe_allow_html=True)
    
    if not is_admin:
        st.warning("⚠️ Beheerdersmodus is niet actief. Voer het juiste wachtwoord in de zijbalk in om Excel-bestanden te importeren.")
        
    st.write("""
    Heb je je Lego verzameling momenteel in Excel of CSV staan? Upload het bestand hieronder.
    Je kunt zelf aangeven op welke **Sheet** je voorraad staat, en welke kolommen horen bij het **setnummer**, de **aankoopprijs**, de **aankoopdatum**, het **aantal**, en optioneel de **naam**.
    """)
    
    uploaded_file = st.file_uploader("Kies een Excel (.xlsx) of CSV (.csv) bestand", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        try:
            # 1. Behandel Excel Sheets
            sheet_name = None
            if uploaded_file.name.endswith('.xlsx'):
                excel_file_obj = pd.ExcelFile(uploaded_file)
                sheet_names = excel_file_obj.sheet_names
                if len(sheet_names) > 1:
                    sheet_name = st.selectbox("Selecteer het werkblad (Sheet) met jouw voorraad:", options=sheet_names, index=0)
                else:
                    sheet_name = sheet_names[0]
                
                # Herlaad dataframe voor de geselecteerde sheet
                df_preview = pd.read_excel(uploaded_file, sheet_name=sheet_name)
            else:
                df_preview = pd.read_csv(uploaded_file)
                
            st.subheader("Voorbeeld van je bestand (Eerste 5 rijen)")
            st.dataframe(df_preview.head(5), use_container_width=True)
            
            # Kolom mapping formulier
            st.subheader("Kolom Koppeling")
            st.write("Koppel de kolommen uit jouw bestand aan de velden in de app:")
            
            columns = df_preview.columns.tolist()
            
            # Slimme default detectie
            def find_default_col(options, keywords):
                for option in options:
                    if any(kw in option.lower() for kw in keywords):
                        return option
                return options[0] if options else None

            def_set_num = find_default_col(columns, ["setnummer", "nummer set", "set nummer", "set number", "set_num", "set_number", "id"])
            def_price = find_default_col(columns, ["prijs", "price", "stuksprijs", "aankoopprijs", "aankoop", "kosten", "waarde"])
            def_date = find_default_col(columns, ["wanneer gekocht", "datum", "date", "aankoopdatum", "gekocht"])
            def_name = find_default_col(columns, ["naam set", "naam", "name", "titel", "title", "omschrijving"])
            def_qty = find_default_col(columns, ["aantal", "quantity", "qty", "stuks", "aantal stuks"])
            
            col_mapping = {}
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                col_mapping['set_number'] = st.selectbox("Setnummer kolom *", options=columns, index=columns.index(def_set_num) if def_set_num in columns else 0)
                col_mapping['name'] = st.selectbox("Naam kolom (optioneel, kies 'Geen' voor automatische ophalen)", options=["Geen"] + columns, index=columns.index(def_name) + 1 if def_name in columns else 0)
                col_mapping['quantity'] = st.selectbox("Aantal (quantity) kolom (optioneel, kies 'Geen' voor standaard 1)", options=["Geen"] + columns, index=columns.index(def_qty) + 1 if def_qty in columns else 0)
            with col_m2:
                col_mapping['purchase_price'] = st.selectbox("Aankoopprijs kolom *", options=columns, index=columns.index(def_price) if def_price in columns else 0)
                col_mapping['purchase_date'] = st.selectbox("Aankoopdatum kolom *", options=columns, index=columns.index(def_date) if def_date in columns else 0)
                
            if st.button("Start Import", type="primary"):
                if not is_admin:
                    st.error("Je moet ingelogd zijn als beheerder om sets te importeren!")
                else:
                    # Reset file pointer naar het begin
                    uploaded_file.seek(0)
                    
                    # Filter 'Geen' uit mapping
                    mapping = {
                        'set_number': col_mapping['set_number'],
                        'purchase_price': col_mapping['purchase_price'],
                        'purchase_date': col_mapping['purchase_date']
                    }
                    if col_mapping['name'] != "Geen":
                        mapping['name'] = col_mapping['name']
                    if col_mapping['quantity'] != "Geen":
                        mapping['quantity'] = col_mapping['quantity']
                        
                    with st.spinner("Importeren en foto's/marktprijzen downloaden... Dit kan even duren afhankelijk van het aantal sets."):
                        success_count, errors = import_excel_or_csv(uploaded_file, mapping, sheet_name=sheet_name)
                        
                        if success_count > 0:
                            st.success(f"Gereed! Er zijn {success_count} sets succesvol geïmporteerd.")
                            if errors:
                                st.warning(f"Er waren problemen bij {len(errors)} rijen:")
                                for err in errors[:10]:
                                    st.write(f"- {err}")
                                if len(errors) > 10:
                                    st.write("...en meer.")
                            st.balloons()
                            st.info("Ga naar 'Mijn Voorraad' of 'Dashboard' om je geïmporteerde sets te bewonderen!")
                        else:
                            st.error("Er zijn geen sets geïmporteerd. Controleer de kolomkoppelingen.")
                            if errors:
                                for err in errors[:5]:
                                    st.write(err)
        except Exception as e:
            st.error(f"Fout bij het laden van het bestand: {e}")

# --- GEBRUIKERSBEHEER PAGE ---
elif menu == "👥 Gebruikersbeheer":
    st.markdown("<h1 class='main-header'>👥 Gebruikersbeheer</h1>", unsafe_allow_html=True)
    
    if not is_admin:
        st.error("Je hebt geen toegang tot deze pagina.")
    else:
        st.write("Hier kun je nieuwe gebruikers aanmaken, wachtwoorden wijzigen of gebruikers verwijderen.")
        
        # Haal alle gebruikers op
        users_list = get_all_users()
        df_users = pd.DataFrame(users_list)
        
        st.subheader("Bestaande Gebruikers")
        st.dataframe(
            df_users.rename(
                columns={
                    "id": "ID",
                    "username": "Gebruikersnaam",
                    "password": "Wachtwoord",
                    "role": "Rol"
                }
            ),
            use_container_width=True,
            hide_index=True
        )
        
        # Twee kolommen: Toevoegen en Bewerken/Verwijderen
        col_add, col_edit = st.columns(2)
        
        with col_add:
            st.subheader("➕ Gebruiker Toevoegen")
            with st.form("add_user_form", clear_on_submit=True):
                new_username = st.text_input("Gebruikersnaam")
                new_password = st.text_input("Wachtwoord", type="password")
                new_role = st.selectbox("Rol", ["admin", "viewer"])
                
                add_user_submit = st.form_submit_button("Gebruiker Aanmaken")
                if add_user_submit:
                    if not new_username.strip() or not new_password.strip():
                        st.error("Gebruikersnaam en wachtwoord zijn verplicht!")
                    else:
                        success = create_user(new_username.strip(), new_password.strip(), new_role)
                        if success:
                            st.success(f"Gebruiker '{new_username}' succesvol aangemaakt!")
                            st.rerun()
                        else:
                            st.error("Gebruikersnaam bestaat al!")
                            
        with col_edit:
            st.subheader("⚙️ Gebruiker Bewerken of Verwijderen")
            current_logged_in = st.session_state.logged_in_user["username"] if st.session_state.logged_in_user else ""
            
            selected_user = st.selectbox(
                "Selecteer gebruiker",
                options=users_list,
                format_func=lambda x: f"{x['username']} ({x['role']})" + (" (Jij)" if x['username'] == current_logged_in else "")
            )
            
            if selected_user:
                with st.form("edit_user_form"):
                    edit_username = st.text_input("Gebruikersnaam aanpassen", value=selected_user["username"])
                    edit_password = st.text_input("Wachtwoord aanpassen", value=selected_user["password"], type="password")
                    
                    # Voorkom dat de ingelogde beheerder zijn eigen rol per ongeluk wijzigt (bijv. naar viewer)
                    if selected_user["username"] == current_logged_in:
                        st.write(f"Rol: **{selected_user['role']}** *(Je kunt je eigen rol niet wijzigen)*")
                        edit_role = selected_user["role"]
                    else:
                        edit_role = st.selectbox("Rol aanpassen", ["admin", "viewer"], index=0 if selected_user["role"] == "admin" else 1)
                    
                    col_btn_u, col_btn_d = st.columns(2)
                    with col_btn_u:
                        if st.form_submit_button("Wijzigingen Opslaan"):
                            if not edit_username.strip() or not edit_password.strip():
                                st.error("Velden mogen niet leeg zijn!")
                            else:
                                success = update_user(selected_user["id"], edit_username.strip(), edit_password.strip(), edit_role)
                                if success:
                                    # Als we onszelf hebben aangepast, update dan ook de actieve sessie
                                    if selected_user["username"] == current_logged_in:
                                        st.session_state.logged_in_user = {
                                            "id": selected_user["id"],
                                            "username": edit_username.strip(),
                                            "password": edit_password.strip(),
                                            "role": edit_role
                                        }
                                    st.success("Gebruiker succesvol bijgewerkt!")
                                    st.rerun()
                                else:
                                    st.error("Fout bij bijwerken (mogelijk bestaat de gebruikersnaam al)!")
                    with col_btn_d:
                        if selected_user["username"] == current_logged_in:
                            st.write("*(Je kunt jezelf niet verwijderen)*")
                        else:
                            if st.form_submit_button("Gebruiker Verwijderen", type="primary"):
                                delete_user(selected_user["id"])
                                st.warning("Gebruiker verwijderd!")
                                st.rerun()
