import streamlit as st
import pandas as pd
from db import get_connection
from streamlit_autorefresh import st_autorefresh

def show_giudice():
    # Autorefresh ogni 10 secondi (10000 ms)
    st_autorefresh(interval=10000, key="refresh_giudice")

    st.markdown("""
        <style>
            .main .block-container {padding-top: 1rem; max-width: 740px;}
            .stTable, .stDataFrame {background: #fcfcfc !important; border-radius: 12px;}
            .stAlert {border-radius: 12px;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #003366;'>Pannello Giudice</h2>", unsafe_allow_html=True)

    params = st.query_params
    codice_param = params.get("giudice", "").strip()

    if not codice_param or len(codice_param) < 5 or not codice_param[-4:].isdigit():
        st.error("Accesso non valido. Assicurati che il link contenga il parametro corretto.")
        return

    cognome_url = codice_param[:-4].strip().replace(" ", "").lower()
    codice = codice_param[-4:]

    conn = get_connection()
    c = conn.cursor()
    try:
        giudice = c.execute(
            "SELECT id, name, surname, apparatus FROM judges WHERE REPLACE(LOWER(surname), ' ', '') = ? AND code = ? LIMIT 1",
            (cognome_url, codice)).fetchone()
        if not giudice:
            st.error("Giudice non trovato o codice errato.")
            return

        giudice_id, nome, cognome_db, attrezzo_orig = giudice

        attrezzi_giudice = c.execute(
            "SELECT DISTINCT apparatus FROM judges WHERE REPLACE(LOWER(surname), ' ', '') = ? AND code = ?",
            (cognome_url, codice)).fetchall()
        attrezzi_lista = [row[0] for row in attrezzi_giudice]

        with st.container():
            st.markdown(
                f"""
                <div style="background-color:#e6f4ea; border-radius:8px; padding:16px; border-left: 6px solid #3ca664; margin-bottom: 16px;">
                    <span style='font-size: 1.3em;'>👋 <b>Benvenuto {nome} {cognome_db.upper()}</b></span><br>
                    <span style='color: #555;'>Puoi inserire punteggi solo per gli attrezzi assegnati: <b>{', '.join(attrezzi_lista)}</b></span>
                </div>
                """, unsafe_allow_html=True
            )

        # Attrezzo selezionabile solo se >1
        if len(attrezzi_lista) > 1:
            selected_attrezzo = st.selectbox(
                "Seleziona attrezzo per questa sessione:",
                attrezzi_lista,
                index=attrezzi_lista.index(attrezzo_orig) if attrezzo_orig in attrezzi_lista else 0,
                key="sel_attrezzo"
            )
        else:
            selected_attrezzo = attrezzi_lista[0]
            st.markdown(
                f"<div style='background-color:#eef6fb; border-left: 4px solid #59a3d6; border-radius:8px; padding:8px; margin-bottom:12px;'>"
                f"🛠️ <b>Attrezzo assegnato:</b> {selected_attrezzo}</div>",
                unsafe_allow_html=True
            )

        # Rotazione corrente
        rotazione_corrente = int(c.execute("SELECT value FROM state WHERE key = 'rotazione_corrente'").fetchone()[0])

        # --- Elenco atleti in rotazione corrente per l'attrezzo selezionato ---
        atleti_rotazione = c.execute("""
            SELECT r.athlete_id, a.name || ' ' || a.surname AS Atleta
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
            ORDER BY r.id
        """, (selected_attrezzo, rotazione_corrente)).fetchall()

        # --- Punteggi già assegnati dal giudice ---
        punteggi_assegnati = c.execute("""
            SELECT s.athlete_id, a.name || ' ' || a.surname AS Atleta, s.apparatus AS Attrezzo, s.score AS Punteggio
            FROM scores s
            JOIN athletes a ON a.id = s.athlete_id
            WHERE s.judge_id = ?
              AND s.apparatus = ?
              AND s.athlete_id IN (
                  SELECT athlete_id FROM rotations WHERE apparatus = ? AND rotation_order = ?
              )
            ORDER BY Atleta
        """, (giudice_id, selected_attrezzo, selected_attrezzo, rotazione_corrente)).fetchall()

        # --- Costruzione DataFrame "pulita" con badge simbolici e highlight ---
        if atleti_rotazione:
            id_valutati = {row[0] for row in punteggi_assegnati}
            nomi_valutati = {row[1]: row[3] for row in punteggi_assegnati}  # nome: punteggio

            table = []
            for athlete_id, nome_atleta in atleti_rotazione:
                stato = "Valutato" if athlete_id in id_valutati else "Da valutare"
                punteggio = nomi_valutati.get(nome_atleta, "")
                table.append({
                    "Atleta": nome_atleta,
                    "Punteggio": punteggio if punteggio != "" else "-",
                    "Stato": "✓ Valutato" if stato == "Valutato" else "⏳ Da valutare"
                })
            df_all = pd.DataFrame(table)

            def highlight_row(row):
                # Valutato e punteggio 0
                if "Valutato" in row["Stato"]:
                    p = str(row["Punteggio"]).replace(",", ".").strip()
                    if p in {"0", "0.0"}:
                        return [
                            "background-color: #ffeaea; color: #bb2222; font-weight: 700;",
                            "background-color: #ffeaea; color: #bb2222; font-weight: 700;",
                            "background-color: #ffeaea; color: #bb2222; font-weight: 700;"
                        ]
                    return [
                        "background-color: #e1ffe1;",
                        "background-color: #e1ffe1;",
                        "background-color: #e1ffe1;"
                    ]
                # Da valutare
                return [
                    "background-color: #ffeedd;",
                    "background-color: #ffeedd;",
                    "background-color: #ffeedd;"
                ]

            st.markdown("### <span style='color: #235;'>Situazione atleti nella rotazione corrente</span>", unsafe_allow_html=True)
            st.dataframe(
                df_all.style.apply(highlight_row, axis=1),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nessun atleta assegnato per questa rotazione.")

        # --- Solo atleti non ancora valutati per inserimento punteggio ---
        rotazioni = c.execute("""
            SELECT r.id, a.name || ' ' || a.surname
            FROM rotations r
            JOIN athletes a ON a.id = r.athlete_id
            WHERE r.apparatus = ? AND r.rotation_order = ?
              AND r.athlete_id NOT IN (
                  SELECT athlete_id FROM scores
                  WHERE judge_id = ? AND apparatus = ?
              )
            ORDER BY r.id
        """, (selected_attrezzo, rotazione_corrente, giudice_id, selected_attrezzo)).fetchall()

        if not rotazioni:
            st.markdown(
                f"<div style='background-color:#e6f4ea; border-radius:8px; padding:14px 12px; border-left: 6px solid #3ca664; margin-bottom:16px;'>"
                f"<span style='font-size:1.1em;'>✅ Hai già valutato tutti gli atleti su <b>{selected_attrezzo}</b> in questa rotazione! 👏</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            return

        with st.form("form_punteggio"):
            st.markdown(f"#### <span style='color:#003366'>Inserisci punteggio per <b>{selected_attrezzo}</b></span>",
                        unsafe_allow_html=True)
            selected_rotation = st.selectbox("Seleziona atleta", rotazioni, format_func=lambda x: x[1],
                                             key="sel_atleta")
            d = st.number_input("Difficulty (D)", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")
            e = st.number_input("Execution (E)", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")
            penalty = 0.0  # default sempre zero per ora

            punteggio = round(d + e - penalty, 3)

            # Session key unica per la conferma zero di questo atleta+attrezzo+rotazione
            confirm_key = f"conferma_zero_{selected_rotation[0]}_{selected_attrezzo}_{rotazione_corrente}"
            conferma_zero = st.session_state.get(confirm_key, False)

            submit = st.form_submit_button("Invia punteggio")

            if submit:
                if punteggio == 0.0 and not conferma_zero:
                    st.session_state[confirm_key] = True
                    st.warning(
                        "⚠️ Hai assegnato 0 punti. Premi di nuovo 'Invia punteggio' per confermare il punteggio 0.")
                    st.stop()  # Blocca l'invio, serve una seconda conferma
                rot_id = selected_rotation[0]
                row = c.execute("SELECT athlete_id FROM rotations WHERE id = ?", (rot_id,)).fetchone()
                if not row:
                    st.error("Errore interno, riprovare.")
                else:
                    atleta_id = row[0]
                    existing = c.execute("""
                        SELECT 1 FROM scores
                        WHERE athlete_id = ? AND apparatus = ? AND judge_id = ?
                    """, (atleta_id, selected_attrezzo, giudice_id)).fetchone()

                    if existing:
                        st.warning("Hai già assegnato un punteggio a questo atleta.")
                    else:
                        c.execute("""
                            INSERT INTO scores (apparatus, athlete_id, judge_id, d, e, penalty, score)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (selected_attrezzo, atleta_id, giudice_id, d, e, penalty, punteggio))
                        conn.commit()
                        if punteggio == 0.0:
                            st.markdown(
                                "<div style='background-color:#fff7e0; border-left: 6px solid #ffe066; border-radius:8px; padding:12px 10px; margin-bottom:10px;'>"
                                "⚠️ <b>Hai assegnato <span style='color:#ba2020;'>0</span> punti.</b> "
                                "Se l'atleta è assente o la prova è nulla, hai confermato il punteggio."
                                "</div>",
                                unsafe_allow_html=True
                            )
                        st.markdown(
                            f"<div style='background-color:#e6f4ea; border-radius:8px; padding:14px 12px; border-left: 6px solid #3ca664; margin-bottom:10px;'>"
                            f"<span style='font-size:1.1em;'>✅ Punteggio <b>{punteggio:.2f}</b> inserito per <b>{selected_rotation[1]}</b> su <b>{selected_attrezzo}</b>.</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        # Reset conferma dopo salvataggio
                        if punteggio == 0.0:
                            st.session_state[confirm_key] = False


    finally:
        conn.close()
