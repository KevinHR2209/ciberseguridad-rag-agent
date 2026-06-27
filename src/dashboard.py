import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.logger import leer_logs

st.set_page_config(page_title="Dashboard Observabilidad", layout="wide", page_icon="📊")

st.title("📊 Dashboard de Observabilidad")
st.caption("Monitoreo del Agente RAG — Ley 21.663 | EP3 ISY0101")

logs = leer_logs()

if not logs:
    st.info("Sin datos aún. Ejecuta el agente principal y realiza algunas consultas.")
    st.markdown("Lanza el agente con: `streamlit run src/app.py`")
    st.stop()

df = pd.DataFrame(logs)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["error_bool"] = df["error"].notna()
df["latencia_s"] = df["latencia_s"].astype(float)
df["precision_score"] = df["precision_score"].astype(float)

# ── Métricas resumen ────────────────────────────────────────────────────────
st.subheader("Resumen General")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total consultas", len(df))
col2.metric("Latencia promedio", f"{df['latencia_s'].mean():.2f}s")
col3.metric("Latencia máxima", f"{df['latencia_s'].max():.2f}s")
col4.metric("Precisión promedio", f"{df['precision_score'].mean():.0%}")
col5.metric("Tasa de errores", f"{df['error_bool'].mean():.0%}")

st.divider()

col_a, col_b = st.columns(2)

# ── Gráfico 1: Latencia ─────────────────────────────────────────────────────
with col_a:
    st.subheader("⏱️ Latencia por Consulta")
    fig_lat = px.line(
        df, x="timestamp", y="latencia_s",
        title="Latencia en segundos por ejecución",
        labels={"latencia_s": "Latencia (s)", "timestamp": "Tiempo"},
        markers=True, color_discrete_sequence=["#1f77b4"],
    )
    fig_lat.add_hline(
        y=df['latencia_s'].mean(), line_dash="dash", line_color="orange",
        annotation_text=f"Promedio: {df['latencia_s'].mean():.2f}s",
    )
    st.plotly_chart(fig_lat, use_container_width=True)

# ── Gráfico 2: Errores ──────────────────────────────────────────────────────
with col_b:
    st.subheader("🚨 Distribución de Errores")
    error_counts = df["error_bool"].value_counts().reset_index()
    error_counts.columns = ["Estado", "Cantidad"]
    error_counts["Estado"] = error_counts["Estado"].map({True: "Con error", False: "Exitosa"})
    fig_err = px.pie(
        error_counts, names="Estado", values="Cantidad",
        title="Consultas exitosas vs con error",
        color="Estado",
        color_discrete_map={"Exitosa": "#2ecc71", "Con error": "#e74c3c"},
    )
    st.plotly_chart(fig_err, use_container_width=True)

col_c, col_d = st.columns(2)

# ── Gráfico 3: Herramientas ─────────────────────────────────────────────────
with col_c:
    st.subheader("🔧 Herramientas Utilizadas")
    tool_counts = df["herramienta"].value_counts().reset_index()
    tool_counts.columns = ["Herramienta", "Usos"]
    fig_tools = px.bar(
        tool_counts, x="Herramienta", y="Usos",
        title="Frecuencia de uso por herramienta",
        color="Herramienta",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    st.plotly_chart(fig_tools, use_container_width=True)

# ── Gráfico 4: Precisión vs RAM ─────────────────────────────────────────────
with col_d:
    st.subheader("🧠 Precisión y Uso de RAM")
    fig_prec = go.Figure()
    fig_prec.add_trace(go.Scatter(
        x=df["timestamp"], y=df["precision_score"],
        name="Precisión", mode="lines+markers", line=dict(color="#9b59b6")
    ))
    fig_prec.add_trace(go.Scatter(
        x=df["timestamp"], y=df["ram_mb"] / df["ram_mb"].max(),
        name="RAM (normalizada)", mode="lines", line=dict(color="#e67e22", dash="dot")
    ))
    fig_prec.update_layout(
        title="Precisión vs Uso de RAM (normalizado)",
        yaxis_title="Score / RAM normalizada",
        xaxis_title="Tiempo",
    )
    st.plotly_chart(fig_prec, use_container_width=True)

st.divider()

# ── Tabla últimas consultas ─────────────────────────────────────────────────
st.subheader("📋 Últimas 20 Consultas")
cols_tabla = ["timestamp", "query", "herramienta", "latencia_s", "precision_score", "ram_mb", "error"]
df_tabla = df[cols_tabla].tail(20).sort_values("timestamp", ascending=False)
df_tabla.columns = ["Timestamp", "Query", "Herramienta", "Latencia (s)", "Precisión", "RAM (MB)", "Error"]
st.dataframe(df_tabla, use_container_width=True, hide_index=True)

# ── Detección de anomalías ──────────────────────────────────────────────────
st.subheader("🔍 Detección de Anomalías")
UMBRAL_LATENCIA = df['latencia_s'].mean() + 2 * df['latencia_s'].std()
anomalias = df[df['latencia_s'] > UMBRAL_LATENCIA]

if len(anomalias) > 0:
    st.warning(f"⚠️ Se detectaron **{len(anomalias)} consultas** con latencia anormalmente alta (> {UMBRAL_LATENCIA:.2f}s).")
    st.dataframe(anomalias[["timestamp", "query", "latencia_s", "herramienta"]].rename(columns={
        "timestamp": "Timestamp", "query": "Query",
        "latencia_s": "Latencia (s)", "herramienta": "Herramienta"
    }), use_container_width=True, hide_index=True)
else:
    st.success("✅ No se detectaron anomalías de latencia. El sistema opera dentro de parámetros normales.")

st.caption("Recarga la página para ver datos actualizados.")
