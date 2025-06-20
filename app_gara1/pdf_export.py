from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Spacer, Paragraph
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd
import io
import os

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
