
import streamlit as st
import pandas as pd
import io
from db import get_connection

def export_results_detailed():
    st.title("Esportazione Risultati Dettagliati (D/E)")

    conn = get_connection()
    c = conn.cursor()

    df = pd.read_sql_query("""
        SELECT a.name || ' ' || a.surname AS Atleta,
               a.club AS Club,
               s.d AS D,
               s.e AS E,
               s.score AS Totale
        FROM scores s
        JOIN athletes a ON a.id = s.athlete_id
        ORDER BY Totale DESC
    """, conn)

    st.dataframe(df, use_container_width=True)

    # Download CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Scarica CSV",
        data=csv,
        file_name='risultati_dettagliati.csv',
        mime='text/csv'
    )

    # Download XLSX
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Risultati Dettagliati', index=False)
    buffer.seek(0)
    st.download_button(
        label="Scarica Excel",
        data=buffer.getvalue(),
        file_name='risultati_dettagliati.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    conn.close()
