import streamlit as st
import os
import time
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import Tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain import hub

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

    # ── HERRAMIENTA 1: Consulta normativa (RAG) ─────────────────────────────
    rag_template = """CONTEXTO LEGAL AUTORIZADO:\n{context}\n\nCONSULTA: {question}\n\nResponde nivel ingeniero TI. Cita el Artículo y la Ley. Finaliza con: 'Esta interpretación no sustituye asesoría legal formal.'"""
    rag_prompt = PromptTemplate.from_template(rag_template)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    def buscador_normativo(query: str) -> str:
        return rag_chain.invoke(query)

    # ── HERRAMIENTA 2: Guardar reporte ──────────────────────────────────────
    def guardar_reporte(entrada: str) -> str:
        """Guarda un reporte en /reportes/. Input: 'nombre_archivo|contenido'"""
        if "|" in entrada:
            nombre, contenido = entrada.split("|", 1)
        else:
            nombre = f"reporte_{int(time.time())}"
            contenido = entrada

        valido, nombre_limpio = validar_nombre_archivo(nombre.strip())
        if not valido:
            return f"Error: {nombre_limpio}"
        if not nombre_limpio.endswith(".txt"):
            nombre_limpio += ".txt"

        ruta = os.path.join(REPORTES_DIR, nombre_limpio)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido.strip())
        return f"Reporte guardado exitosamente en '{ruta}'."

    # ── HERRAMIENTA 3: Evaluar cumplimiento ─────────────────────────────────
    def evaluar_cumplimiento(descripcion: str) -> str:
        """Evalúa si un sistema/proceso cumple con la Ley 21.663."""
        prompt_eval = f"""Eres un auditor experto en Ley 21.663 de Ciberseguridad de Chile.

Descripción del sistema o proceso a evaluar:
{descripcion}

Evalúa el cumplimiento y responde EXCLUSIVAMENTE con este formato:
VEREDICTO: [CUMPLE / INCUMPLE / REQUIERE_REVISIÓN]
NIVEL_RIESGO: [ALTO / MEDIO / BAJO]
JUSTIFICACIÓN: [Explicación técnica-legal citando artículos relevantes]
RECOMENDACIONES: [Acciones concretas si aplica]"""
        return llm.invoke(prompt_eval)

    # ── Construcción del agente ReAct ────────────────────────────────────────
    herramientas = [
        Tool(
            name="buscador_normativo",
            func=buscador_normativo,
            description="Busca y responde consultas sobre la Ley 21.663, Ley 21.459, Ley 21.719 y Ley 19.628. Úsala para preguntas sobre artículos, plazos, obligaciones y sanciones.",
        ),
        Tool(
            name="guardar_reporte",
            func=guardar_reporte,
            description="Guarda un reporte técnico en disco. Input: 'nombre_archivo|contenido del reporte'. Úsala cuando el usuario pide generar o guardar un informe.",
        ),
        Tool(
            name="evaluar_cumplimiento",
            func=evaluar_cumplimiento,
            description="Evalúa si un sistema, proceso o configuración cumple con la Ley 21.663. Retorna CUMPLE/INCUMPLE/REQUIERE_REVISIÓN con justificación. Input: descripción del sistema.",
        ),
    ]

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    react_prompt = hub.pull("hwchase17/react-chat")
    agent = create_react_agent(llm=llm, tools=herramientas, prompt=react_prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=herramientas,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )

    return agent_executor, retriever


st.title("⚖️ Consultor Técnico-Legal Ciberseguridad")
st.caption("Agente RAG + 3 herramientas | Ley 21.663 Chile | EP3 ISY0101")

col1, col2 = st.columns([3, 1])
with col2:
    st.markdown("[📊 Ver Dashboard](http://localhost:8502)", unsafe_allow_html=True)

agent_executor, retriever = load_components()

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
    if alertas:
        for alerta in alertas:
            st.warning(f"⚠️ Seguridad: {alerta}")

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").markdown(user_input)

    with st.spinner("Procesando con el agente..."):
        inicio = time.time()
        error_msg = None
        respuesta = ""
        herramienta_usada = "buscador_normativo"

        try:
            resultado = agent_executor.invoke({"input": query_limpia})
            respuesta = resultado.get("output", "Sin respuesta.")
            if "guardar_reporte" in str(resultado):
                herramienta_usada = "guardar_reporte"
            elif "evaluar_cumplimiento" in str(resultado):
                herramienta_usada = "evaluar_cumplimiento"
        except Exception as e:
            error_msg = str(e)
            respuesta = f"Error procesando la consulta: {e}"

        latencia = round(time.time() - inicio, 3)

    registrar_metricas(
        query=query_limpia,
        respuesta=respuesta,
        latencia=latencia,
        herramienta_usada=herramienta_usada,
        error=error_msg,
    )

    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    st.chat_message("assistant").markdown(respuesta)

    with st.sidebar:
        st.metric("⏱️ Latencia última consulta", f"{latencia}s")
        if error_msg:
            st.error(f"Error: {error_msg}")
