import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import qrcode
import io
import time
import json
import zipfile
import os
import base64
import datetime
from db import get_connection
from PIL import Image
from exporter import export_results_detailed
from pdf_export import export_pdf_results


# Utility immagine base64

def image_to_base64(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def mostra_logo(titolo):
    logo_path = os.path.join("img", "logo.png")
    if os.path.exists(logo_path):
        logo_b64 = image_to_base64(logo_path)
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <img src="data:image/png;base64,{logo_b64}" alt="Gympoints Logo" style="height:160px;"/>
                <h1 style="margin: 0; padding: 0;">{titolo}</h1>
            </div>
            <hr style="margin-top: 10px;"/>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning(f"Logo non trovato: {os.path.abspath(logo_path)}")
        st.title(titolo)

# Genera codice giudice univoco
def genera_codice_giudice(nome: str, cognome: str) -> str:
    combinazione = f"{nome.lower()}_{cognome.lower()}"
    hash_val = hashlib.sha256(combinazione.encode()).hexdigest()
    code = int(hash_val[:4], 16) % 10000
    return str(code).zfill(4)


# Esportazione completa gara in ZIP
def export_full_competition():
    conn = get_connection()
    c = conn.cursor()
    data = {}

    for table in ['athletes', 'judges', 'rotations', 'state']:
        c.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in c.description]
        rows = c.fetchall()
        data[table] = [dict(zip(columns, row)) for row in rows]

    conn.close()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"gara_export_{timestamp}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for table, content in data.items():
            json_bytes = json.dumps(content, indent=2).encode('utf-8')
            zipf.writestr(f"{table}.json", json_bytes)

    with open(zip_filename, "rb") as f:
        st.download_button("Download Dati Gara", f.read(), file_name=zip_filename, mime="application/zip")

    os.remove(zip_filename)


# Importazione completa gara da ZIP
def import_full_competition(uploaded_zip):
    with zipfile.ZipFile(uploaded_zip, 'r') as zipf:
        files = zipf.namelist()
        conn = get_connection()
        c = conn.cursor()
        for file in files:
            table = file.replace('.json', '')
            with zipf.open(file) as f:
                content = json.load(f)
                c.execute(f"DELETE FROM {table}")
                if content:
                    columns = content[0].keys()
                    placeholders = ", ".join(["?"] * len(columns))
                    for row in content:
                        values = tuple(row[col] for col in columns)
                        c.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})", values)
        conn.commit()
        conn.close()
    st.success("Dati di gara importati correttamente")


# Reset completo DB
def reset_database():
    conn = get_connection()
    c = conn.cursor()
    for table in ['scores', 'rotations', 'judges', 'athletes', 'state']:
        c.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    st.success("Database resettato con successo")


# MAIN ADMIN
def show_admin():
    # CSS per alzare il logo
    st.markdown("""
        <style>
        /* Riduce il padding globale */
        .main .block-container {
            padding-top: 0rem !important;
        }

        /* Nasconde l'header Streamlit (menu hamburger, ecc.) */
        header {
            visibility: hidden;
            height: 0px !important;
        }

        /* Rimuove margine tra top della pagina e primo blocco */
        section.main > div:first-child {
            margin-top: 0rem !important;
            padding-top: 0rem !important;
        }

        /* Rimuove margini invisibili auto-generati */
        div.block-container:before,
        div.block-container:after {
            content: none !important;
            height: 0px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    mostra_logo("")
    # ---- Login Admin ----
    def check_credentials(username, password):
        # Inserisci qui i tuoi utenti e password (meglio hashate in futuro)
        valid_users = {
            "admin": "supersegreta123",  # puoi usare anche un hash qui
        }
        return valid_users.get(username) == password

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        st.title("Accesso Amministrazione")
        with st.form("login_form"):
            username = st.text_input("Utente")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                if check_credentials(username, password):
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Credenziali non valide.")
        return  # blocca l'accesso al resto della pagina

    st.title("Amministrazione Gara")

    conn = get_connection()
    c = conn.cursor()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Atleti", "Giudici", "Rotazioni", "Esportazioni", "Stato Gara", "Impostazioni Gara", "Backup & Restore"])

    # --- GESTIONE ATLETI ---
    with tab1:
        st.subheader("Gestione Atleti")
        if st.button("Esporta elenco atleti in CSV"):
            df = pd.read_sql_query("SELECT name, surname, club, category FROM athletes", conn)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "atleti.csv", "text/csv")

        uploaded_file = st.file_uploader("Importa elenco atleti da CSV", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                exists = c.execute(
                    "SELECT 1 FROM athletes WHERE name = ? AND surname = ? AND club = ? AND category = ?",
                    (row['name'], row['surname'], row['club'], row['category'])).fetchone()
                if not exists:
                    c.execute("INSERT INTO athletes (name, surname, club, category) VALUES (?, ?, ?, ?)",
                              (row['name'], row['surname'], row['club'], row['category']))
            conn.commit()
            st.success("Atleti importati correttamente")

        with st.form("add_athlete"):
            name = st.text_input("Nome")
            surname = st.text_input("Cognome")
            club = st.text_input("Società")
            category = st.text_input("Categoria")
            if st.form_submit_button("Aggiungi atleta"):
                c.execute("INSERT INTO athletes (name, surname, club, category) VALUES (?, ?, ?, ?)",
                          (name, surname, club, category))
                conn.commit()

        st.dataframe(c.execute("SELECT * FROM athletes").fetchall(), use_container_width=True)

    # --- GESTIONE GIUDICI ---
    with tab2:
        st.subheader("Gestione Giudici")
        with st.form("add_judge"):
            name = st.text_input("Nome Giudice")
            surname = st.text_input("Cognome Giudice")
            apparatus = st.selectbox("Attrezzo",
                                     ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"])
            if st.form_submit_button("Aggiungi giudice"):
                code = genera_codice_giudice(name, surname)
                c.execute("INSERT INTO judges (name, surname, apparatus, code) VALUES (?, ?, ?, ?)",
                          (name, surname, apparatus, code))
                conn.commit()
                st.success(f"Giudice aggiunto. Codice accesso: {code}")
                st.rerun()

        df_giudici = pd.read_sql_query("SELECT name, surname, apparatus, code FROM judges ORDER BY surname, name", conn)
        st.dataframe(df_giudici, use_container_width=True)

        assegnazioni = c.execute(
            "SELECT id, name, surname, apparatus, code FROM judges ORDER BY surname, name, apparatus").fetchall()
        if assegnazioni:
            labels = [f"{row[1]} {row[2]} – {row[3]} [codice: {row[4]}]" for row in assegnazioni]
            id_map = {label: row[0] for label, row in zip(labels, assegnazioni)}
            selected_label = st.selectbox("Modifica/elimina assegnazione:", labels)
            if selected_label:
                judge_id = id_map[selected_label]
                current_row = next(row for row in assegnazioni if row[0] == judge_id)
                nome_corr, cognome_corr, apparatus_corr = current_row[1], current_row[2], current_row[3]
                with st.form("edit_judge"):
                    new_name = st.text_input("Nome", value=nome_corr)
                    new_surname = st.text_input("Cognome", value=cognome_corr)
                    new_apparatus = st.selectbox("Attrezzo",
                                                 ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele",
                                                  "Sbarra"],
                                                 index=["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio",
                                                        "Parallele", "Sbarra"].index(apparatus_corr))
                    delete = st.checkbox("Elimina questa assegnazione")
                    submitted = st.form_submit_button("Applica modifiche")
                    if submitted:
                        if delete:
                            c.execute("DELETE FROM judges WHERE id = ?", (judge_id,))
                        else:
                            code = genera_codice_giudice(new_name, new_surname)
                            c.execute("UPDATE judges SET name = ?, surname = ?, apparatus = ?, code = ? WHERE id = ?",
                                      (new_name, new_surname, new_apparatus, code, judge_id))
                        conn.commit()
                        st.success("Modifica eseguita.")
                        st.rerun()
        else:
            st.info("Nessuna assegnazione giudice da modificare.")


        # Ricaviamo dinamicamente il base URL dall'ambiente Streamlit
        try:
            url_base = st.request.base_url
        except:
            url_base = "https://gara1.gympoints.ch"  # fallback

        st.subheader("QR Code di accesso giudici")

        # Ricaviamo dinamicamente il base URL dall'ambiente Streamlit
        try:
            url_base = st.request.base_url
        except:
            url_base = "https://gara1.gympoints.ch"  # fallback

        # Recuperiamo i giudici dal DB
        giudici = c.execute("SELECT name, surname, code FROM judges ORDER BY surname, name").fetchall()

        # Se non ci sono giudici
        if not giudici:
            st.info("Nessun giudice inserito.")
        else:
            opzioni = [f"{name} {surname} (Codice: {code})" for name, surname, code in giudici]
            opzione_selezionata = st.selectbox("Seleziona il giudice per il QR code", opzioni, index=0)

            indice = opzioni.index(opzione_selezionata)
            name, surname, code = giudici[indice]

            giudice_key = f"{surname.strip().lower()}{code}"
            full_url = f"{url_base}?giudice={giudice_key}"

            qr_img = qrcode.make(full_url)
            buf = io.BytesIO()
            qr_img.save(buf)
            buf.seek(0)

            st.image(buf, caption=f"{name} {surname}", width=200)

    # --- GESTIONE ROTAZIONI ---
    with tab3:
        st.subheader("Gestione Rotazioni")
        attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Volteggio", "Parallele", "Sbarra"]
        athletes = c.execute("SELECT id, name || ' ' || surname || ' (' || club || ')' FROM athletes").fetchall()

        with st.form("add_rotation"):
            athlete_id = st.selectbox("Atleta", athletes, format_func=lambda x: x[1])
            apparatus = st.selectbox("Attrezzo", attrezzi)
            rotation_order = st.number_input("Ordine di rotazione", min_value=1, step=1)
            if st.form_submit_button("Aggiungi rotazione"):
                c.execute("INSERT INTO rotations (apparatus, athlete_id, rotation_order) VALUES (?, ?, ?)",
                          (apparatus, athlete_id[0], rotation_order))
                conn.commit()
                st.success("Rotazione aggiunta")

        rot_table = c.execute("""
            SELECT r.id, r.apparatus, a.name || ' ' || a.surname AS atleta, r.rotation_order
            FROM rotations r JOIN athletes a ON a.id = r.athlete_id
            ORDER BY r.rotation_order, r.apparatus, r.id
        """).fetchall()
        st.dataframe(rot_table, use_container_width=True)

        if st.button("Reset completo rotazioni"):
            c.execute("DELETE FROM rotations")
            conn.commit()
            st.success("Tutte le rotazioni eliminate")
        # PREVIEW rotazioni olimpiche
        st.markdown("### Preview rotazioni olimpiche 2–6")
        gruppi = []
        for att in attrezzi:
            ids = c.execute("""
                SELECT a.name || ' ' || a.surname
                FROM rotations r
                JOIN athletes a ON a.id = r.athlete_id
                WHERE r.rotation_order = 1 AND r.apparatus = ?
                ORDER BY r.id
            """, (att,)).fetchall()
            gruppi.append([x[0] for x in ids])

        for rot in range(2, 7):
            gruppi = [g[1:] + g[:1] if g else [] for g in gruppi]
            gruppi = gruppi[-1:] + gruppi[:-1]
            st.markdown(f"#### Rotazione {rot}")
            for att, gruppo in zip(attrezzi, gruppi):
                st.markdown(f"**{att}**:")
                if gruppo:
                    for idx, name in enumerate(gruppo, start=1):
                        st.write(f"{idx}. {name}")
                else:
                    st.write("_(vuoto)_")

        if st.button("Genera rotazioni olimpiche 2–6"):
            gruppi_db = []
            for att in attrezzi:
                ids = c.execute("""
                    SELECT athlete_id
                    FROM rotations
                    WHERE rotation_order = 1 AND apparatus = ?
                    ORDER BY id
                """, (att,)).fetchall()
                gruppi_db.append([x[0] for x in ids])

            for rot in range(2, 7):
                gruppi_db = [g[1:] + g[:1] if g else [] for g in gruppi_db]
                gruppi_db = gruppi_db[-1:] + gruppi_db[:-1]
                for att, gruppo in zip(attrezzi, gruppi_db):
                    for athlete_id in gruppo:
                        c.execute("INSERT INTO rotations (apparatus, athlete_id, rotation_order) VALUES (?, ?, ?)",
                                  (att, athlete_id, rot))
            conn.commit()
            st.success("Rotazioni olimpiche 2–6 generate")

    # --- ESPORTAZIONI STANDARD ---
    with tab4:
        st.subheader("Esportazioni")
        export_results_detailed()
        export_pdf_results()

    # --- STATO GARA ---
    with tab5:
        st.subheader("Stato gara")
        rotazione_corrente = c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()
        rotazione_corrente = int(rotazione_corrente[0]) if rotazione_corrente else 1
        nuova_rotazione = st.number_input("Rotazione corrente:", min_value=1, step=1, value=rotazione_corrente)
        if st.button("Aggiorna rotazione"):
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", ("rotazione_corrente", str(nuova_rotazione)))
            conn.commit()
            st.success("Rotazione aggiornata")

        logica_attuale = c.execute("SELECT value FROM state WHERE key = 'logica_classifica'").fetchone()
        logica_attuale = logica_attuale[0] if logica_attuale else "incrementale"
        nuova_logica = st.radio("Logica classifica:", ["incrementale", "olimpica"],
                                index=0 if logica_attuale == "incrementale" else 1)
        if st.button("Salva logica classifica"):
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", ("logica_classifica", nuova_logica))
            conn.commit()
            st.success("Logica aggiornata")

    # --- IMPOSTAZIONI GARA ---
    with tab6:
        st.subheader("Impostazioni generali")
        nome_comp = c.execute("SELECT value FROM state WHERE key = 'nome_competizione'").fetchone()
        nome_comp = nome_comp[0] if nome_comp else ""
        nome_gara = st.text_input("Nome competizione:", value=nome_comp)

        show_ranking_live = c.execute("SELECT value FROM state WHERE key = 'show_ranking_live'").fetchone()
        show_ranking_live = show_ranking_live[0] == "1" if show_ranking_live else False
        show_ranking_toggle = st.toggle("Mostra classifica nel Live", value=show_ranking_live)

        show_final_ranking = c.execute("SELECT value FROM state WHERE key = 'show_final_ranking'").fetchone()
        show_final_ranking = show_final_ranking[0] == "1" if show_final_ranking else False
        show_final_toggle = st.toggle("Mostra classifica finale", value=show_final_ranking)

        if st.button("Salva impostazioni gara"):
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)", ("nome_competizione", nome_gara))
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)",
                      ("show_ranking_live", "1" if show_ranking_toggle else "0"))
            c.execute("REPLACE INTO state (key, value) VALUES (?, ?)",
                      ("show_final_ranking", "1" if show_final_toggle else "0"))
            conn.commit()
            st.success("Impostazioni aggiornate")

    # --- BACKUP & RESTORE ---
    with tab7:
        st.subheader("Backup e Restore Gara Completa")

        if st.button("Esporta Gara Completa"):
            export_full_competition()

        uploaded_zip = st.file_uploader("Importa dati gara (zip)", type="zip")
        if uploaded_zip:
            import_full_competition(uploaded_zip)

        if st.button("Reset Completo Database"):
            reset_database()

    conn.close()
