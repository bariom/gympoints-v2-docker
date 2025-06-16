
import streamlit as st
import pandas as pd
from db import get_connection
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import io

def generate_pdf(df, nome_gara="Gara Ginnastica Artistica", data_gara="Data Gara"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph(f"<b>{nome_gara}</b>", styles['Title'])
    subtitle = Paragraph(f"<i>{data_gara}</i>", styles['Normal'])

    elements.append(title)
    elements.append(subtitle)
    elements.append(Spacer(1, 20))

    # Header tabella
    data = [['#', 'Atleta', 'Club', 'D', 'E', 'Totale']]

    # Righe punteggi
    for i, row in enumerate(df.itertuples(index=False), start=1):
        data.append([
            i,
            row.Atleta,
            row.Club,
            f"{row.D:.1f}" if row.D is not None else "-",
            f"{row.E:.1f}" if row.E is not None else "-",
            f"{row.Totale:.3f}"
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))

    elements.append(table)
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def export_pdf_results():
    st.title("Generazione Report PDF Risultati")

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

    if st.button("Genera PDF"):
        pdf_bytes = generate_pdf(df)
        st.download_button(
            label="Scarica Report PDF",
            data=pdf_bytes,
            file_name='risultati_ufficiali.pdf',
            mime='application/pdf'
        )

    conn.close()
