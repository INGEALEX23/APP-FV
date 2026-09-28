import streamlit as st
import math
import io
import os
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="CALCULADORA FV ZONA ZERO", layout="wide", page_icon="☀️")

# ==========================================
# BASE DE DATOS DE RADIACIÓN SOLAR (HSP Y LATITUD)
# ==========================================
CIUDADES_SOLAR = {
    "Saltillo, Coahuila": {"hsp": 5.6, "inc": 25.4},
    "Ramos Arizpe, Coahuila": {"hsp": 5.6, "inc": 25.5},
    "Arteaga, Coahuila": {"hsp": 5.5, "inc": 25.4},
    "Torreón, Coahuila": {"hsp": 5.9, "inc": 25.5},
    "Monclova, Coahuila": {"hsp": 5.5, "inc": 26.9},
    "Piedras Negras, Coahuila": {"hsp": 5.3, "inc": 28.7},
    "Monterrey, Nuevo León": {"hsp": 5.2, "inc": 25.6},
    "San Pedro Garza García, NL": {"hsp": 5.2, "inc": 25.6},
    "Guadalajara, Jalisco": {"hsp": 5.7, "inc": 20.6},
    "Ciudad de México (CDMX)": {"hsp": 5.0, "inc": 19.4},
    "Querétaro, Querétaro": {"hsp": 5.5, "inc": 20.6},
    "San Luis Potosí, SLP": {"hsp": 5.7, "inc": 22.1},
    "Hermosillo, Sonora": {"hsp": 6.2, "inc": 29.0},
    "Chihuahua, Chihuahua": {"hsp": 5.8, "inc": 28.6},
    "Mérida, Yucatán": {"hsp": 5.3, "inc": 20.9},
    "Personalizado / Manual": {"hsp": 5.5, "inc": 25.0}
}

# ==========================================
# GESTIÓN PERMANENTE DEL LOGOTIPO
# ==========================================
logo_bytes = None
for default_logo in ["logo.png", "logo.jpg", "logo.jpeg"]:
    if os.path.exists(default_logo):
        with open(default_logo, "rb") as f:
            logo_bytes = f.read()
        break

with st.sidebar:
    st.header("🏢 Identidad de Marca")
    if logo_bytes is not None:
        st.success("Logotipo base cargado automáticamente.")
    logo_file = st.file_uploader("Reemplazar logotipo temporalmente (PNG/JPG)", type=["png", "jpg", "jpeg"])
    if logo_file is not None:
        logo_bytes = logo_file.read()
        st.session_state["logo_bytes"] = logo_bytes

if "logo_bytes" in st.session_state and st.session_state["logo_bytes"]:
    logo_bytes = st.session_state["logo_bytes"]

# Cabecera
col_h1, col_h2 = st.columns([1.5, 4.5])
with col_h1:
    if logo_bytes:
        st.image(logo_bytes, width=240)
    else:
        st.info("Coloca 'logo.png' en GitHub para cargarlo fijo.")
with col_h2:
    st.title("CALCULADORA FV ZONA ZERO")
    st.caption("All Engineering Solutions | Dimensionamiento Solar, NOM-001 Art. 690 y Presupuestos")

st.divider()

# ==========================================
# CATÁLOGOS BASE Y TABLAS NOM-001
# ==========================================
PANEL_CATALOG = {
    "Osda 550W Bifacial (Vmp: 42.1V, Imp: 13.06A, Voc: 49.8V, Isc: 13.98A)": {
        "p_watts": 550, "vmp": 42.1, "imp": 13.06, "voc": 49.8, "isc": 13.98
    },
    "Tier 1 580W Monocristalino (Vmp: 42.8V, Imp: 13.55A, Voc: 51.2V, Isc: 14.32A)": {
        "p_watts": 580, "vmp": 42.8, "imp": 13.55, "voc": 51.2, "isc": 14.32
    },
    "Tier 1 660W Alto Rendimiento (Vmp: 38.3V, Imp: 17.23A, Voc: 45.9V, Isc: 18.25A)": {
        "p_watts": 660, "vmp": 38.3, "imp": 17.23, "voc": 45.9, "isc": 18.25
    }
}

INVERTER_CATALOG = {
    "Microinversor Hoymiles HMS-2000-4T (4 MPPT Indep, 2000W, 220V CA)": {
        "tipo": "micro", "potencia": 2000, "vac": 220, "modulos_max": 4, "fases": 2, "mppt_count": 4
    },
    "Microinversor Hoymiles HMT-2250-6T (Trifásico 220V CA, 2250W)": {
        "tipo": "micro", "potencia": 2250, "vac": 220, "modulos_max": 6, "fases": 3, "mppt_count": 3
    },
    "Inversor Central Growatt MIN 3000TL-X (220V, 2 MPPT, 3000W)": {
        "tipo": "central", "potencia": 3000, "vac": 220, "fases": 2, "mppt_count": 2
    },
    "Inversor Central Growatt MIN 6000TL-X (220V, 2 MPPT, 6000W)": {
        "tipo": "central", "potencia": 6000, "vac": 220, "fases": 2, "mppt_count": 2
    },
    "Inversor Central Solis 10kW Trifásico (3F 220V CA, 10000W)": {
        "tipo": "central", "potencia": 10000, "vac": 220, "fases": 3, "mppt_count": 2
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
            caida_pct = (caida_v / tension_v) * 100.0
            if caida_pct <= caida_max_pct:
                return cond["calibre"], caida_pct
    return TABLA_CONDUCTORES[-1]["calibre"], 2.0

def dimensionar_tuberia(calibre, num_conductores=3):
    if calibre in ["14 AWG", "12 AWG", "10 AWG"]:
        return '3/4" Conduit EMT' if num_conductores <= 4 else '1" Conduit EMT'
    elif calibre in ["8 AWG", "6 AWG"]:
        return '1" Conduit EMT'
    else:
        return '1 1/4" Conduit RMC'

# ==========================================
# GENERADORES DE PDF
# ==========================================
def crear_pdf_solo_presupuesto(datos, logo_raw=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=26, bottomMargin=26)
    story = []
    styles = getSampleStyleSheet()

    t_empresa = ParagraphStyle(name="PEmp", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#0f172a"), spaceAfter=2)
    fol_style = ParagraphStyle(name="PFol", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#0f172a"), alignment=2, leading=11)
    h2_style = ParagraphStyle(name="PH2", parent=styles["Heading2"], fontSize=9.5, textColor=colors.HexColor("#1e3a8a"), spaceBefore=4, spaceAfter=2)
    cell_style = ParagraphStyle(name="PCell", parent=styles["Normal"], fontSize=7.5, leading=9.5)
    cell_bold = ParagraphStyle(name="PCellB", parent=styles["Normal"], fontSize=7.5, leading=9.5, fontName="Helvetica-Bold")
    firm_style = ParagraphStyle(name="PFirm", parent=styles["Normal"], fontSize=7.5, leading=10, alignment=1)

    # Estilos de alto impacto para el bloque de ROI
    fin_lbl = ParagraphStyle(name="PFinLbl", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#94a3b8"), alignment=1, fontName="Helvetica-Bold")
    fin_val_gold = ParagraphStyle(name="PFinValG", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#fbbf24"), alignment=1, fontName="Helvetica-Bold")
    fin_val_white = ParagraphStyle(name="PFinValW", parent=styles["Normal"], fontSize=10, textColor=colors.white, alignment=1, fontName="Helvetica-Bold")

    # 1. Encabezado con Logo y Folio/Fecha
    logo_img = RLImage(io.BytesIO(logo_raw), width=165, height=65) if logo_raw else Paragraph("<b>ZONA ZERO</b><br/><font size=7>All Engineering Solutions</font>", t_empresa)
    header_data = [
        [logo_img,
         Paragraph(f"<b>ZONA ZERO 'ALL ENGINEERING SOLUTIONS'</b><br/>"
                   f"Saltillo, Coahuila | Soluciones Integrales de Ingeniería<br/>"
                   f"<b>Folio:</b> {datos['folio']}<br/>"
                   f"<b>Fecha:</b> {datos['fecha']}", fol_style)]
    ]
    th = Table(header_data, colWidths=[180, 360])
    th.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(th)
    story.append(Spacer(1, 3))

    # Franja de Título
    story.append(Table([[Paragraph("<font color='white'><b>COTIZACIÓN COMERCIAL - SISTEMA FOTOVOLTAICO INTERCONECTADO</b></font>", cell_bold)]],
                       colWidths=[540],
                       style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1e3a8a")),
                              ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                              ('TOPPADDING', (0,0), (-1,-1), 3),
                              ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
    story.append(Spacer(1, 4))

    # Datos Generales
    datos_gen = [
        [Paragraph("<b>Cliente:</b>", cell_bold), Paragraph(str(datos['cliente']), cell_style),
         Paragraph("<b>Ubicación:</b>", cell_bold), Paragraph(str(datos['ciudad']), cell_style)],
        [Paragraph("<b>Servicio / RPU:</b>", cell_bold), Paragraph(str(datos['rpu']), cell_style),
         Paragraph("<b>Tensión CA:</b>", cell_bold), Paragraph(f"{datos['vac']}V ({datos['fases']} Fases)", cell_style)],
        [Paragraph("<b>Potencia Total:</b>", cell_bold), Paragraph(f"<b>{datos['kwp']:.2f} kWp</b>", cell_style),
         Paragraph("<b>No. Módulos:</b>", cell_bold), Paragraph(f"{datos['n_paneles']} piezas", cell_style)]
    ]
    tg = Table(datos_gen, colWidths=[90, 180, 90, 180])
    tg.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(tg)
    story.append(Spacer(1, 4))

    # 1. BLOQUE DE ALTO IMPACTO: Análisis Energético y Retorno de Inversión
    story.append(Paragraph("1. Análisis Energético y Retorno de Inversión", h2_style))
    tabla_fin = [
        [Paragraph("GENERACIÓN ESTIMADA", fin_lbl), Paragraph("AHORRO BIMESTRAL", fin_lbl), Paragraph("AHORRO ANUAL ESTIMADO", fin_lbl), Paragraph("RETORNO DE INVERSIÓN", fin_lbl)],
        [Paragraph(f"{datos['gen_bimestral']:,.0f} kWh/bim", fin_val_white),
         Paragraph(f"${datos['ahorro_bim']:,.2f} MXN", fin_val_gold),
         Paragraph(f"${datos['ahorro_anual']:,.2f} MXN", fin_val_gold),
         Paragraph(f"{datos['roi']:.1f} AÑOS", fin_val_gold)]
    ]
    tfin = Table(tabla_fin, colWidths=[135, 135, 135, 135])
    tfin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0f172a")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,0), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 1),
        ('BOTTOMPADDING', (0,1), (-1,1), 4.5),
        ('LINEAFTER', (0,0), (2,-1), 0.5, colors.HexColor("#334155")),
    ]))
    story.append(tfin)
    story.append(Spacer(1, 4))

    # 2. Equipamiento Principal
    story.append(Paragraph("2. Equipamiento Seleccionado", h2_style))
    tabla_eq = [
        [Paragraph("<b>Concepto</b>", cell_bold), Paragraph("<b>Descripción Técnica</b>", cell_bold), Paragraph("<b>Cant.</b>", cell_bold)],
        [Paragraph("Módulos Solares", cell_style), Paragraph(str(datos['panel_nombre']), cell_style), Paragraph(f"{datos['n_paneles']}", cell_style)],
        [Paragraph("Inversión / Conversión", cell_style), Paragraph(f"{datos['inv_nombre']} ({datos['topologia']})", cell_style), Paragraph(f"{datos['n_inversores']}", cell_style)],
        [Paragraph("Estructura de Montaje", cell_style), Paragraph("Aluminio anodizado AL6005-T5 con tornillería de acero inoxidable", cell_style), Paragraph("1 Lote", cell_style)]
    ]
    te = Table(tabla_eq, colWidths=[130, 360, 50])
    te.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('ALIGN', (2,0), (2,-1), 'CENTER')
    ]))
    story.append(te)
    story.append(Spacer(1, 4))

    # 3. Alcance
    story.append(Paragraph("3. Alcance del Proyecto Llave en Mano", h2_style))
    alcances = [
        [Paragraph("• Suministro y montaje mecánico de módulos fotovoltaicos e inversores.", cell_style)],
        [Paragraph("• Cableado solar fotovoltaico CD (PV Wire) o troncal CA en tubería Conduit bajo NOM-001-SEDE-2012.", cell_style)],
        [Paragraph("• Gabinete de protección con interruptores termomagnéticos y supresor de transitorios (DPS).", cell_style)],
        [Paragraph("• Sistema de puesta a tierra equipotencial con electrodo de cobre y conectores certificados.", cell_style)],
        [Paragraph("• Trámites de interconexión con CFE y pruebas de comisionamiento y puesta en marcha.", cell_style)]
    ]
    ta = Table(alcances, colWidths=[540])
    ta.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(ta)
    story.append(Spacer(1, 4))

    # 4. Inversión
    story.append(Paragraph("4. Resumen de Inversión", h2_style))
    tabla_precios = [
        [Paragraph("<b>CONCEPTO</b>", cell_bold), Paragraph("<b>MONTO (MXN)</b>", cell_bold)],
        [Paragraph("SUBTOTAL", cell_bold), Paragraph(f"${datos['subtotal']:,.2f}", cell_bold)],
        [Paragraph("I.V.A. (16%)", cell_bold), Paragraph(f"${datos['iva']:,.2f}", cell_bold)],
        [Paragraph("<b>INVERSIÓN TOTAL LLAVE EN MANO</b>", cell_bold), Paragraph(f"<b>${datos['total']:,.2f}</b>", cell_bold)]
    ]
    tp = Table(tabla_precios, colWidths=[380, 160])
    tp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f8fafc")),
    ]))
    story.append(tp)
    
    # 3 ESPACIOS AMPLIADOS HACIA ABAJO PARA DESPEGAR LAS FIRMAS
    story.append(Spacer(1, 28))

    firmas = [
        [Paragraph("____________________________________________<br/><b>Zona Zero 'All Engineering Solutions'</b><br/>Ingeniería y Proyectos", firm_style),
         Paragraph(f"____________________________________________<br/><b>Aceptación del Cliente</b><br/>Fecha: {datos['fecha']} | Firma", firm_style)]
    ]
    tf = Table(firmas, colWidths=[270, 270])
    tf.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(tf)

    doc.build(story)
    buffer.seek(0)
    return buffer

def crear_pdf_memoria_tecnica(datos, logo_raw=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    t_empresa = ParagraphStyle(name="MEmp", parent=styles["Heading1"], fontSize=15, textColor=colors.HexColor("#0f172a"), spaceAfter=2)
    s_empresa = ParagraphStyle(name="MSub", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#475569"))
    h2_style = ParagraphStyle(name="MH2", parent=styles["Heading2"], fontSize=10, textColor=colors.HexColor("#1e3a8a"), spaceBefore=8, spaceAfter=4)
    cell_style = ParagraphStyle(name="MCell", parent=styles["Normal"], fontSize=7.5, leading=9.5)
    cell_bold = ParagraphStyle(name="MCellB", parent=styles["Normal"], fontSize=7.5, leading=9.5, fontName="Helvetica-Bold")

    logo_img = RLImage(io.BytesIO(logo_raw), width=150, height=60) if logo_raw else Paragraph("<b>ZONA ZERO</b>", t_empresa)
    story.append(Table([[logo_img, Paragraph(f"<b>ZONA ZERO 'ALL ENGINEERING SOLUTIONS'</b><br/>Memoria Técnica de Dimensionamiento Eléctrico | NOM-001-SEDE-2012 Art. 690<br/><b>Folio:</b> {datos['folio']} | <b>Fecha:</b> {datos['fecha']}", s_empresa)]],
                       colWidths=[160, 380],
                       style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("1. Parámetros de Generación y Sitio", h2_style))
    tabla_sitio = [
        [Paragraph("<b>Cliente:</b>", cell_bold), Paragraph(str(datos['cliente']), cell_style), Paragraph("<b>Ubicación:</b>", cell_bold), Paragraph(str(datos['ciudad']), cell_style)],
        [Paragraph("<b>RPU / CFE:</b>", cell_bold), Paragraph(str(datos['rpu']), cell_style), Paragraph("<b>HSP Promedio:</b>", cell_bold), Paragraph(f"{datos['hsp']} hrs/día", cell_style)],
        [Paragraph("<b>Potencia Pico (kWp):</b>", cell_bold), Paragraph(f"{datos['kwp']:.2f} kWp", cell_style), Paragraph("<b>Inclinación:</b>", cell_bold), Paragraph(f"{datos['inclinacion']}° al Sur", cell_style)],
        [Paragraph("<b>Generación Bimestral:</b>", cell_bold), Paragraph(f"{datos['gen_bimestral']:.0f} kWh", cell_style), Paragraph("<b>Arreglo Strings/MPPT:</b>", cell_bold), Paragraph(str(datos['config_strings']), cell_style)]
    ]
    ts = Table(tabla_sitio, colWidths=[120, 150, 120, 150])
    ts.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    story.append(ts)
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Memoria de Cálculo de Conductores y Protecciones (NOM-001 Art. 690)", h2_style))
    tabla_elec = [
        [Paragraph("<b>Circuito</b>", cell_bold),
         Paragraph("<b>Conductor</b>", cell_bold),
         Paragraph("<b>Canalización</b>", cell_bold),
         Paragraph("<b>Protección Sobrecorriente</b>", cell_bold),
         Paragraph("<b>Caída %</b>", cell_bold)],
        [Paragraph("Lado CD (Generación)", cell_style),
         Paragraph(str(datos['cal_cd']), cell_style),
         Paragraph(str(datos['tub_cd']), cell_style),
         Paragraph(str(datos['prot_cd']), cell_style),
         Paragraph(f"{datos['caida_cd']:.2f}%", cell_style)],
        [Paragraph("Lado CA (Interconexión)", cell_style),
         Paragraph(str(datos['cal_ca']), cell_style),
         Paragraph(str(datos['tub_ca']), cell_style),
         Paragraph(str(datos['prot_ca']), cell_style),
         Paragraph(f"{datos['caida_ca']:.2f}%", cell_style)]
    ]
    te = Table(tabla_elec, colWidths=[70, 120, 150, 130, 70])
    te.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (4,1), (4,-1), 'CENTER')
    ]))
    story.append(te)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Criterios Normativos de Diseño Aplicados", h2_style))
    notas = [
        [Paragraph("• <b>Art. 690-8(a)(1):</b> La corriente máxima por string es 1.25 × Isc. En microinversores la conexión es directa sin tiradas largas en CD.", cell_style)],
        [Paragraph("• <b>Art. 690-8(b)(1):</b> Dispositivos de sobrecorriente dimensionados al 125% de la corriente continua de diseño.", cell_style)],
        [Paragraph("• <b>Art. 310-15:</b> Conductores de cobre con aislamiento THHN/THHW-LS 75°C seleccionados por ampacidad y caída admisible &le; 2.0%.", cell_style)],
        [Paragraph("• <b>Capítulo 9, Tabla 1:</b> Factor de ocupación de tubería conduit no mayor al 40% para 3 o más conductores en canalización.", cell_style)]
    ]
    tn = Table(notas, colWidths=[540])
    tn.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2)
    ]))
    story.append(tn)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# INTERFAZ DE CAPTURA
# ==========================================
col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader("1. Datos del Cliente y Presupuesto")
    
    c_fol1, c_fol2 = st.columns(2)
    with c_fol1:
        folio_doc = st.text_input("Folio de Cotización", value=f"ZZ-{date.today().strftime('%Y%m')}-01")
    with c_fol2:
        fecha_doc = st.date_input("Fecha de Emisión", value=date.today())

    cliente = st.text_input("Nombre del Cliente / Empresa", value="", placeholder="Ej. Juan Pérez / Taller Industrial")
    
    # Búsqueda de Ciudad con autocompletado solar o modo manual
    ciudad_sel = st.selectbox("Ciudad (Búsqueda automática de HSP / Inclinación)", list(CIUDADES_SOLAR.keys()), index=0)
    
    if ciudad_sel == "Personalizado / Manual":
        ciudad_nombre = st.text_input("Escribe el nombre de la Ciudad", value="", placeholder="Ej. Piedras Negras, Coahuila")
        default_hsp = 5.5
        default_inc = 25.0
    else:
        ciudad_nombre = ciudad_sel
        default_hsp = CIUDADES_SOLAR[ciudad_sel]["hsp"]
        default_inc = CIUDADES_SOLAR[ciudad_sel]["inc"]

    c1, c2 = st.columns(2)
    with c1:
        hsp = st.number_input("Horas Solares Pico (HSP)", min_value=0.0, max_value=10.0, value=float(default_hsp), step=0.1)
    with c2:
        inclinacion = st.number_input("Inclinación de Paneles (°)", min_value=0.0, max_value=90.0, value=float(default_inc), step=1.0)

    rpu = st.text_input("No. de Servicio CFE / RPU", value="", placeholder="Ej. 012345678901")
    servicio_ca = st.selectbox("Tipo de Acometida CA", ["Bifásico 2F-3H (220V/127V)", "Monofásico 1F-2H (127V)", "Trifásico 3F-4H (220V/127V)"])
    
    c_tar1, c_tar2 = st.columns(2)
    with c_tar1:
        consumo_bim = st.number_input("Consumo Promedio Bimestral (kWh)", min_value=0.0, value=None, placeholder="Ej. 1450")
    with c_tar2:
        costo_kwh = st.number_input("Costo del kWh CFE ($ MXN)", min_value=0.0, value=None, placeholder="Ej. 4.10")

with col_b:
    st.subheader("2. Equipos y Topología")
    
    # Módulo Fotovoltaico
    panel_manual = st.checkbox("⚙️ Ingresar Módulo Solar manualmente", value=False)
    if not panel_manual:
        panel_sel = st.selectbox("Módulo Fotovoltaico (Catálogo)", list(PANEL_CATALOG.keys()))
        p_spec = PANEL_CATALOG[panel_sel]
    else:
        st.caption("Ficha técnica del Módulo Solar:")
        c_pm1, c_pm2 = st.columns(2)
        with c_pm1:
            nom_mod = st.text_input("Marca / Modelo", value="", placeholder="Ej. Osda / Risen / Jinko")
            p_watts = st.number_input("Potencia Pico Pmp (W)", min_value=0.0, value=None, placeholder="Ej. 550")
            voc = st.number_input("Voltaje Voc (V)", min_value=0.0, value=None, placeholder="Ej. 49.8")
        with c_pm2:
            vmp = st.number_input("Voltaje Vmp (V)", min_value=0.0, value=None, placeholder="Ej. 42.1")
            isc = st.number_input("Corriente Isc (A)", min_value=0.0, value=None, placeholder="Ej. 13.98")
            imp = st.number_input("Corriente Imp (A)", min_value=0.0, value=None, placeholder="Ej. 13.06")
        
        panel_sel = f"{nom_mod} ({p_watts or 0:.0f}W)"
        p_spec = {
            "p_watts": p_watts or 550.0, "vmp": vmp or 42.1, "imp": imp or 13.06,
            "voc": voc or 49.8, "isc": isc or 13.98
        }

    st.write("---")

    # Inversor / Microinversor
    inv_manual = st.checkbox("⚙️ Ingresar Inversor / Microinversor manualmente", value=False)
    if not inv_manual:
        inv_sel = st.selectbox("Inversor (Catálogo)", list(INVERTER_CATALOG.keys()))
        i_spec = INVERTER_CATALOG[inv_sel]
    else:
        st.caption("Ficha técnica del Inversor / Microinversor:")
        tipo_inv = st.radio("Tipo de Dispositivo", ["Microinversor", "Inversor Central"], horizontal=True)
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            inv_sel = st.text_input("Marca y Modelo", value="", placeholder="Ej. Hoymiles HMS-2000")
            pot_ca = st.number_input("Potencia Nominal CA (Watts)", min_value=0.0, value=None, placeholder="Ej. 2000")
            vac_in = st.selectbox("Tensión CA (V)", [220, 127, 440], index=0)
            fases_in = st.selectbox("Fases CA", [2, 1, 3], index=0)
        with col_i2:
            if tipo_inv == "Microinversor":
                mod_max = st.number_input("Módulos por Micro", min_value=1, max_value=8, value=4)
                mppt_count = mod_max
            else:
                mod_max = 24
                mppt_count = st.number_input("No. de Rastreadores MPPT", min_value=1, max_value=6, value=2)

        i_spec = {
            "tipo": "micro" if tipo_inv == "Microinversor" else "central",
            "potencia": pot_ca or 2000.0,
            "vac": vac_in,
            "fases": fases_in,
            "modulos_max": mod_max,
            "mppt_count": mppt_count
        }

    st.write("---")

    c3, c4 = st.columns(2)
    with c3:
        dist_cd = st.number_input("Distancia CD (módulos a inversor central en m)", min_value=0.0, value=None, placeholder="Ej. 15.0")
    with c4:
        dist_ca = st.number_input("Distancia CA (inversor a centro de carga en m)", min_value=0.0, value=None, placeholder="Ej. 18.0")

    subtotal_manual = st.number_input("Subtotal del Proyecto (MXN antes de IVA)", min_value=0.0, value=None, placeholder="Ej. 75000.00")

st.divider()

# ==========================================
# MOTOR DE CÁLCULO
# ==========================================
campos_listos = (consumo_bim is not None and consumo_bim > 0 and 
                 hsp is not None and hsp > 0 and 
                 dist_ca is not None)

if not campos_listos:
    st.info("👋 Ingresa el consumo bimestral, el costo de kWh y la distancia de CA para realizar el cálculo.")
else:
    # 1. Dimensionamiento Solar
    consumo_diario = consumo_bim / 60.0
    potencia_pico_kw = consumo_diario / (hsp * 0.80)
    n_paneles = math.ceil((potencia_pico_kw * 1000) / p_spec["p_watts"])
    kwp_real = (n_paneles * p_spec["p_watts"]) / 1000.0
    gen_bimestral = kwp_real * hsp * 60 * 0.80
    pct_cobertura = (gen_bimestral / consumo_bim) * 100.0

    # 2. Análisis Financiero
    precio_kwh_calc = costo_kwh if (costo_kwh is not None and costo_kwh > 0) else 4.10
    ahorro_bimestral = min(gen_bimestral, consumo_bim) * precio_kwh_calc
    ahorro_anual = ahorro_bimestral * 6

    # 3. Topología e Inversores
    if i_spec["tipo"] == "micro":
        topologia = "Microinversores"
        n_inversores = math.ceil(n_paneles / i_spec["modulos_max"])
        vac = i_spec["vac"]
        fases = i_spec.get("fases", 2)
        es_tri = (fases == 3)
        config_strings = f"{n_inversores} Microinversores (Entrada individual por módulo)"
        
        cal_cd = "Chicote MC4 12 AWG (Fab)"
        prot_cd = "Integrada en Micro"
        tub_cd = "Sin canalización CD (Techo)"
        caida_cd = 0.2
    else:
        topologia = "Inversor Central"
        n_inversores = 1
        vac = i_spec["vac"]
        fases = i_spec.get("fases", 2)
        es_tri = (fases == 3)
        num_mppt = max(1, i_spec.get("mppt_count", 2))
        strings = num_mppt
        paneles_por_string = math.ceil(n_paneles / strings)
        config_strings = f"{strings} Strings ({paneles_por_string} módulos c/u en serie)"

        i_diseno_string = p_spec["isc"] * 1.25 * 1.25
        prot_cd_amp = seleccionar_proteccion(i_diseno_string)
        prot_cd = f"{prot_cd_amp}A Fusible CD (x{strings})"
        
        v_string = paneles_por_string * p_spec["vmp"]
        dist_cd_calc = dist_cd if (dist_cd is not None and dist_cd > 0) else 15.0
        cal_cd_calc, caida_cd = calcular_calibre(i_diseno_string, dist_cd_calc, v_string, caida_max_pct=1.5, es_trifasico=False)
        cal_cd = f"{cal_cd_calc} PV-Wire ({strings} pares)"
        tub_cd = dimensionar_tuberia(cal_cd_calc, num_conductores=strings*2)

    # 4. Circuito CA
    potencia_ca_total = min(kwp_real * 1000, n_inversores * i_spec["potencia"])
    if es_tri:
        i_nom_ca = potencia_ca_total / (math.sqrt(3) * vac)
    else:
        i_nom_ca = potencia_ca_total / vac

    i_diseno_ca = i_nom_ca * 1.25
    prot_ca_amp = seleccionar_proteccion(i_diseno_ca)
    prot_ca = f"{prot_ca_amp}A Termomagnético ({fases}P)"
    cal_ca, caida_ca = calcular_calibre(i_diseno_ca, dist_ca, vac, caida_max_pct=2.0, es_trifasico=es_tri)
    tub_ca = dimensionar_tuberia(cal_ca, num_conductores=fases+1)

    # 5. Inversión y ROI
    subtotal = subtotal_manual if (subtotal_manual is not None and subtotal_manual > 0) else (kwp_real * 1000 * 21.5 / 1.16)
    iva = subtotal * 0.16
    total_sistema = subtotal + iva
    roi_anos = total_sistema / ahorro_anual if ahorro_anual > 0 else 0.0

    # ==========================================
    # MÉTRICAS Y RESULTADOS VISUALES
    # ==========================================
    st.subheader("3. Resultados del Dimensionamiento")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Paneles Necesarios", f"{n_paneles} módulos", f"{kwp_real:.2f} kWp")
    m2.metric("Generación Est.", f"{gen_bimestral:.0f} kWh/bim", f"{pct_cobertura:.1f}% cubierto")
    m3.metric("Ahorro Bimestral", f"${ahorro_bimestral:,.0f} MXN", f"${ahorro_anual:,.0f}/año")
    m4.metric("Retorno (ROI)", f"{roi_anos:.1f} años", f"Tarifa: ${precio_kwh_calc:.2f}/kWh")
    m5.metric("Protección CA", f"{prot_ca_amp} A", f"Calibre: {cal_ca}")

    st.write("---")

    # Datos para los PDFs
    datos_pdf = {
        "folio": folio_doc if folio_doc else "S/F",
        "fecha": fecha_doc.strftime("%d/%m/%Y") if fecha_doc else date.today().strftime("%d/%m/%Y"),
        "cliente": cliente if cliente else "Sin especificar",
        "ciudad": ciudad_nombre if ciudad_nombre else "Sin especificar",
        "rpu": rpu if rpu else "Sin especificar",
        "hsp": hsp, "inclinacion": inclinacion if inclinacion else 25.0,
        "kwp": kwp_real, "n_paneles": n_paneles, "panel_nombre": panel_sel, "inv_nombre": inv_sel,
        "gen_bimestral": gen_bimestral, "pct_cobertura": pct_cobertura, "topologia": topologia,
        "n_inversores": n_inversores, "vac": vac, "fases": fases, "config_strings": config_strings,
        "cal_cd": cal_cd, "tub_cd": tub_cd, "prot_cd": prot_cd, "caida_cd": caida_cd,
        "cal_ca": cal_ca, "tub_ca": tub_ca, "prot_ca": prot_ca, "caida_ca": caida_ca,
        "ahorro_bim": ahorro_bimestral, "ahorro_anual": ahorro_anual, "roi": roi_anos,
        "subtotal": subtotal, "iva": iva, "total": total_sistema
    }

    st.subheader("4. Descarga de Documentos Técnicos y Comerciales")
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        pdf_presupuesto = crear_pdf_solo_presupuesto(datos_pdf, logo_bytes)
        nom_cliente = cliente.replace(" ", "_") if cliente else "Cliente"
        st.download_button(
            label="📑 Descargar SOLO Cotización (1 Hoja Cliente)",
            data=pdf_presupuesto,
            file_name=f"Cotizacion_ZonaZero_{nom_cliente}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with col_btn2:
        pdf_memoria = crear_pdf_memoria_tecnica(datos_pdf, logo_bytes)
        st.download_button(
            label="📘 Descargar Memoria Técnica NOM-001 Art. 690",
            data=pdf_memoria,
            file_name=f"Memoria_Tecnica_NOM_{nom_cliente}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
