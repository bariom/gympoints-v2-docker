from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Spacer, Paragraph
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd
import io
import os

def costruisci_df_classifica(attrezzi=None):
    if attrezzi is None:
        attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Parallele", "Sbarra", "Volteggio"]

    conn = get_connection()
    query = """
        SELECT 
            a.id AS atleta_id,
            a.name AS Nome,
            a.surname AS Cognome,
            a.birth_year AS Anno,
            a.club AS Società,
            s.apparatus AS Attrezzo,
            s.d AS D,
            s.score AS TotaleParziale
        FROM athletes a
        LEFT JOIN scores s ON a.id = s.athlete_id
    """
    df_raw = pd.read_sql_query(query, conn)
    conn.close()

    df_pivot_d = df_raw.pivot_table(index=['Cognome', 'Nome', 'Anno', 'Società'],
                                    columns='Attrezzo', values='D', aggfunc='first')
    df_pivot_t = df_raw.pivot_table(index=['Cognome', 'Nome', 'Anno', 'Società'],
                                    columns='Attrezzo', values='TotaleParziale', aggfunc='first')

    df_pivot_d.columns = [f"{col}_D" for col in df_pivot_d.columns]
    df_pivot_t.columns = [f"{col}_Tot" for col in df_pivot_t.columns]

    df = pd.concat([df_pivot_d, df_pivot_t], axis=1).reset_index()

    # Ordina colonne secondo attrezzi
    ordered_cols = ['Cognome', 'Nome', 'Anno', 'Società']
    for a in attrezzi:
        ordered_cols.append(f"{a}_D")
        ordered_cols.append(f"{a}_Tot")
    df = df.reindex(columns=[col for col in ordered_cols if col in df.columns])

    # Calcolo totale
    df['Totale'] = df[[c for c in df.columns if c.endswith("_Tot")]].sum(axis=1, skipna=True)
    df = df.sort_values(by="Totale", ascending=False).reset_index(drop=True)

    return df

def export_pdf_results():
    st.title("Classifica Federale - Esportazione PDF")

    attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Parallele", "Sbarra", "Volteggio"]
    df = costruisci_df_classifica(attrezzi)

    st.dataframe(df, use_container_width=True)

    if st.button("Genera PDF"):
        pdf_bytes = generate_official_pdf(df, attrezzi=attrezzi)
        st.download_button(
            label="📥 Scarica Report PDF",
            data=pdf_bytes,
            file_name="classifica_gam.pdf",
            mime="application/pdf"
        )

def generate_official_pdf(df, attrezzi=None, logo_path=None, gara_title="Classifica GAM Introduzione"):
    if attrezzi is None:
        attrezzi = ["Suolo", "Cavallo a maniglie", "Anelli", "Parallele", "Sbarra", "Volteggio"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20
    )
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph(gara_title, styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Percorsi delle icone attrezzi
    icon_paths = [os.path.join("img", f"{a}.png") for a in attrezzi]

    # Prima riga intestazioni
    headers = ["Rg.", "Cognome", "Nome", "Anno", "Società"]
    for path in icon_paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                img = RLImage(io.BytesIO(f.read()), width=24, height=24)
                headers.append(img)
        else:
            headers.append(" ")
    headers.append("Totale")

    # Seconda riga sotto intestazione
    sublabels = ["", "", "", "", ""]
    for a in attrezzi:
        sublabels.append("D\nTot")
    sublabels.append("")

    # Composizione righe
    table_data = [headers, sublabels]
    for i, row in enumerate(df.itertuples(index=False), start=1):
        riga = [
            i,
            getattr(row, "Cognome", ""),
            getattr(row, "Nome", ""),
            getattr(row, "Anno", ""),
            getattr(row, "Società", "")
        ]
        for a in attrezzi:
            d_val = getattr(row, f"{a}_D", "-")
            t_val = getattr(row, f"{a}_Tot", "-")
            d_fmt = f"{d_val:.1f}" if isinstance(d_val, (int, float)) else "-"
            t_fmt = f"{t_val:.3f}" if isinstance(t_val, (int, float)) else "-"
            riga.append(f"{d_fmt}\n{t_fmt}")
        riga.append(f"{row.Totale:.3f}")
        table_data.append(riga)

    # Tabella
    table = Table(table_data, repeatRows=2)
    table.setStyle(TableStyle([
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (2,1)),
        ('SPAN', (3,0), (3,1)), ('SPAN', (4,0), (4,1)), ('SPAN', (-1,0), (-1,1)),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.4, colors.grey),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
