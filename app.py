import streamlit as st
import math
import io
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(
    page_title="CALCULADORA FV ZONA ZERO",
    layout="wide",
    page_icon="⚡"
)

# ==========================================
# 1. CATALOGOS PREDEFINIDOS Y TABLAS NOM-001
# ==========================================
PANEL_CATALOG = {
    "-- Seleccionar del catálogo --": None,
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
    "-- Seleccionar del catálogo --": None,
    "Microinversor Hoymiles HMS-2000-4T (4 MPPT, 2000W, 220V CA)": {
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
# 2. GENERADORES DE PDF CON LOGO
# ==========================================
def preparar_imagen_logo(logo_bytes, max_w=140, max_h=50):
    if not logo_bytes:
        return None
    try:
        img_buffer = io.BytesIO(logo_bytes)
        pil_img = PILImage.open(img_buffer)
        w, h = pil_img.size
        ratio = min(max_w / w, max_h / h)
        return RLImage(io.BytesIO(logo_bytes), width=w * ratio, height=h * ratio)
    except Exception:
        return None

def crear_pdf_solo_presupuesto(datos, logo_bytes):
    """Genera exclusivamente la cotización formal de 1 sola página con logo."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=32,
        bottomMargin=32
    )
    story = []
    styles = getSampleStyleSheet()

    header_title = ParagraphStyle(
        name="CotTitle",
        parent=styles["Heading1"],
        fontSize=17,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceAfter=2
    )
    badge_style = ParagraphStyle(
        name="Badge",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0369a1"),
        fontName="Helvetica-Bold"
    )
    section_title = ParagraphStyle(
        name="SecTitle",
        parent=styles["Heading2"],
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#1e3a8a"),
        fontName="Helvetica-Bold",
        spaceBefore=7,
        spaceAfter=3
    )
    body_text = ParagraphStyle(
        name="BodyTextCustom",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155")
    )
    terms_text = ParagraphStyle(
        name="Terms",
        parent=styles["Normal"],
        fontSize=6.8,
        leading=9,
        textColor=colors.HexColor("#64748b")
    )

    # Encabezado con Logo (si existe)
    logo_obj = preparar_imagen_logo(logo_bytes, max_w=130, max_h=45)
    titulos_header = [
        Paragraph("ZONA ZERO - ENERGÍA SOLAR", header_title),
        Paragraph("PROPUESTA TÉCNICA Y COMERCIAL | SISTEMA FOTOVOLTAICO INTERCONECTADO", badge_style)
    ]

    if logo_obj:
        header_table = Table([[titulos_header, logo_obj]], colWidths=[390, 150])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        story.append(header_table)
    else:
        for t in titulos_header:
            story.append(t)
    
    story.append(Spacer(1, 6))

    # Ficha del Cliente y Proyecto
    info_cliente_data = [
        [
            Paragraph(f"<b>Cliente:</b> {datos['cliente']}<br/><b>Servicio CFE / RPU:</b> {datos['rpu']}<br/><b>Ubicación:</b> {datos['ciudad']}", body_text),
            Paragraph(f"<b>Capacidad Total:</b> {datos['kwp']:.2f} kWp<br/><b>Módulos:</b> {datos['n_paneles']} piezas ({datos['panel_nombre'][:28]})<br/><b>Inversor:</b> {datos['n_inversores']}x ({datos['inv_nombre'][:28]})", body_text)
        ]
    ]
    t_info = Table(info_cliente_data, colWidths=[270, 270])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 5))

    # Indicadores Financieros y Energéticos
    story.append(Paragraph("Resumen de Beneficio Energético y Retorno", section_title))
    resumen_financiero = [
        ["Generación Estimada", "Ahorro Bimestral Proyectado", "Mitigación de Consumo", "Retorno de Inversión"],
        [f"{datos['gen_bimestral']:,.0f} kWh/bim", f"${datos['ahorro_bimestral']:,.2f} MXN", f"{datos['pct_cobertura']:.1f} %", f"{datos['roi']:.1f} Años"]
    ]
    t_resumen = Table(resumen_financiero, colWidths=[135, 135, 135, 135])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284c7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bae6fd")),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#f0f9ff")),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,1), (-1,1), colors.HexColor("#0369a1")),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 5))

    # Desglose del Presupuesto
    story.append(Paragraph("Desglose de Inversión (Proyecto Llave en Mano)", section_title))
    tabla_costos = [
        ["Concepto / Partida", "Especificación de Suministro e Instalación", "Importe (MXN)"],
        [
            "Módulos e Inversores",
            f"{datos['n_paneles']} paneles solares fotovoltaicos + tecnología de micro/inversores",
            f"${datos['costo_equipos']:,.2f}"
        ],
        [
            "Estructura de Montaje",
            "Perfilería de aluminio anodizado AL6005-T5 con tornillería de acero inoxidable",
            f"${datos['costo_estructura']:,.2f}"
        ],
        [
            "Instalación Eléctrica NOM",
            f"Cable fotovoltaico, canalización conduit, protecciones CD ({datos['prot_cd']}A) y CA ({datos['prot_ca']}A)",
            f"${datos['costo_electrico']:,.2f}"
        ],
        [
            "Mano de Obra y Trámites",
            "Mano de obra certificada, sistema de tierras físicas y gestión de interconexión CFE",
            f"${datos['costo_mano_obra']:,.2f}"
        ],
        ["", "SUBTOTAL", f"${datos['subtotal']:,.2f}"],
        ["", "I.V.A. (16%)", f"${datos['iva']:,.2f}"],
        ["", "INVERSIÓN TOTAL", f"${datos['total']:,.2f}"]
    ]
    t_costos = Table(tabla_costos, colWidths=[140, 260, 140])
    t_costos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-4), 0.5, colors.HexColor("#cbd5e1")),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('FONTNAME', (1,-3), (2,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (1,-3), (2,-2), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (1,-1), (2,-1), colors.HexColor("#e2e8f0")),
        ('FONTSIZE', (1,-1), (2,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_costos)
    story.append(Spacer(1, 8))

    # Términos y Condiciones
    condiciones = (
        "<b>Términos y Condiciones Comerciales:</b><br/>"
        "• Validez de la propuesta: 15 días naturales a partir de su entrega.<br/>"
        "• Garantías: 12 a 25 años en generación de paneles solares, 10 a 12 años en inversores, 1 año en mano de obra e instalación.<br/>"
        "• Esquema de pago: 60% anticipo al ordenar materiales, 30% a la entrega del equipo en sitio y 10% al finalizar la instalación física.<br/>"
        "• La colocación y configuración del medidor bidireccional está sujeta a los tiempos y calendarios de CFE Distribución."
    )
    story.append(Paragraph(condiciones, terms_text))
    story.append(Spacer(1, 16))

    # Firmas
    firmas = [
        ["________________________________________", "________________________________________"],
        ["ZONA ZERO - Ingeniero Instalador", "Aceptación del Cliente"]
    ]
    t_firmas = Table(firmas, colWidths=[270, 270])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,1), 7.5),
        ('TEXTCOLOR', (0,1), (-1,1), colors.HexColor("#475569")),
    ]))
    story.append(t_firmas)

    doc.build(story)
    buffer.seek(0)
    return buffer

def crear_pdf_memoria_tecnica(datos, logo_bytes):
    """Genera la memoria técnica de cálculo NOM-001 Art. 690 en PDF sin diagrama unifilar."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(name="DocTitle", parent=styles["Heading1"], fontSize=15, textColor=colors.HexColor("#0f172a"), spaceAfter=3)
    subtitle_style = ParagraphStyle(name="DocSub", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#475569"), spaceAfter=10)
    h2_style = ParagraphStyle(name="DocH2", parent=styles["Heading2"], fontSize=10.5, textColor=colors.HexColor("#1e3a8a"), spaceBefore=7, spaceAfter=5)

    logo_obj = preparar_imagen_logo(logo_bytes, max_w=120, max_h=40)
    titulos = [
        Paragraph("ZONA ZERO - MEMORIA DE CÁLCULO ELÉCTRICO", title_style),
        Paragraph(f"Cliente: <b>{datos['cliente']}</b> | Ubicación: <b>{datos['ciudad']}</b> | RPU: <b>{datos['rpu']}</b>", subtitle_style)
    ]
    if logo_obj:
        hdr = Table([[titulos, logo_obj]], colWidths=[400, 140])
        hdr.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        story.append(hdr)
    else:
        for t in titulos:
            story.append(t)

    story.append(Spacer(1, 8))
    story.append(Paragraph("1. Dimensionamiento del Arreglo Solar", h2_style))
    tabla_dim_data = [
        ["Parámetro", "Valor", "Parámetro", "Valor"],
        ["Potencia Total Pico", f"{datos['kwp']:.2f} kWp", "HSP Promedio", f"{datos['hsp']} hrs/día"],
        ["Número de Módulos", f"{datos['n_paneles']} piezas", "Inclinación Recomendada", f"{datos['inclinacion']}° Sur"],
        ["Modelo de Módulo", f"{datos['panel_nombre'][:26]}...", "Generación Bimestral", f"{datos['gen_bimestral']:.0f} kWh"],
        ["Inversor/Micro", f"{datos['inv_nombre'][:26]}...", "Cobertura de Consumo", f"{datos['pct_cobertura']:.1f} %"]
    ]
    t1 = Table(tabla_dim_data, colWidths=[135, 135, 135, 135])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Especificaciones Eléctricas de Interconexión (NOM-001 Art. 690)", h2_style))
    tabla_elec = [
        ["Circuito", "Conductor Calculado", "Canalización", "Protección Contra Sobrecorriente", "Caída Tensión"],
        ["Lado CD (Solar)", datos['cal_cd'], datos['tub_cd'], f"{datos['prot_cd']}A Fusible / DPS CD", f"{datos['caida_cd']:.2f}%"],
        ["Lado CA (Red)", datos['cal_ca'], datos['tub_ca'], f"{datos['prot_ca']}A Termomagnético", f"{datos['caida_ca']:.2f}%"]
    ]
    t2 = Table(tabla_elec, colWidths=[85, 115, 130, 130, 80])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ALIGN', (4,1), (4,-1), 'CENTER'),
    ]))
    story.append(t2)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. BARRA LATERAL: LOGO DE LA EMPRESA
# ==========================================
with st.sidebar:
    st.header("⚡ ZONA ZERO")
    st.caption("Personalización de Marca")
    logo_file = st.file_uploader("Cargar Logotipo (PNG / JPG)", type=["png", "jpg", "jpeg"])
    logo_bytes = logo_file.read() if logo_file is not None else None

    if logo_bytes:
        st.image(logo_bytes, caption="Logotipo cargado", use_container_width=True)
    else:
        st.info("Sube tu logo para que aparezca aquí y en la cotización PDF.")

# ==========================================
# 4. INTERFAZ: ENCABEZADO Y CAMPOS EN BLANCO
# ==========================================
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("⚡ CALCULADORA FV ZONA ZERO")
    st.caption("Cálculo bajo NOM-001-SEDE-2012 Art. 690 y Cotizador Profesional")
with header_col2:
    if logo_bytes:
        st.image(logo_bytes, width=120)

col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader("1. Datos del Cliente y Servicio CFE")
    cliente = st.text_input("Nombre del Cliente / Empresa", value="", placeholder="Ej. Juan Pérez / Bodega Industrial")
    ciudad = st.text_input("Ciudad / Ubicación", value="", placeholder="Ej. Saltillo, Coah")

    c1, c2 = st.columns(2)
    with c1:
        hsp = st.number_input("Horas Solares Pico (HSP)", min_value=0.0, value=None, step=0.1, placeholder="Ej. 5.6")
    with c2:
        inclinacion = st.number_input("Inclinación de Paneles (°)", min_value=0.0, value=None, step=1.0, placeholder="Ej. 25.0")

    rpu = st.text_input("No. de Servicio CFE / RPU", value="", placeholder="12 dígitos del recibo")
    servicio_ca = st.selectbox("Tipo de Acometida CFE", ["Bifásico 2F-3H (220V/127V)", "Monofásico 1F-2H (127V)", "Trifásico 3F-4H (220V/127V)"])
    
    consumo_bim = st.number_input("Consumo Promedio Bimestral (kWh)", min_value=0.0, value=None, step=50.0, placeholder="Ej. 1450")
    tarifa_costo_kwh = st.number_input("Costo promedio por kWh (MXN)", min_value=0.0, value=None, step=0.1, placeholder="Ej. 4.10")

with col_b:
    st.subheader("2. Equipos y Topología")
    
    # PANEL SOLAR: Catálogo o Manual
    panel_manual = st.checkbox("⚙️ Ingresar Módulo Solar manualmente", value=False)
    p_spec = None
    panel_sel = ""

    if not panel_manual:
        panel_sel = st.selectbox("Módulo Fotovoltaico (Catálogo)", list(PANEL_CATALOG.keys()))
        p_spec = PANEL_CATALOG[panel_sel]
    else:
        st.caption("Ficha Técnica del Módulo Solar:")
        c_pm1, c_pm2 = st.columns(2)
        with c_pm1:
            nom_mod = st.text_input("Marca / Modelo del Panel", value="", placeholder="Ej. Longi Hi-MO 6")
            p_watts = st.number_input("Potencia Pico Pmp (W)", min_value=0.0, value=None, step=10.0, placeholder="550")
            voc = st.number_input("Voltaje Circuito Abierto Voc (V)", min_value=0.0, value=None, step=0.1, placeholder="49.8")
        with c_pm2:
            vmp = st.number_input("Voltaje Máx. Potencia Vmp (V)", min_value=0.0, value=None, step=0.1, placeholder="42.1")
            isc = st.number_input("Corriente Cortocircuito Isc (A)", min_value=0.0, value=None, step=0.1, placeholder="13.98")
            imp = st.number_input("Corriente Máx. Potencia Imp (A)", min_value=0.0, value=None, step=0.1, placeholder="13.06")
        
        if nom_mod and p_watts and voc and vmp and isc and imp:
            panel_sel = f"{nom_mod} ({p_watts:.0f}W)"
            p_spec = {
                "p_watts": float(p_watts), "vmp": float(vmp), "imp": float(imp),
                "voc": float(voc), "isc": float(isc), "temp_coeff_voc": -0.28
            }

    st.write("---")

    # INVERSOR: Catálogo o Manual
    inv_manual = st.checkbox("⚙️ Ingresar Inversor / Microinversor manualmente", value=False)
    i_spec = None
    inv_sel = ""

    if not inv_manual:
        inv_sel = st.selectbox("Inversor (Catálogo)", list(INVERTER_CATALOG.keys()))
        i_spec = INVERTER_CATALOG[inv_sel]
    else:
        st.caption("Ficha Técnica del Inversor / Microinversor:")
        tipo_inv = st.radio("Tipo de Dispositivo", ["Microinversor", "Inversor Central"], horizontal=True)
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            nom_inv_custom = st.text_input("Marca y Modelo", value="", placeholder="Ej. Hoymiles HMS-2000")
            pot_ca = st.number_input("Potencia Nominal CA (Watts)", min_value=0.0, value=None, step=500.0, placeholder="2000")
            vac_in = st.selectbox("Tensión de Salida CA (V)", [220, 127, 440], index=0)
            fases_in = st.selectbox("Número de Fases CA", [2, 1, 3], index=0)
        with col_inv2:
            if tipo_inv == "Microinversor":
                mod_max = st.number_input("Módulos por Micro", min_value=1, max_value=8, value=4)
                v_mppt_min, v_mppt_max, voc_max = 16.0, 60.0, 65.0
            else:
                mod_max = st.number_input("Capacidad máx. módulos sugerida", min_value=2, max_value=80, value=20)
                v_mppt_min = st.number_input("Vmin MPPT (V)", min_value=0.0, value=None, step=10.0, placeholder="90")
                v_mppt_max = st.number_input("Vmax MPPT (V)", min_value=0.0, value=None, step=10.0, placeholder="550")
                voc_max = st.number_input("Voltaje Máx. Admisible CD (V)", min_value=0.0, value=None, step=10.0, placeholder="600")

        if nom_inv_custom and pot_ca:
            inv_sel = nom_inv_custom
            i_spec = {
                "tipo": "micro" if tipo_inv == "Microinversor" else "central",
                "potencia": float(pot_ca),
                "vac": vac_in,
                "fases": fases_in,
                "modulos_max": mod_max,
                "v_mppt_min": float(v_mppt_min) if v_mppt_min else 80.0,
                "v_mppt_max": float(v_mppt_max) if v_mppt_max else 550.0,
                "voc_max": float(voc_max) if voc_max else 600.0,
                "eficiencia": 0.97
            }

    st.write("---")

    c3, c4 = st.columns(2)
    with c3:
        dist_cd = st.number_input("Distancia CD (módulos a inversor en m)", min_value=0.0, value=None, step=1.0, placeholder="Ej. 12.0")
    with c4:
        dist_ca = st.number_input("Distancia CA (inversor a centro de carga en m)", min_value=0.0, value=None, step=1.0, placeholder="Ej. 18.0")

    costo_por_watt = st.number_input(
        "Precio estimado por Watt instalado (MXN/Wp)", 
        min_value=0.0, value=None, step=0.5, 
        placeholder="Ej. 21.5"
    )

st.divider()

# ==========================================
# 5. VALIDACIÓN Y MOTOR DE CÁLCULO
# ==========================================
datos_listos = all([
    cliente,
    ciudad,
    hsp and hsp > 0,
    inclinacion is not None,
    consumo_bim and consumo_bim > 0,
    tarifa_costo_kwh and tarifa_costo_kwh > 0,
    p_spec is not None,
    i_spec is not None,
    dist_cd and dist_cd > 0,
    dist_ca and dist_ca > 0,
    costo_por_watt and costo_por_watt > 0
])

if not datos_listos:
    st.info("👈 Llena los campos vacíos de cliente, consumo y equipos para generar el dimensionamiento y las cotizaciones.")
else:
    consumo_diario = consumo_bim / 60.0
    potencia_pico_kw = consumo_diario / (hsp * 0.80)
    n_paneles = math.ceil((potencia_pico_kw * 1000.0) / p_spec["p_watts"])
    kwp_real = (n_paneles * p_spec["p_watts"]) / 1000.0
    gen_bimestral = kwp_real * hsp * 60.0 * 0.80
    pct_cobertura = (gen_bimestral / consumo_bim) * 100.0

    if i_spec["tipo"] == "micro":
        topologia = "Microinversores"
        n_inversores = math.ceil(n_paneles / i_spec["modulos_max"])
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

    # CA NOM-001 Art. 690: Carga continua al 125%
    potencia_ca_total = min(kwp_real * 1000.0, n_inversores * i_spec["potencia"])
    i_nom_ca = potencia_ca_total / (math.sqrt(3) * vac) if es_tri else potencia_ca_total / vac
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

    # ==========================================
    # 6. RESULTADOS VISUALES
    # ==========================================
    st.subheader("3. Resultados del Dimensionamiento")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Paneles Necesarios", f"{n_paneles} piezas", f"{kwp_real:.2f} kWp")
    m2.metric("Generación Proyectada", f"{gen_bimestral:.0f} kWh/bim", f"{pct_cobertura:.1f}% cubierto")
    m3.metric("Protección CA", f"{prot_ca} A", f"Cal: {cal_ca}")
    m4.metric("Tecnología", f"{n_inversores} unidad(es)", topologia)
    m5.metric("Retorno de Inversión", f"{roi_anos:.1f} años", f"${ahorro_bim:,.0f}/bim")

    st.write("---")

    # Empaquetado para PDF
    datos_pdf = {
        "cliente": cliente, "ciudad": ciudad, "rpu": rpu if rpu else "S/N", "hsp": hsp, "inclinacion": inclinacion,
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

    pdf_presupuesto = crear_pdf_solo_presupuesto(datos_pdf, logo_bytes)
    with btn_col1:
        st.download_button(
            label="📑 Descargar SOLO Cotización (1 Hoja con Logo)",
            data=pdf_presupuesto,
            file_name=f"Cotizacion_ZonaZero_{cliente.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    pdf_memoria = crear_pdf_memoria_tecnica(datos_pdf, logo_bytes)
    with btn_col2:
        st.download_button(
            label="📘 Descargar Memoria Técnica NOM-001 (PDF)",
            data=pdf_memoria,
            file_name=f"Memoria_Tecnica_ZonaZero_{cliente.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
