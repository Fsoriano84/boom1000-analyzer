# app_boom1000.py
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import tempfile
import os

# --- Funciones de análisis ---
def preprocess_image(image):
    img = np.array(image)
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    return img, gray

def detect_candles(gray, min_area=80, max_area=1500):
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    candles = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if min_area < area < max_area:
            x, y, w, h = cv2.boundingRect(cnt)
            candles.append({'x': x, 'y': y, 'w': w, 'h': h, 'area': area})
    
    candles = sorted(candles, key=lambda c: c['x'])
    return candles[-50:]

def detect_trend(candles, img_height):
    if len(candles) < 3:
        return "Indefinido", 0
    
    prices = [img_height - (c['y'] + c['h'] // 2) for c in candles[-10:]]
    slope = np.polyfit(range(len(prices)), prices, 1)[0]
    
    if slope > 2:
        trend = "Alcista"
    elif slope < -2:
        trend = "Bajista"
    else:
        trend = "Lateral"
    
    return trend, abs(slope)

def detect_last_candle_pattern(candle, gray):
    x, y, w, h = candle['x'], candle['y'], candle['w'], candle['h']
    roi = gray[y:y+h, x:x+w]
    if roi.size == 0:
        return "N/A"
    
    mean_val = cv2.mean(roi)[0]
    color = "Verde" if mean_val > 150 else "Roja"
    
    ratio = h / w
    
    if ratio > 4:
        return "Martillo" if color == "Verde" else "Estrella Fugaz"
    elif ratio < 1.2:
        return "Doji" if h < 15 else "Vela Pequeña"
    elif ratio > 2.5 and color == "Verde":
        return "Cuerpo Largo Alcista"
    elif ratio > 2.5 and color == "Roja":
        return "Cuerpo Largo Bajista"
    else:
        return f"Vela {color}"

def detect_support_resistance(candles, img_height, tolerance=8):
    if len(candles) == 0:
        return [], []
    
    lows = [img_height - (c['y'] + c['h']) for c in candles]
    highs = [img_height - c['y'] for c in candles]
    
    def cluster_levels(levels):
        levels = sorted(set([round(l, -1) for l in levels]))
        clusters = []
        for l in levels:
            if not clusters or abs(l - clusters[-1]) > tolerance:
                clusters.append(l)
            else:
                clusters[-1] = (clusters[-1] + l) / 2
        return sorted(clusters)
    
    supports = cluster_levels(lows)[-3:]
    resistances = cluster_levels(highs)[:3]
    return supports, resistances

def analyze_frame(image, timeframe):
    img, gray = preprocess_image(image)
    candles = detect_candles(gray)
    img_height = img.shape[0] if len(img.shape) == 3 else gray.shape[0]

    trend, strength = detect_trend(candles, img_height)
    supports, resistances = detect_support_resistance(candles, img_height)
    
    last_pattern = "N/A"
    if candles:
        last_pattern = detect_last_candle_pattern(candles[-1], gray)

    score = 0
    recom = "Esperar"
    confidence = "Baja"

    if trend == "Bajista" and "Martillo" in last_pattern and supports:
        score += 3
    if trend == "Lateral" and "Doji" in last_pattern:
        score += 1
    if trend == "Bajista" and len(candles) > 30:
        score += 2

    if score >= 4:
        recom = "👉 POSIBLE COMPRA (anticipar boom)"
        confidence = "Media-Alta"
    elif score >= 2:
        recom = "Observar zona de soporte"
        confidence = "Media"
    else:
        recom = "Evitar compra por ahora"
        confidence = "Baja"

    return {
        "timeframe": timeframe,
        "trend": trend,
        "last_candle": last_pattern,
        "supports": supports,
        "resistances": resistances,
        "recommendation": recom,
        "confidence": confidence,
        "candle_count": len(candles)
    }

# --- Interfaz de Streamlit ---
st.set_page_config(page_title="🔍 Boom1000 Vision Analyzer", layout="centered")
st.title("🚀 Boom1000 Vision Analyzer")
st.markdown("Sube dos imágenes del gráfico B1000: **1H y 24H** para un análisis completo.")

col1, col2 = st.columns(2)

with col1:
    img_1h = st.file_uploader("📸 Gráfico 1H", type=["png", "jpg", "jpeg"], key="1h")
    if img_1h:
        st.image(img_1h, caption="1H - Vista previa", width=300)

with col2:
    img_24h = st.file_uploader("📸 Gráfico 24H", type=["png", "jpg", "jpeg"], key="24h")
    if img_24h:
        st.image(img_24h, caption="24H - Vista previa", width=300)

if st.button("🔍 Analizar Ambas Imágenes"):
    if not img_1h or not img_24h:
        st.error("Por favor sube ambas imágenes (1H y 24H)")
    else:
        with st.spinner("Analizando imágenes..."):

            def save_temp_image(uploaded_file):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                temp_file.write(uploaded_file.read())
                temp_file.close()
                return temp_file.name

            path_1h = save_temp_image(img_1h)
            path_24h = save_temp_image(img_24h)

            image_1h = Image.open(path_1h)
            image_24h = Image.open(path_24h)

            result_1h = analyze_frame(image_1h, "1H")
            result_24h = analyze_frame(image_24h, "24H")

            os.unlink(path_1h)
            os.unlink(path_24h)

            st.success("✅ Análisis completado")
            st.markdown("## 📊 Informe de Análisis Integrado")

            st.markdown(f"""
            ### 🕰️ **Marco temporal: 1H**
            - **Tendencia:** {result_1h['trend']}
            - **Última vela:** {result_1h['last_candle']}
            - **Soportes clave:** {result_1h['supports']}
            - **Resistencias:** {result_1h['resistances']}
            - **Recomendación:** {result_1h['recommendation']}
            - **Confianza:** {result_1h['confidence']}

            ### 📅 **Marco temporal: 24H**
            - **Tendencia general:** {result_24h['trend']}
            - **Última vela (24H):** {result_24h['last_candle']}
            - **Soportes clave (24H):** {result_24h['supports']}
            - **Recomendación:** {result_24h['recommendation']}

            ## 🎯 **Conclusión Final**
            """)

            final_recom = "⚠️ Esperar confirmación"
            if "POSIBLE COMPRA" in result_1h['recommendation'] and "Bajista" in result_24h['trend']:
                final_recom = "🟢 **ALTA PROBABILIDAD DE COMPRA** – El gráfico de 1H muestra señal de reversión tras caída en 24H. ¡Podría estar cerca el boom!"
            elif "Observar" in result_1h['recommendation']:
                final_recom = "🟡 **OBSERVAR ZONA DE SOPORTE** – Aún no hay señal clara, pero el boom podría estar cerca."
            else:
                final_recom = "🔴 **NO COMPRAR AHORA** – Falta señal de reversión o soporte claro."

            st.markdown(f"<div style='background:#0d1b2a; color:#e0e1dd; padding:15px; border-radius:10px; font-size:1.1em;'>{final_recom}</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("💡 **Consejo**: Usa esta herramienta junto con el conteo de ticks (si lo llevas) para mayor precisión. El boom suele ocurrir cada ~1000 ticks.")
