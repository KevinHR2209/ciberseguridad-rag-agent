import streamlit as st
import os
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

st.set_page_config(page_title="Consultor Ciberseguridad Ley 21.663", layout="wide")

@st.cache_resource
def load_rag_pipeline():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    if not os.path.exists("faiss_index"):
        st.error("No se encontró el índice FAISS. Ejecuta 'python src/ingest.py' primero.")
        st.stop()
        
    db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    retriever = db.as_retriever(search_kwargs={"k": 3})
    
    # Usamos el modelo ligero que configuramos antes
    llm = OllamaLLM(model="llama3.2:1b", temperature=0.1)
    
    template = """CONTEXTO LEGAL AUTORIZADO - USAR EXCLUSIVAMENTE ESTE TEXTO:
{context}
    
CONSULTA TÉCNICA DEL USUARIO: {question}
    
INSTRUCCIONES OPERATIVAS:
1. Responde a nivel ingeniero TI basándote SOLO en el contexto.
2. Cita siempre el Artículo y la Ley al final de la respuesta.
3. Finaliza con: "Esta interpretación no sustituye asesoría legal formal."
"""
    
    prompt = PromptTemplate.from_template(template)
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Cadena RAG Moderna (LCEL) - ¡Reemplaza a RetrievalQA!
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain, retriever

st.title("⚖️ Consultor Técnico-Legal Ciberseguridad")
st.caption("Asistente RAG local basado en la Ley 21.663 de Chile")

rag_chain, retriever = load_rag_pipeline()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

if prompt := st.chat_input("Ej: ¿Cuál es el plazo para reportar una filtración de datos?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)
    
    with st.spinner("Buscando en la normativa..."):
        try:
            # Ejecutamos la búsqueda de documentos y la respuesta por separado
            fuentes = retriever.invoke(prompt)
            respuesta = rag_chain.invoke(prompt)
            
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
            st.chat_message("assistant").markdown(respuesta)
            
            with st.expander("Ver artículos fuente extraídos"):
                for idx, doc in enumerate(fuentes):
                    st.markdown(f"**Fuente {idx+1}:** {doc.metadata.get('archivo_origen', 'Desconocido')}")
                    st.info(doc.page_content)
        except Exception as e:
            st.error(f"Error procesando la consulta: {e}")