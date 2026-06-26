import logging
import json
import os
from datetime import datetime

LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "agent_runs.log")

os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, "system.log"), encoding="utf-8"),
    ],
)
system_logger = logging.getLogger("agent_system")


def _anonimizar(texto: str) -> str:
    """
    Anonimiza RUTs chilenos y emails antes de guardar en log.
    """
    import re
    texto = re.sub(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b', '[RUT-ANONIMIZADO]', texto)
    texto = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[EMAIL-ANONIMIZADO]', texto)
    return texto


def log_event(query: str, respuesta: str, latencia: float, precision: float,
              herramienta: str, cpu_percent: float, ram_mb: float,
              error: str = None):
    """
    Guarda un evento de ejecución del agente en formato JSON estructurado.
    """
    evento = {
        "timestamp": datetime.now().isoformat(),
        "query": _anonimizar(query),
        "herramienta": herramienta,
        "latencia_s": latencia,
        "precision_score": precision,
        "cpu_percent": cpu_percent,
        "ram_mb": ram_mb,
        "tokens_estimados": len(respuesta.split()),
        "error": error,
        "respuesta_snippet": _anonimizar(respuesta[:150]),
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")

    if error:
        system_logger.error(f"Error en consulta | query='{query[:60]}' | error='{error}'")
    else:
        system_logger.info(f"Consulta OK | latencia={latencia}s | precision={precision} | tool={herramienta}")


def leer_logs() -> list:
    """
    Lee todos los eventos del log y los retorna como lista de dicts.
    """
    if not os.path.exists(LOG_FILE):
        return []
    eventos = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                try:
                    eventos.append(json.loads(linea))
                except json.JSONDecodeError:
                    pass
    return eventos
