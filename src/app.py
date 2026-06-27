import streamlit as st
import os
import time
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability import registrar_metricas
from src.security import sanitizar_input, verificar_rate_limit, generar_session_id, validar_nombre_archivo

REPORTES_DIR = "reportes"
os.makedirs(REPORTES_DIR, exist_ok=True)

st.set_page_config(page_title="Consultor Ciberseguridad Ley 21.663", layout="wide")


@st.cache_resource
def load_components():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    if not os.path.exists("faiss_index"):
        st.error("No se encontró el índice FAISS. Ejecuta 'python src/ingest.py' primero.")
        st.stop()
    db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    retriever = db.as_retriever(search_kwargs={"k": 3})
    llm = OllamaLLM(model="llama3.2:1b", temperature=0.1)

    rag_template = """CONTEXTO LEGAL AUTORIZADO:
{context}

CONSULTA: {question}

Responde en español, nivel ingeniero TI. Cita el Artículo y la Ley. Sé conciso (máximo 200 palabras). Finaliza con: 'Esta interpretación no sustituye asesoría legal formal.'"""
    rag_prompt = PromptTemplate.from_template(rag_template)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    eval_template = """Eres auditor experto en Ley 21.663 de Ciberseguridad de Chile.
Sistema/proceso a evaluar: {descripcion}

Responde EXCLUSIVAMENTE con este formato (máximo 150 palabras):
VEREDICTO: [CUMPLE / INCUMPLE / REQUIERE_REVISIÓN]
NIVEL_RIESGO: [ALTO / MEDIO / BAJO]
JUSTIFICACIÓN: [cita artículos relevantes]
RECOMENDACIONES: [acciones concretas]"""
    eval_prompt = PromptTemplate.from_template(eval_template)
    eval_chain = eval_prompt | llm | StrOutputParser()

    return rag_chain, eval_chain, llm


def detectar_herramienta(query: str) -> str:
    q = query.lower()
    if any(p in q for p in ["evalúa", "cumple", "cumplimiento", "verifica", "audita", "revisa si"]):
        return "evaluar_cumplimiento"
    if any(p in q for p in ["guarda", "genera reporte", "crea reporte", "guardar", "informe"]):
        return "guardar_reporte"
    return "buscador_normativo"


def guardar_reporte_txt(nombre: str, contenido: str) -> str:
    valido, nombre_limpio = validar_nombre_archivo(nombre.strip())
    if not valido:
        return f"Error: {nombre_limpio}"
    if not nombre_limpio.endswith(".txt"):
        nombre_limpio += ".txt"
    ruta = os.path.join(REPORTES_DIR, nombre_limpio)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return f"✅ Reporte guardado en '{ruta}'."


# ── UI ─────────────────────────────────────────────────────────────
st.title("⚖️ Consultor Técnico-Legal Ciberseguridad")
st.caption("Agente RAG + 3 herramientas | Ley 21.663 Chile | EP3 ISY0101")

col1, col2 = st.columns([3, 1])
with col2:
    st.markdown("[📊 Ver Dashboard](http://localhost:8502)", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔧 Herramientas disponibles")
    st.markdown("- 🔍 **buscador_normativo** \u2014 consultas legales RAG")
    st.markdown("- 📊 **evaluar_cumplimiento** \u2014 auditoría de sistemas")
    st.markdown("- 💾 **guardar_reporte** \u2014 genera informe en disco")
    st.divider()
    st.markdown("**Ejemplos rápidos:**")
    st.markdown("👉 *¿Plazo para reportar filtración?*")
    st.markdown("👉 *Evalúa si logs sin cifrado cumplen Ley 21.663*")
    st.markdown("👉 *Genera reporte sobre obligaciones CISO*")

rag_chain, eval_chain, llm = load_components()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import random
    st.session_state.session_id = generar_session_id(str(random.random()))

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

if user_input := st.chat_input("¿Cuál es el plazo para reportar una filtración de datos?"):
    permitido, msg_limite = verificar_rate_limit(st.session_state.session_id)
    if not permitido:
        st.warning(msg_limite)
        st.stop()

    query_limpia, alertas = sanitizar_input(user_input)
    for alerta in alertas:
        st.warning(f"⚠️ Seguridad: {alerta}")

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").markdown(user_input)

    herramienta = detectar_herramienta(query_limpia)

    with st.spinner(f"Procesando con **{herramienta}**..."):
        inicio = time.time()
        error_msg = None
        respuesta = ""

        try:
            if herramienta == "evaluar_cumplimiento":
                respuesta = eval_chain.invoke({"descripcion": query_limpia})

            elif herramienta == "guardar_reporte":
                contenido_reporte = rag_chain.invoke(query_limpia)
                nombre = f"reporte_{int(time.time())}"
                msg_guardado = guardar_reporte_txt(nombre, contenido_reporte)
                respuesta = f"{contenido_reporte}\n\n---\n{msg_guardado}"

            else:  # buscador_normativo
                respuesta = rag_chain.invoke(query_limpia)

        except Exception as e:
            error_msg = str(e)
            respuesta = f"Error procesando la consulta: {e}"

        latencia = round(time.time() - inicio, 3)

    registrar_metricas(
        query=query_limpia,
        respuesta=respuesta,
        latencia=latencia,
        herramienta_usada=herramienta,
        error=error_msg,
    )

    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    st.chat_message("assistant").markdown(respuesta)

    with st.sidebar:
        st.metric("⏱️ Latencia última consulta", f"{latencia}s")
        st.info(f"🔧 Herramienta: `{herramienta}`")
        if error_msg:
            st.error(f"Error: {error_msg}")
