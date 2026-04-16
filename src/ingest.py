import os
import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def ingest_leyes():
    print("Iniciando ingesta de documentos legales...")
    pdf_paths = glob.glob("data/*.pdf")
    
    if not pdf_paths:
        print("❌ Error: No se encontraron archivos PDF en la carpeta 'data/'. Por favor, agrega al menos uno.")
        return

    documentos_procesados = []
    
    # Splitter especializado
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\nArtículo", "\nArt.", "\nN°", "\n", " ", ""]
    )

    for ruta in pdf_paths:
        print(f"Procesando: {ruta}")
        cargador = PyPDFLoader(ruta)
        paginas = cargador.load()
        fragmentos = divisor.split_documents(paginas)
        
        nombre_archivo = os.path.basename(ruta)
        for fragmento in fragmentos:
            fragmento.metadata.update({"archivo_origen": nombre_archivo})
            
        documentos_procesados.extend(fragmentos)

    print(f"Total de chunks generados: {len(documentos_procesados)}")
    
    print("Generando embeddings y creando base vectorial FAISS...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    vectorstore = FAISS.from_documents(documentos_procesados, embeddings)
    vectorstore.save_local("faiss_index")
    print("✅ Índice FAISS guardado exitosamente en la carpeta 'faiss_index'")

if __name__ == "__main__":
    ingest_leyes()