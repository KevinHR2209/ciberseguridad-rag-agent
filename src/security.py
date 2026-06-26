import re
import time
import hashlib
from collections import defaultdict

_solicitudes_por_sesion: dict = defaultdict(list)
MAX_SOLICITUDES = 10
VENTANA_SEGUNDOS = 60

PATRONES_INJECTION = [
    r"ignora (todas |las )?instrucciones",
    r"olvida (todo|el contexto)",
    r"actúa como",
    r"eres ahora",
    r"nuevo (rol|sistema|prompt)",
    r"jailbreak",
    r"<\s*script",
    r"\beval\s*\(",
    r"__import__",
    r"os\.system",
]


def verificar_rate_limit(session_id: str) -> tuple:
    """
    Verifica si la sesión ha excedido el límite de solicitudes.
    Retorna (permitido: bool, mensaje: str).
    """
    ahora = time.time()
    historial = _solicitudes_por_sesion[session_id]
    historial[:] = [t for t in historial if ahora - t < VENTANA_SEGUNDOS]

    if len(historial) >= MAX_SOLICITUDES:
        espera = int(VENTANA_SEGUNDOS - (ahora - historial[0]))
        return False, f"Límite de {MAX_SOLICITUDES} consultas/minuto alcanzado. Espera {espera}s."

    historial.append(ahora)
    return True, ""


def sanitizar_input(texto: str) -> tuple:
    """
    Limpia el input del usuario: trunca, detecta injection, elimina caracteres de control.
    Retorna (texto_limpio, lista_alertas).
    """
    alertas = []

    if len(texto) > 1000:
        texto = texto[:1000]
        alertas.append("Input truncado a 1000 caracteres.")

    texto_lower = texto.lower()
    for patron in PATRONES_INJECTION:
        if re.search(patron, texto_lower):
            alertas.append(f"Patrón de inyección detectado: '{patron}'")
            texto = re.sub(patron, "[BLOQUEADO]", texto, flags=re.IGNORECASE)

    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    return texto.strip(), alertas


def generar_session_id(datos_sesion: str) -> str:
    """
    Genera un ID de sesión anonimizado por hash SHA-256.
    """
    return hashlib.sha256(datos_sesion.encode()).hexdigest()[:16]


def validar_nombre_archivo(nombre: str) -> tuple:
    """
    Valida que un nombre de archivo sea seguro (sin path traversal).
    """
    nombre_limpio = re.sub(r'[^\w\-.]', '_', nombre)
    if '..' in nombre_limpio or '/' in nombre_limpio:
        return False, "Nombre de archivo no permitido."
    return True, nombre_limpio
