import streamlit as st
import math
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="Calculadora Solar & Cotizador", layout="wide", page_icon="☀️")

# ==========================================
# 1. CATALOGOS PREDEFINIDOS Y TABLAS NOM-001
# ==========================================
PANEL_CATALOG = {
    "Osda 550W Bifacial (Vmp: 42.1V, Imp: 13.06A, Voc: 49.8V, Isc: 13.98A)": {
        "p_watts": 550.0, "vmp": 42.1, "imp": 13.06, "voc": 49.8, "isc": 13.98, "temp_coeff_voc": -0.28
    },
    "Tier 1 580W Monocristalino (Vmp: 42.8V, Imp: 13.55A, Voc: 51.2V, Isc: 14.32A)": {
        "p_watts": 580.0, "vmp": 42.8, "imp": 13.55, "voc": 51.2, "isc": 14.32, "temp_coeff_voc": -0.27
    },
    "Tier 1 660W Alto Rendimiento (Vmp: 38.3V, Imp: 17.23A, Voc: 45.9V, Isc: 18.25A)": {
        "p_watts": 660.0, "vmp": 38.3, "imp": 17.23, "voc": 45.9, "isc": 18.25, "temp_coeff_voc": -0.26
    }
}

INVERTER_CATALOG = {
    "Microinversor Hoymiles HMS-2000-4T (4 Entradas MPPT, 2000W, 220V CA)": {
        "tipo": "micro", "potencia": 2000.0, "vac": 220, "fases": 2, "modulos_max": 4, "eficiencia": 0.965
    },
    "Microinversor Hoymiles HMT-2250-6T (Trifásico 220V CA, 2250W)": {
        "tipo": "micro", "potencia": 2250.0, "vac": 220, "fases": 3, "modulos_max": 6, "eficiencia": 0.965
    },
    "Inversor Central Growatt MIN 3000TL-X (1F/2F 220V, 2 MPPT, 3000W)": {
        "tipo": "central", "potencia": 3000.0, "vac": 220, "fases": 2, "v_mppt_min": 80.0, "v_mppt_max": 500.0, "voc_max": 550.0, "modulos_max": 10, "eficiencia": 0.975
    },
    "Inversor Central Growatt MIN 6000TL-X (1F/2F 220V, 2 MPPT, 6000W)": {
        "tipo": "central", "potencia": 6000.0, "vac": 220, "fases": 2, "v_mppt_min": 80.0, "v_mppt_max": 500.0, "voc_max": 550.0, "modulos_max": 18, "eficiencia": 0.975
    },
    "Inversor Central Solis 10kW Trifásico (3F 220V CA, 10000W)": {
        "tipo": "central", "potencia": 10000.0, "vac": 220, "fases": 3, "v_mppt_min": 160.0, "v_mppt_max": 850.0, "voc_max": 1000.0, "modulos_max": 30, "eficiencia": 0.98
    }
}

TABLA_CONDUCTORES = [
    {"calibre": "14 AWG", "ampacidad": 20, "resistencia": 10.1},
    {"calibre": "12 AWG", "ampacidad": 25, "resistencia": 6.36},
    {"calibre": "10 AWG", "ampacidad": 35, "resistencia": 3.99},
    {"calibre": "8 AWG", "ampacidad": 50, "resistencia": 2.56},
    {"calibre": "6 AWG", "ampacidad": 65, "resistencia": 1.61},
    {"calibre": "4 AWG", "ampacidad": 85, "resistencia": 1.01},
    {"calibre": "2 AWG", "ampacidad": 115, "resistencia": 0.636},
    {"calibre": "1/0 AWG", "ampacidad": 150, "resistencia": 0.399},
]

PROTECCIONES_ESTANDAR = [15, 20, 25, 30, 40, 50, 60, 70, 80, 100, 125, 150]

def seleccionar_proteccion(corriente_diseno):
    for amp in PROTECCIONES_ESTANDAR:
        if amp >= corriente_diseno:
            return amp
    return PROTECCIONES_ESTANDAR[-1]

def calcular_calibre(corriente_diseno, longitud_m, tension_v, caida_max_pct=1.5, es_trifasico=False):
    for cond in TABLA_CONDUCTORES:
        if cond["ampacidad"] >= corriente_diseno:
            factor = math.sqrt(3) if es_trifasico else 2.0
            r_total = (cond["resistencia"] / 1000.0) * longitud_m
            caida_v = factor * corriente_diseno * r_total
            caida_pct = (caida_v / tension_v) * 100.0 if tension_v > 0 else 0
            if caida_pct <= caida_max_pct:
                return cond["calibre"], caida_pct
    return TABLA_CONDUCTORES[-1]["calibre"], 2.0

def dimensionar_tuberia(calibre):
    if calibre in ["14 AWG", "12 AWG", "10 AWG"]:
        return '3/4" Conduit Pared Delgada (EMT)'
    elif calibre in ["8 AWG", "6 AWG"]:
        return '1" Conduit Pared Delgada (EMT)'
    else:
        return '1 1/4" - 1 1/2" Conduit Pared Gruesa (RMC)'

# ==========================================
# 2. MOTOR GRÁFICO (DIAGRAMA UNIFILAR)
# ==========================================
def generar_diagrama_unifilar(topologia, n_paneles, n_inversores, cal_ca, cal_cd, prot_ca, prot_cd, vac):
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # Módulos Solares
    ax.add_patch(patches.Rectangle((0.5, 1.2), 1.5, 1.6, fill=True, color="#1e3a8a", alpha=0.9))
    ax.text(1.25, 2.0, f"ARREGLO PV\n{n_paneles} Módulos", color="white", ha="center", va="center", weight="bold", fontsize=8)

    # Conductor CD
    ax.annotate("", xy=(3.0, 2.0), xytext=(2.0, 2.0), arrowprops=dict(arrowstyle="->", lw=1.5, color="black"))
    ax.text(2.5, 2.2, f"CD: {cal_cd}\nFusible: {prot_cd}A", ha="center", fontsize=7, color="#b91c1c")

    # Desconectador CD / DPS
    ax.add_patch(patches.Rectangle((3.0, 1.4), 0.8, 1.2, fill=True, color="#f3f4f6", ec="black", lw=1.2))
    ax.text(3.4, 2.0, "DESC.\nCD/DPS", ha="center", va="center", fontsize=7, weight="bold")

    # Inversor(es)
    ax.annotate("", xy=(4.8, 2.0), xytext=(3.8, 2.0), arrowprops=dict(arrowstyle="->", lw=1.5, color="black"))
    ax.add_patch(patches.Rectangle((4.8, 1.2), 1.6, 1.6, fill=True, color="#059669", alpha=0.9))
    lbl_inv = f"{n_inversores}x MICRO" if topologia == "Microinversores" else f"{n_inversores}x INV. CENTRAL"
    ax.text(5.6, 2.0, f"{lbl_inv}\nCC/CA", color="white", ha="center", va="center", weight="bold", fontsize=8)

    # Conductor CA
    ax.annotate("", xy=(7.4, 2.0), xytext=(6.4, 2.0), arrowprops=dict(arrowstyle="->", lw=1.5, color="black"))
    ax.text(6.9, 2.2, f"CA: {cal_ca}\nInt: {prot_ca}A", ha="center", fontsize=7, color="#047857")

    # Tablero CA
    ax.add_patch(patches.Rectangle((7.4, 1.4), 0.9, 1.2, fill=True, color="#f3f4f6", ec="black", lw=1.2))
    ax.text(7.85, 2.0, f"TABLERO\n{vac}V", ha="center", va="center", fontsize=7, weight="bold")

    # Medidor CFE
    ax.annotate("", xy=(9.0, 2.0), xytext=(8.3, 2.0), arrowprops=dict(arrowstyle="->", lw=1.5, color="black"))
    circ = patches.Circle((9.4, 2.0), 0.45, fill=True, color="#d97706", ec="black")
    ax.add_patch(circ)
    ax.text(9.4, 2.0, "MEDIDOR\nCFE", ha="center", va="center", color="white", weight="bold", fontsize=7)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf

# ==========================================
# 3. GENERADORES DE PDF
# ==========================================
def crear_pdf_memoria_completa(datos):
    """Genera el informe técnico completo de 2 hojas: Dimensionamiento, NOM-001, Diagrama y Presupuesto."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="DocTitle", parent=styles["Heading1"], fontSize=15, textColor=colors.HexColor("#0f172a"), spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        name="DocSub", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#475569"), spaceAfter=10
    )
    h2_style = ParagraphStyle(
        name="DocH2", parent=styles["Heading2"], fontSize=10.5, textColor=colors.HexColor("#1e3a8a"), spaceBefore=7, spaceAfter=5
    )
    body_style = ParagraphStyle(
        name="DocBody", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#1e293b"), spaceAfter=3
    )

    story.append(Paragraph("MEMORIA TÉCNICA Y ECONÓMICA - SISTEMA SOLAR FOTOVOLTAICO", title_style))
    story.append(Paragraph(f"Cliente: <b>{datos['cliente']}</b> | Ubicación: <b>{datos['ciudad']}</b> | RPU/Servicio: <b>{datos['rpu']}</b>", subtitle_style))

    # 1. Dimensionamiento
    story.append(Paragraph("1. Dimensionamiento del Sistema", h2_style))
    tabla_dim_data = [
        ["Parámetro", "Valor Determinado", "Parámetro", "Valor Determinado"],
        ["Potencia Total", f"{datos['kwp']:.2f} kWp", "HSP Promedio", f"{datos['hsp']} hrs/día"],
        ["No. de Módulos", f"{datos['n_paneles']} piezas", "Inclinación Sugerida", f"{datos['inclinacion']}° Sur"],
        ["Modelo de Módulo", f"{datos['panel_nombre'][:28]}...", "Generación Bimestral Est.", f"{datos['gen_bimestral']:.0f} kWh"],
        ["Inversor/Micro", f"{datos['inv_nombre'][:28]}...", "Mitigación de Consumo", f"{datos['pct_cobertura']:.1f} %"]
    ]
    t1 = Table(tabla_dim_data, colWidths=[130, 130, 130, 130])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t1)
    story.append(Spacer(1, 6))

    # 2. Especificaciones Eléctricas
    story.append(Paragraph("2. Especificaciones Eléctricas de Interconexión (NOM-001 Art. 690)", h2_style))
    tabla_elec = [
        ["Circuito", "Conductor Calculado", "Canalización", "Protección de Sobrecorriente", "Caída de Tensión"],
        ["Lado CD (Solar)", datos['cal_cd'], datos['tub_cd'], f"{datos['prot_cd']}A Fusible/DPS 1000V", f"{datos['caida_cd']:.2f}%"],
        ["Lado CA (Red)", datos['cal_ca'], datos['tub_ca'], f"{datos['prot_ca']}A Termomagnético", f"{datos['caida_ca']:.2f}%"]
    ]
    t2 = Table(tabla_elec, colWidths=[80, 110, 130, 120, 80])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ALIGN', (4,1), (4,-1), 'CENTER'),
    ]))
    story.append(t2)
    story.append(Spacer(1, 6))

    # 3. Diagrama Unifilar
    story.append(Paragraph("3. Diagrama Unifilar Simplificado", h2_style))
    img_buffer = generar_diagrama_unifilar(
        datos['topologia'], datos['n_paneles'], datos['n_inversores'],
        datos['cal_ca'], datos['cal_cd'], datos['prot_ca'], datos['prot_cd'], datos['vac']
    )
    story.append(RLImage(img_buffer, width=520, height=160))
    story.append(Spacer(1, 6))

    # 4. Presupuesto
    story.append(Paragraph("4. Resumen Económico", h2_style))
    tabla_costos = [
        ["Concepto", "Importe (MXN)"],
        ["Suministro de módulos fotovoltaicos y micro/inversores", f"${datos['costo_equipos']:,.2f}"],
        ["Estructura de montaje en aluminio anodizado y tornillería inox", f"${datos['costo_estructura']:,.2f}"],
        ["Cableado solar, canalizaciones conduit, protecciones CD/CA y tierras", f"${datos['costo_electrico']:,.2f}"],
        ["Mano de obra certificada, pruebas de aislamiento y gestión CFE", f"${datos['costo_mano_obra']:,.2f}"],
        ["SUBTOTAL", f"${datos['subtotal']:,.2f}"],
        ["I.V.A. (16%)", f"${datos['iva']:,.2f}"],
        ["TOTAL PROYECTO LLAVE EN MANO", f"${datos['total']:,.2f}"]
    ]
    t3 = Table(tabla_costos, colWidths=[380, 140])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,-3), (-1,-1), 1, colors.HexColor("#0f172a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))
    story.append(t3)
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"Ahorro bimestral estimado: <b>${datos['ahorro_bimestral']:,.2f} MXN</b> | Tiempo de retorno de inversión: <b>{datos['roi']:.1f} años</b>.", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer


def crear_pdf_solo_presupuesto(datos):
    """Genera exclusivamente la cotización formal comercial en 1 sola hoja limpia, ideal para el cliente final."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    story = []
    styles = getSampleStyleSheet()

    header_title = ParagraphStyle(
        name="CotTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceAfter=4
    )
    badge_style = ParagraphStyle(
        name="Badge",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0369a1"),
        fontName="Helvetica-Bold",
        spaceAfter=12
    )
    section_title = ParagraphStyle(
        name="SecTitle",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a8a"),
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=5
    )
    body_text = ParagraphStyle(
        name="BodyTextCustom",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    terms_text = ParagraphStyle(
        name="Terms",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#64748b")
    )

    # Encabezado Comercial
    story.append(Paragraph("COTIZACIÓN COMERCIAL - SISTEMA FOTOVOLTAICO", header_title))
    story.append(Paragraph("Soluciones de Energía Solar Interconectada a la Red (CFE)", badge_style))

    # Ficha del Cliente y del Proyecto
    info_cliente_data = [
        [
            Paragraph(f"<b>Cliente:</b> {datos['cliente']}<br/><b>Servicio / RPU:</b> {datos['rpu']}<br/><b>Ubicación:</b> {datos['ciudad']}", body_text),
            Paragraph(f"<b>Capacidad del Sistema:</b> {datos['kwp']:.2f} kWp<br/><b>Módulos:</b> {datos['n_paneles']} piezas ({datos['panel_nombre'][:22]}...)<br/><b>Inversor:</b> {datos['n_inversores']}x ({datos['inv_nombre'][:22]}...)", body_text)
        ]
    ]
    t_info = Table(info_cliente_data, colWidths=[260, 260])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 10))

    # Indicadores Clave de Ahorro
    story.append(Paragraph("Resumen de Beneficio Energético y Financiero", section_title))
    resumen_financiero = [
        ["Generación Estimada", "Ahorro Bimestral Estimado", "Cobertura de Consumo", "Retorno de Inversión"],
        [f"{datos['gen_bimestral']:,.0f} kWh/bim", f"${datos['ahorro_bimestral']:,.2f} MXN", f"{datos['pct_cobertura']:.1f} %", f"{datos['roi']:.1f} Años"]
    ]
    t_resumen = Table(resumen_financiero, colWidths=[130, 130, 130, 130])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284c7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bae6fd")),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#f0f9ff")),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,1), (-1,1), colors.HexColor("#0369a1")),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 10))

    # Desglose Formal del Presupuesto
    story.append(Paragraph("Desglose del Presupuesto (Llave en Mano)", section_title))
    tabla_costos = [
        ["Concepto / Partida", "Detalle de Suministro e Instalación", "Importe (MXN)"],
        [
            "Módulos e Inversores",
            f"{datos['n_paneles']} paneles solares + inversor/microinversores certificados NOM/UL",
            f"${datos['costo_equipos']:,.2f}"
        ],
        [
            "Estructura de Montaje",
            "Perfilería de aluminio anodizado AL6005-T5 y tornillería de acero inox para azotea",
            f"${datos['costo_estructura']:,.2f}"
        ],
        [
            "Eléctrico y Protecciones",
            "Cable fotovoltaico XLPE, tubería conduit, supresor DPS, fusibles CD e interruptores CA",
            f"${datos['costo_electrico']:,.2f}"
        ],
        [
            "Instalación y Trámites",
            "Mano de obra especializada, puesta a tierra, pruebas NOM y gestión de contrato CFE",
            f"${datos['costo_mano_obra']:,.2f}"
        ],
        ["", "SUBTOTAL", f"${datos['subtotal']:,.2f}"],
        ["", "I.V.A. (16%)", f"${datos['iva']:,.2f}"],
        ["", "INVERSIÓN TOTAL", f"${datos['total']:,.2f}"]
    ]
    t_costos = Table(tabla_costos, colWidths=[130, 250, 140])
    t_costos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-4), 0.5, colors.HexColor("#cbd5e1")),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('FONTNAME', (1,-3), (2,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (1,-3), (2,-2), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (1,-1), (2,-1), colors.HexColor("#e2e8f0")),
        ('FONTSIZE', (1,-1), (2,-1), 9.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_costos)
    story.append(Spacer(1, 12))

    # Términos, Condiciones y Firmas
    condiciones = (
        "<b>Términos y Condiciones:</b><br/>"
        "• Vigencia de la cotización: 15 días naturales a partir de su emisión.<br/>"
        "• Garantías: 12 a 25 años en paneles solares según fabricante, 10 a 12 años en inversores, 1 año en mano de obra.<br/>"
        "• Forma de pago: 60% al anticipo para suministro de materiales, 30% a la entrega del equipo en sitio y 10% al concluir la instalación.<br/>"
        "• El trámite de cambio de medidor bidireccional queda sujeto a los tiempos operativos de CFE Distribución."
    )
    story.append(Paragraph(condiciones, terms_text))
    story.append(Spacer(1, 24))

    # Cuadro de Firmas
    firmas = [
        ["________________________________________", "________________________________________"],
        ["Ingeniero / Empresa Instaladora", "Aceptación del Cliente"]
    ]
    t_firmas = Table(firmas, colWidths=[260, 260])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,1), 8),
        ('TEXTCOLOR', (0,1), (-1,1), colors.HexColor("#475569")),
    ]))
    story.append(t_firmas)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# 4. INTERFAZ STREAMLIT
# ==========================================
st.title("☀️ Calculadora Solar & Cotizador Profesional")
st.caption("Cálculo bajo NOM-001-SEDE-2012 Art. 690, Diagrama Unifilar y Generador de Expediente CFE.")

col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader("1. Datos del Cliente y Servicio CFE")
    cliente = st.text_input("Nombre del Cliente / Empresa", value="Residencial Los Álamos")
    ciudad = st.selectbox("Ciudad (Referencia HSP / Latitud)", ["Saltillo, Coah (HSP: 5.6)", "Monterrey, NL (HSP: 5.2)", "Torreón, Coah (HSP: 5.8)", "Personalizado"])
    
    if "Saltillo" in ciudad:
        hsp_def, lat_def = 5.6, 25.4
    elif "Monterrey" in ciudad:
        hsp_def, lat_def = 5.2, 25.6
    elif "Torreón" in ciudad:
        hsp_def, lat_def = 5.8, 25.5
    else:
        hsp_def, lat_def = 5.0, 24.0

    c1, c2 = st.columns(2)
    with c1:
        hsp = st.number_input("Horas Solares Pico (HSP)", value=float(hsp_def), step=0.1)
    with c2:
        inclinacion = st.number_input("Inclinación Óptima (°)", value=float(lat_def), step=1.0)

    rpu = st.text_input("No. de Servicio CFE / RPU", value="012345678901")
    servicio_ca = st.selectbox("Tipo de Acometida CFE", ["Bifásico 2F-3H (220V/127V)", "Monofásico 1F-2H (127V)", "Trifásico 3F-4H (220V/127V)"])
    
    consumo_bim = st.number_input("Consumo Promedio Bimestral (kWh)", min_value=50, value=1450, step=50)
    tarifa_costo_kwh = st.number_input("Costo promedio por kWh (MXN)", value=4.10, step=0.1)

with col_b:
    st.subheader("2. Equipos y Topología")
    
    # SELECCIÓN O ENTRADA MANUAL DEL PANEL
    panel_manual = st.checkbox("⚙️ Ingresar Módulo Solar manualmente", value=False)
    if not panel_manual:
        panel_sel = st.selectbox("Módulo Fotovoltaico (Catálogo)", list(PANEL_CATALOG.keys()))
        p_spec = PANEL_CATALOG[panel_sel]
    else:
        st.caption("Ficha Técnica del Módulo Solar:")
        c_pm1, c_pm2 = st.columns(2)
        with c_pm1:
            nom_mod = st.text_input("Marca / Modelo del Panel", value="Panel Solar Personalizado")
            p_watts = st.number_input("Potencia Pico Pmp (W)", value=550.0, step=10.0)
            voc = st.number_input("Voltaje Circuito Abierto Voc (V)", value=49.8, step=0.1)
        with c_pm2:
            vmp = st.number_input("Voltaje Máx. Potencia Vmp (V)", value=42.1, step=0.1)
            isc = st.number_input("Corriente Cortocircuito Isc (A)", value=13.98, step=0.1)
            imp = st.number_input("Corriente Máx. Potencia Imp (A)", value=13.06, step=0.1)
        
        panel_sel = f"{nom_mod} ({p_watts:.0f}W)"
        p_spec = {
            "p_watts": p_watts, "vmp": vmp, "imp": imp,
            "voc": voc, "isc": isc, "temp_coeff_voc": -0.28
        }

    st.write("---")

    # SELECCIÓN O ENTRADA MANUAL DEL INVERSOR
    inv_manual = st.checkbox("⚙️ Ingresar Inversor / Microinversor manualmente", value=False)
    if not inv_manual:
        inv_sel = st.selectbox("Inversor (Catálogo)", list(INVERTER_CATALOG.keys()))
        i_spec = INVERTER_CATALOG[inv_sel]
    else:
        st.caption("Ficha Técnica del Inversor / Microinversor:")
        tipo_inv = st.radio("Tipo de Dispositivo", ["Microinversor", "Inversor Central"], horizontal=True)
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            inv_sel = st.text_input("Marca y Modelo", value="Inversor Personalizado")
            pot_ca = st.number_input("Potencia Nominal CA (Watts)", value=6000.0, step=500.0)
            vac_in = st.selectbox("Tensión de Salida CA (V)", [220, 127, 440], index=0)
            fases_in = st.selectbox("Número de Fases CA", [2, 1, 3], index=0)
        with col_inv2:
            if tipo_inv == "Microinversor":
                mod_max = st.number_input("Módulos admisibles por Micro", min_value=1, max_value=8, value=4)
                v_mppt_min, v_mppt_max, voc_max = 16.0, 60.0, 65.0
            else:
                mod_max = st.number_input("Capacidad máx. módulos sugerida", min_value=4, max_value=60, value=20)
                v_mppt_min = st.number_input("Vmin MPPT (V)", value=90.0, step=10.0)
                v_mppt_max = st.number_input("Vmax MPPT (V)", value=550.0, step=10.0)
                voc_max = st.number_input("Voltaje Máx. Admisible CD (V)", value=600.0, step=10.0)

        i_spec = {
            "tipo": "micro" if tipo_inv == "Microinversor" else "central",
            "potencia": pot_ca,
            "vac": vac_in,
            "fases": fases_in,
            "modulos_max": mod_max,
            "v_mppt_min": v_mppt_min,
            "v_mppt_max": v_mppt_max,
            "voc_max": voc_max,
            "eficiencia": 0.97
        }

    st.write("---")

    c3, c4 = st.columns(2)
    with c3:
        dist_cd = st.number_input("Distancia CD (módulos a inversor en m)", value=12.0, step=1.0)
    with c4:
        dist_ca = st.number_input("Distancia CA (inversor a centro de carga en m)", value=18.0, step=1.0)

    costo_por_watt = st.number_input(
        "Precio estimado por Watt instalado (MXN base)", 
        value=21.5, step=0.5, 
        help="Incluye estructura, equipos e instalación en MXN/Wp"
    )

# ==========================================
# 5. CÁLCULO FOTOVOLTAICO Y ELÉCTRICO
# ==========================================
consumo_diario = consumo_bim / 60.0
potencia_pico_kw = consumo_diario / (hsp * 0.80)
n_paneles = math.ceil((potencia_pico_kw * 1000.0) / p_spec["p_watts"])
kwp_real = (n_paneles * p_spec["p_watts"]) / 1000.0
gen_bimestral = kwp_real * hsp * 60.0 * 0.80
pct_cobertura = (gen_bimestral / consumo_bim) * 100.0

if i_spec["tipo"] == "micro":
    topologia = "Microinversores"
    n_inversores = math.ceil(n_paneles / i_spec["modulos_max"])
    vac = i_spec["vac"]
    es_tri = i_spec.get("fases", 1) == 3
else:
    topologia = "Inversor Central"
    n_inversores = max(1, math.ceil(n_paneles / i_spec["modulos_max"]))
    vac = i_spec["vac"]
    es_tri = i_spec.get("fases", 1) == 3

# CD NOM-001 Art. 690-8: Isc * 1.25 * 1.25
i_diseno_cd = p_spec["isc"] * 1.25 * 1.25
prot_cd = seleccionar_proteccion(i_diseno_cd)
cal_cd, caida_cd = calcular_calibre(i_diseno_cd, dist_cd, p_spec["vmp"], caida_max_pct=1.5, es_trifasico=False)
tub_cd = dimensionar_tuberia(cal_cd)

# CA NOM-001 Art. 690: Corriente continua al 125%
potencia_ca_total = min(kwp_real * 1000.0, n_inversores * i_spec["potencia"])
if es_tri:
    i_nom_ca = potencia_ca_total / (math.sqrt(3) * vac)
else:
    i_nom_ca = potencia_ca_total / vac

i_diseno_ca = i_nom_ca * 1.25
prot_ca = seleccionar_proteccion(i_diseno_ca)
cal_ca, caida_ca = calcular_calibre(i_diseno_ca, dist_ca, vac, caida_max_pct=2.0, es_trifasico=es_tri)
tub_ca = dimensionar_tuberia(cal_ca)

# Costos y ROI
total_sistema = kwp_real * 1000.0 * costo_por_watt
subtotal = total_sistema / 1.16
iva = total_sistema - subtotal
costo_equipos = subtotal * 0.55
costo_estructura = subtotal * 0.12
costo_electrico = subtotal * 0.15
costo_mano_obra = subtotal * 0.18

ahorro_bim = min(gen_bimestral, consumo_bim) * tarifa_costo_kwh
roi_anos = total_sistema / (ahorro_bim * 6.0) if ahorro_bim > 0 else 0.0

st.divider()

# ==========================================
# 6. RESULTADOS VISUALES
# ==========================================
st.subheader("3. Resultados del Dimensionamiento")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Paneles Necesarios", f"{n_paneles} módulos", f"{kwp_real:.2f} kWp")
m2.metric("Generación Est.", f"{gen_bimestral:.0f} kWh/bim", f"{pct_cobertura:.1f}% cubierto")
m3.metric("Protección CA", f"{prot_ca} A", f"Calibre: {cal_ca}")
m4.metric("Inversor(es)", f"{n_inversores} unidad(es)", topologia)
m5.metric("Retorno (ROI)", f"{roi_anos:.1f} años", f"Ahorro: ${ahorro_bim:,.0f}/bim")

st.write("#### Diagrama Unifilar Dinámico")
buf_img = generar_diagrama_unifilar(topologia, n_paneles, n_inversores, cal_ca, cal_cd, prot_ca, prot_cd, vac)
st.image(buf_img, use_container_width=True)

# Empaquetado de datos
datos_pdf = {
    "cliente": cliente, "ciudad": ciudad, "rpu": rpu, "hsp": hsp, "inclinacion": inclinacion,
    "kwp": kwp_real, "n_paneles": n_paneles, "panel_nombre": panel_sel, "inv_nombre": inv_sel,
    "gen_bimestral": gen_bimestral, "pct_cobertura": pct_cobertura, "topologia": topologia,
    "n_inversores": n_inversores, "vac": vac,
    "cal_cd": cal_cd, "tub_cd": tub_cd, "prot_cd": prot_cd, "caida_cd": caida_cd,
    "cal_ca": cal_ca, "tub_ca": tub_ca, "prot_ca": prot_ca, "caida_ca": caida_ca,
    "costo_equipos": costo_equipos, "costo_estructura": costo_estructura,
    "costo_electrico": costo_electrico, "costo_mano_obra": costo_mano_obra,
    "subtotal": subtotal, "iva": iva, "total": total_sistema,
    "ahorro_bimestral": ahorro_bim, "roi": roi_anos
}

# ==========================================
# 7. BOTONES DE DESCARGA EN PDF
# ==========================================
st.write("#### 📄 Documentos Generados")
btn_col1, btn_col2 = st.columns(2)

# PDF 1: Solo Presupuesto (1 Hoja)
pdf_presupuesto = crear_pdf_solo_presupuesto(datos_pdf)
with btn_col1:
    st.download_button(
        label="📑 Descargar SOLO Cotización (1 Hoja Cliente)",
        data=pdf_presupuesto,
        file_name=f"Presupuesto_{cliente.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# PDF 2: Memoria Técnica Completa (2 Hojas)
pdf_memoria = crear_pdf_memoria_completa(datos_pdf)
with btn_col2:
    st.download_button(
        label="📘 Descargar Memoria Técnica Completa + Unifilar",
        data=pdf_memoria,
        file_name=f"Memoria_Tecnica_{cliente.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
