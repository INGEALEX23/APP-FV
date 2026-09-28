import streamlit as st
import math
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="CALCULADORA FV ZONA ZERO", layout="wide", page_icon="☀️")

# ==========================================
# GESTIÓN DEL LOGOTIPO
# ==========================================
with st.sidebar:
    st.header("🏢 Identidad de Marca")
    logo_file = st.file_uploader("Cargar logotipo Zona Zero (PNG/JPG)", type=["png", "jpg", "jpeg"])
    if logo_file is not None:
        st.session_state["logo_bytes"] = logo_file.read()
        st.success("Logotipo cargado correctamente.")

logo_bytes = st.session_state.get("logo_bytes", None)

# Cabecera principal
col_h1, col_h2 = st.columns([1.5, 4.5])
with col_h1:
    if logo_bytes:
        st.image(logo_bytes, width=240)
    else:
        st.info("Sube tu logotipo en la barra lateral.")
with col_h2:
    st.title("CALCULADORA FV ZONA ZERO")
    st.caption("All Engineering Solutions | Dimensionamiento Solar, NOM-001 Art. 690 y Presupuestos")

st.divider()

# ==========================================
# CATÁLOGOS BASE Y TABLAS NOM-001-SEDE-2012
# ==========================================
PANEL_CATALOG = {
    "Osda 550W Bifacial (Vmp: 42.1V, Imp: 13.06A, Voc: 49.8V, Isc: 13.98A)": {
        "p_watts": 550, "vmp": 42.1, "imp": 13.06, "voc": 49.8, "isc": 13.98, "temp_coeff_voc": -0.28
    },
    "Tier 1 580W Monocristalino (Vmp: 42.8V, Imp: 13.55A, Voc: 51.2V, Isc: 14.32A)": {
        "p_watts": 580, "vmp": 42.8, "imp": 13.55, "voc": 51.2, "isc": 14.32, "temp_coeff_voc": -0.27
    },
    "Tier 1 660W Alto Rendimiento (Vmp: 38.3V, Imp: 17.23A, Voc: 45.9V, Isc: 18.25A)": {
        "p_watts": 660, "vmp": 38.3, "imp": 17.23, "voc": 45.9, "isc": 18.25, "temp_coeff_voc": -0.26
    }
}

INVERTER_CATALOG = {
    "Microinversor Hoymiles HMS-2000-4T (4 MPPT, 2000W, 220V CA)": {
        "tipo": "micro", "potencia": 2000, "vac": 220, "modulos_max": 4, "fases": 2, "eficiencia": 0.965
    },
    "Microinversor Hoymiles HMT-2250-6T (Trifásico 220V CA, 2250W)": {
        "tipo": "micro", "potencia": 2250, "vac": 220, "modulos_max": 6, "fases": 3, "eficiencia": 0.965
    },
    "Inversor Central Growatt MIN 3000TL-X (220V, 2 MPPT, 3000W)": {
        "tipo": "central", "potencia": 3000, "vac": 220, "fases": 2, "v_mppt_min": 80, "v_mppt_max": 500, "voc_max": 550, "eficiencia": 0.975
    },
    "Inversor Central Growatt MIN 6000TL-X (220V, 2 MPPT, 6000W)": {
        "tipo": "central", "potencia": 6000, "vac": 220, "fases": 2, "v_mppt_min": 80, "v_mppt_max": 500, "voc_max": 550, "eficiencia": 0.975
    },
    "Inversor Central Solis 10kW Trifásico (3F 220V CA, 10000W)": {
        "tipo": "central", "potencia": 10000, "vac": 220, "fases": 3, "v_mppt_min": 160, "v_mppt_max": 850, "voc_max": 1000, "eficiencia": 0.98
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

def dimensionar_tuberia(calibre):
    if calibre in ["14 AWG", "12 AWG", "10 AWG"]:
        return '3/4" Conduit EMT'
    elif calibre in ["8 AWG", "6 AWG"]:
        return '1" Conduit EMT'
    else:
        return '1 1/4" Conduit RMC'

# ==========================================
# GENERADORES DE PDF (REPORTLAB)
# ==========================================
def crear_pdf_solo_presupuesto(datos, logo_raw=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    t_empresa = ParagraphStyle(name="PEmp", parent=styles["Heading1"], fontSize=17, textColor=colors.HexColor("#0f172a"), spaceAfter=2)
    s_empresa = ParagraphStyle(name="PSub", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#475569"))
    h2_style = ParagraphStyle(name="PH2", parent=styles["Heading2"], fontSize=10, textColor=colors.HexColor("#1e3a8a"), spaceBefore=6, spaceAfter=4)
    cell_style = ParagraphStyle(name="PCell", parent=styles["Normal"], fontSize=7.5, leading=9.5)
    cell_bold = ParagraphStyle(name="PCellB", parent=styles["Normal"], fontSize=7.5, leading=9.5, fontName="Helvetica-Bold")

    # Cabecera con Logotipo
    logo_img = RLImage(io.BytesIO(logo_raw), width=130, height=45) if logo_raw else Paragraph("<b>ZONA ZERO</b>", t_empresa)
    info_header = [
        [logo_img, Paragraph("<b>ZONA ZERO 'ALL ENGINEERING SOLUTIONS'</b><br/>Saltillo, Coahuila | Instalaciones Fotovoltaicas y Eléctricas<br/>Tel / WhatsApp de Contacto", s_empresa)]
    ]
    th = Table(info_header, colWidths=[150, 390])
    th.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(th)
    story.append(Spacer(1, 4))

    # Franja de Título
    story.append(Table([[Paragraph("<font color='white'><b>COTIZACIÓN COMERCIAL - SISTEMA FOTOVOLTAICO INTERCONECTADO</b></font>", cell_bold)]],
                       colWidths=[540],
                       style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1e3a8a")),
                              ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                              ('TOPPADDING', (0,0), (-1,-1), 4),
                              ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    story.append(Spacer(1, 6))

    # Datos Generales
    datos_gen = [
        [Paragraph("<b>Cliente:</b>", cell_bold), Paragraph(str(datos['cliente']), cell_style),
         Paragraph("<b>Ubicación:</b>", cell_bold), Paragraph(str(datos['ciudad']), cell_style)],
        [Paragraph("<b>Servicio / RPU:</b>", cell_bold), Paragraph(str(datos['rpu']), cell_style),
         Paragraph("<b>Tensión CA:</b>", cell_bold), Paragraph(f"{datos['vac']}V", cell_style)],
        [Paragraph("<b>Potencia Total:</b>", cell_bold), Paragraph(f"<b>{datos['kwp']:.2f} kWp</b>", cell_style),
         Paragraph("<b>No. Módulos:</b>", cell_bold), Paragraph(f"{datos['n_paneles']} piezas", cell_style)]
    ]
    tg = Table(datos_gen, colWidths=[90, 180, 90, 180])
    tg.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(tg)
    story.append(Spacer(1, 6))

    # Equipamiento Principal
    story.append(Paragraph("1. Equipamiento Seleccionado", h2_style))
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
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (2,0), (2,-1), 'CENTER')
    ]))
    story.append(te)
    story.append(Spacer(1, 6))

    # Alcance del Suministro
    story.append(Paragraph("2. Alcance del Proyecto Llave en Mano", h2_style))
    alcances = [
        [Paragraph("• Suministro y montaje de paneles solares fotovoltaicos y micro/inversores seleccionados.", cell_style)],
        [Paragraph("• Estructura de aluminio para montaje en losa o cubierta con fijaciones herméticas.", cell_style)],
        [Paragraph("• Sistema de canalización conduit y cableado eléctrico en CD y CA bajo normativa NOM-001-SEDE-2012.", cell_style)],
        [Paragraph("• Centro de carga de protección con interruptores termomagnéticos y supresor de transitorios (DPS).", cell_style)],
        [Paragraph("• Sistema de puesta a tierra integral equipotencial con electrodo y conductor de puesta a tierra.", cell_style)],
        [Paragraph("• Pruebas de continuidad, aislamiento, comisionamiento del sistema y entrega de carpeta técnica para CFE.", cell_style)]
    ]
    ta = Table(alcances, colWidths=[540])
    ta.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 1.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
    ]))
    story.append(ta)
    story.append(Spacer(1, 6))

    # Inversión Económica
    story.append(Paragraph("3. Resumen de Inversión", h2_style))
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
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f8fafc")),
    ]))
    story.append(tp)
    story.append(Spacer(1, 14))

    # Líneas de Firma
    firmas = [
        [Paragraph("________________________________________<br/><b>Zona Zero 'All Engineering Solutions'</b><br/>Ingeniería y Proyectos", cell_style),
         Paragraph("________________________________________<br/><b>Aceptación del Cliente</b><br/>Firma y Fecha", cell_style)]
    ]
    tf = Table(firmas, colWidths=[270, 270])
    tf.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
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

    logo_img = RLImage(io.BytesIO(logo_raw), width=130, height=45) if logo_raw else Paragraph("<b>ZONA ZERO</b>", t_empresa)
    story.append(Table([[logo_img, Paragraph("<b>ZONA ZERO 'ALL ENGINEERING SOLUTIONS'</b><br/>Memoria Técnica de Dimensionamiento Eléctrico | NOM-001-SEDE-2012", s_empresa)]],
                       colWidths=[150, 390],
                       style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("1. Parámetros de Generación y Sitio", h2_style))
    tabla_sitio = [
        [Paragraph("<b>Cliente:</b>", cell_bold), Paragraph(str(datos['cliente']), cell_style), Paragraph("<b>Ubicación:</b>", cell_bold), Paragraph(str(datos['ciudad']), cell_style)],
        [Paragraph("<b>RPU / CFE:</b>", cell_bold), Paragraph(str(datos['rpu']), cell_style), Paragraph("<b>HSP Promedio:</b>", cell_bold), Paragraph(f"{datos['hsp']} hrs/día", cell_style)],
        [Paragraph("<b>Potencia Pico (kWp):</b>", cell_bold), Paragraph(f"{datos['kwp']:.2f} kWp", cell_style), Paragraph("<b>Inclinación:</b>", cell_bold), Paragraph(f"{datos['inclinacion']}° al Sur", cell_style)],
        [Paragraph("<b>Generación Bimestral:</b>", cell_bold), Paragraph(f"{datos['gen_bimestral']:.0f} kWh", cell_style), Paragraph("<b>Cobertura:</b>", cell_bold), Paragraph(f"{datos['pct_cobertura']:.1f} %", cell_style)]
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
    
    # Anchos calibrados y textos en Paragraph para evitar traslape
    tabla_elec = [
        [Paragraph("<b>Circuito</b>", cell_bold),
         Paragraph("<b>Conductor</b>", cell_bold),
         Paragraph("<b>Canalización</b>", cell_bold),
         Paragraph("<b>Protección Sobrecorriente</b>", cell_bold),
         Paragraph("<b>Caída %</b>", cell_bold)],
        [Paragraph("Lado CD (Generación)", cell_style),
         Paragraph(str(datos['cal_cd']), cell_style),
         Paragraph(str(datos['tub_cd']), cell_style),
         Paragraph(f"{datos['prot_cd']}A Fusible / DPS 1000V", cell_style),
         Paragraph(f"{datos['caida_cd']:.2f}%", cell_style)],
        [Paragraph("Lado CA (Interconexión)", cell_style),
         Paragraph(str(datos['cal_ca']), cell_style),
         Paragraph(str(datos['tub_ca']), cell_style),
         Paragraph(f"{datos['prot_ca']}A Termomagnético", cell_style),
         Paragraph(f"{datos['caida_ca']:.2f}%", cell_style)]
    ]
    te = Table(tabla_elec, colWidths=[65, 115, 160, 130, 70])
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
        [Paragraph("• <b>Art. 690-8(a)(1):</b> Corriente máxima de circuito fotovoltaico calculada como 125% de la corriente de cortocircuito (Isc) del módulo.", cell_style)],
        [Paragraph("• <b>Art. 690-8(b)(1):</b> Dispositivos de sobrecorriente dimensionados al 125% de la corriente continua de diseño (Isc × 1.25 × 1.25).", cell_style)],
        [Paragraph("• <b>Art. 310-15:</b> Conductores de cobre con aislamiento THHN/THHW-LS seleccionados por ampacidad continua y corregidos por caída de tensión admisible menor al 2%.", cell_style)],
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
# INTERFAZ DE CAPTURA (CAMPOS EN BLANCO)
# ==========================================
col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader("1. Datos del Cliente y Servicio")
    cliente = st.text_input("Nombre del Cliente / Empresa", value="", placeholder="Ej. Juan Pérez / Taller Industrial")
    ciudad = st.text_input("Ciudad / Ubicación", value="", placeholder="Ej. Saltillo, Coahuila")

    c1, c2 = st.columns(2)
    with c1:
        hsp = st.number_input("Horas Solares Pico (HSP)", min_value=0.0, max_value=10.0, value=None, placeholder="Ej. 5.6")
    with c2:
        inclinacion = st.number_input("Inclinación de Paneles (°)", min_value=0.0, max_value=90.0, value=None, placeholder="Ej. 25.0")

    rpu = st.text_input("No. de Servicio CFE / RPU", value="", placeholder="Ej. 012345678901")
    servicio_ca = st.selectbox("Tipo de Acometida CA", ["Bifásico 2F-3H (220V/127V)", "Monofásico 1F-2H (127V)", "Trifásico 3F-4H (220V/127V)"])
    consumo_bim = st.number_input("Consumo Promedio Bimestral (kWh)", min_value=0.0, value=None, placeholder="Ej. 1450")

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
            "voc": voc or 49.8, "isc": isc or 13.98, "temp_coeff_voc": -0.28
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
                v_mppt_min, v_mppt_max, voc_max = 16.0, 60.0, 65.0
            else:
                mod_max = 24
                v_mppt_min = st.number_input("Vmin MPPT (V)", min_value=0.0, value=None, placeholder="Ej. 90")
                v_mppt_max = st.number_input("Vmax MPPT (V)", min_value=0.0, value=None, placeholder="Ej. 550")
                voc_max = st.number_input("Voltaje Máx CD (V)", min_value=0.0, value=None, placeholder="Ej. 600")

        i_spec = {
            "tipo": "micro" if tipo_inv == "Microinversor" else "central",
            "potencia": pot_ca or 2000.0,
            "vac": vac_in,
            "fases": fases_in,
            "modulos_max": mod_max,
            "v_mppt_min": v_mppt_min or 90.0,
            "v_mppt_max": v_mppt_max or 550.0,
            "voc_max": voc_max or 600.0,
            "eficiencia": 0.97
        }

    st.write("---")

    c3, c4 = st.columns(2)
    with c3:
        dist_cd = st.number_input("Distancia CD (m)", min_value=0.0, value=None, placeholder="Ej. 12.0")
    with c4:
        dist_ca = st.number_input("Distancia CA (m)", min_value=0.0, value=None, placeholder="Ej. 18.0")

    subtotal_manual = st.number_input("Subtotal del Proyecto (MXN antes de IVA)", min_value=0.0, value=None, placeholder="Ej. 75000.00")

st.divider()

# ==========================================
# MOTOR DE CÁLCULO
# ==========================================
campos_listos = (consumo_bim is not None and consumo_bim > 0 and 
                 hsp is not None and hsp > 0 and 
                 dist_cd is not None and dist_ca is not None)

if not campos_listos:
    st.info("👋 Ingresa los datos de consumo bimestral, HSP y distancias para ejecutar el cálculo y generar los presupuestos.")
else:
    # Cálculo Solar
    consumo_diario = consumo_bim / 60.0
    potencia_pico_kw = consumo_diario / (hsp * 0.80)
    n_paneles = math.ceil((potencia_pico_kw * 1000) / p_spec["p_watts"])
    kwp_real = (n_paneles * p_spec["p_watts"]) / 1000.0
    gen_bimestral = kwp_real * hsp * 60 * 0.80
    pct_cobertura = (gen_bimestral / consumo_bim) * 100.0

    if i_spec["tipo"] == "micro":
        topologia = "Microinversores"
        n_inversores = math.ceil(n_paneles / i_spec["modulos_max"])
        vac = i_spec["vac"]
        es_tri = i_spec.get("fases", 1) == 3
    else:
        topologia = "Inversor Central"
        n_inversores = 1
        vac = i_spec["vac"]
        es_tri = i_spec.get("fases", 1) == 3

    # Lado CD
    i_diseno_cd = p_spec["isc"] * 1.25 * 1.25
    prot_cd = seleccionar_proteccion(i_diseno_cd)
    cal_cd, caida_cd = calcular_calibre(i_diseno_cd, dist_cd, p_spec["vmp"], caida_max_pct=1.5, es_trifasico=False)
    tub_cd = dimensionar_tuberia(cal_cd)

    # Lado CA
    potencia_ca_total = min(kwp_real * 1000, n_inversores * i_spec["potencia"])
    i_nom_ca = potencia_ca_total / (math.sqrt(3) * vac) if es_tri else potencia_ca_total / vac
    i_diseno_ca = i_nom_ca * 1.25
    prot_ca = seleccionar_proteccion(i_diseno_ca)
    cal_ca, caida_ca = calcular_calibre(i_diseno_ca, dist_ca, vac, caida_max_pct=2.0, es_trifasico=es_tri)
    tub_ca = dimensionar_tuberia(cal_ca)

    # Presupuesto
    subtotal = subtotal_manual if (subtotal_manual is not None and subtotal_manual > 0) else (kwp_real * 1000 * 21.5 / 1.16)
    iva = subtotal * 0.16
    total_sistema = subtotal + iva

    # Métricas Visuales
    st.subheader("3. Resultados del Dimensionamiento")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Paneles Necesarios", f"{n_paneles} módulos", f"{kwp_real:.2f} kWp")
    m2.metric("Generación Est.", f"{gen_bimestral:.0f} kWh/bim", f"{pct_cobertura:.1f}% cubierto")
    m3.metric("Protección CA", f"{prot_ca} A", f"Calibre: {cal_ca}")
    m4.metric("Inversión Total", f"${total_sistema:,.2f} MXN", f"Subtotal: ${subtotal:,.2f}")

    # Datos empaquetados para los PDFs
    datos_pdf = {
        "cliente": cliente if cliente else "Sin especificar",
        "ciudad": ciudad if ciudad else "Sin especificar",
        "rpu": rpu if rpu else "Sin especificar",
        "hsp": hsp, "inclinacion": inclinacion if inclinacion else 25.0,
        "kwp": kwp_real, "n_paneles": n_paneles, "panel_nombre": panel_sel, "inv_nombre": inv_sel,
        "gen_bimestral": gen_bimestral, "pct_cobertura": pct_cobertura, "topologia": topologia,
        "n_inversores": n_inversores, "vac": vac,
        "cal_cd": cal_cd, "tub_cd": tub_cd, "prot_cd": prot_cd, "caida_cd": caida_cd,
        "cal_ca": cal_ca, "tub_ca": tub_ca, "prot_ca": prot_ca, "caida_ca": caida_ca,
        "subtotal": subtotal, "iva": iva, "total": total_sistema
    }

    st.write("---")
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
