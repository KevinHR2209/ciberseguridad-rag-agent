import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import psutil
from src.logger import log_event


def medir_latencia(func, *args, **kwargs):
    inicio = time.time()
    resultado = func(*args, **kwargs)
    latencia = round(time.time() - inicio, 3)
    return resultado, latencia


def medir_recursos():
    proceso = psutil.Process(os.getpid())
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_mb": round(proceso.memory_info().rss / 1024 / 1024, 2),
        "ram_percent": round(proceso.memory_percent(), 2),
    }


def evaluar_precision(respuesta: str, query: str) -> float:
    score = 0.0
    respuesta_lower = respuesta.lower()
    if any(kw in respuesta_lower for kw in ["artículo", "art.", "ley", "n°"]):
        score += 0.5
    if "interpretación no sustituye" in respuesta_lower or "asesoría legal" in respuesta_lower:
        score += 0.2
    if len(respuesta.split()) > 30:
        score += 0.2
    if query.lower() in respuesta_lower[:200]:
        score += 0.1
    return round(min(score, 1.0), 2)


def evaluar_consistencia(respuestas: list) -> float:
    if len(respuestas) < 2:
        return 1.0
    sets_palabras = [set(r.lower().split()) for r in respuestas]
    interseccion = sets_palabras[0].intersection(*sets_palabras[1:])
    union = sets_palabras[0].union(*sets_palabras[1:])
    if not union:
        return 0.0
    return round(len(interseccion) / len(union), 2)


def registrar_metricas(query: str, respuesta: str, latencia: float,
                       herramienta_usada: str = "buscador_normativo",
                       error: str = None):
    recursos = medir_recursos()
    precision = evaluar_precision(respuesta, query) if not error else 0.0
    log_event(
        query=query,
        respuesta=respuesta[:300],
        latencia=latencia,
        precision=precision,
        herramienta=herramienta_usada,
        cpu_percent=recursos["cpu_percent"],
        ram_mb=recursos["ram_mb"],
        error=error,
    )
