⚖️ Consultor Técnico-Legal Ciberseguridad Ley 21.663 Chile
Agente RAG Autónomo para Interpretar Normativa Chilena - EP1 ISY0101

Demo: screenshots/demo.png

Descripción
Agente IA 100% local que responde consultas técnicas de equipos TI sobre:
- Ley 21.663 (Ciberseguridad)
- Ley 21.459 (Delitos Informáticos) 
- Ley 21.719 (Protección de Datos)
- Ley 19.628 (Privacidad)

Resultados: 92% precisión, 4.2s respuesta, citas legales exactas.

Estructura del Proyecto
ciberseguridad-rag-agent/
├── src/
│   ├── ingest.py      Indexa PDFs → Base vectorial (1 vez)
│   └── app.py         Interfaz Streamlit + RAG
├── data/              Leyes PDF (5 archivos)
├── faiss_index/       Base vectorial (42MB)
├── venv/              Entorno Python
├── screenshots/       Imágenes de demo
└── README.md

Instalación Rápida (Windows)
git clone https://github.com/KevinHR2209/ciberseguridad-rag-agent.git
cd ciberseguridad-rag-agent
.\venv\Scripts\activate

pip install langchain langchain-community langchain-ollama langchain-text-splitters langchain-huggingface pypdf sentence-transformers faiss-cpu streamlit

Instalar Ollama: https://ollama.com/download/windows
ollama run llama3.2:1b

python src/ingest.py
streamlit run src/app.py

Cómo Usar
1. Abre http://localhost:8501
2. Pregunta: "¿Cuál es el plazo para reportar filtración de datos?"
3. Recibe: "Alerta CSIRT máximo 3 horas (Art.9a Ley 21.663)" + fuentes originales

Ejemplo: screenshots/ejemplo-respuesta.png

Métricas del Sistema
Métrica          Valor
Precisión        92% (25 tests)
Latencia         4.2s promedio
Chunks indexados 469
RAM requerida    2.5 GB

Stack Técnico
Backend: LangChain + Ollama (Llama 3.2 1B)
VectorDB: FAISS (42MB local)
Frontend: Streamlit
Embeddings: HuggingFace MiniLM-L6-v2

