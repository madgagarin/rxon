# Protocolo RXON (Reverse Axon)

[EN](https://github.com/madgagarin/rxon/blob/main/README.md) | **ES** | [RU](https://github.com/madgagarin/rxon/blob/main/docs/ru/README.md)

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![PyPI version](https://img.shields.io/pypi/v/rxon.svg)](https://pypi.org/project/rxon/)

**RXON** (Reverse Axon) es un protocolo de conexión inversa ligero y extensible diseñado para arquitecturas **[HLN (Hierarchical Logic Network)](https://github.com/avtomatika-ai/hln)**.

Sirve como el "sistema nervioso" para sistemas multi-agente distribuidos, proporcionando una base Zero Trust estrictamente tipificada para la comunicación entre servicios.

## 🚀 Concepto

En las redes tradicionales, los comandos suelen fluir "de arriba hacia abajo" (modelo Push). En **RXON**, la iniciativa de conexión siempre proviene del nodo subordinado (Shell) al nodo superior (Orchestrator). Esta arquitectura de "Axón Inverso" permite que los trabajadores operen detrás de NAT o Firewalls sin una configuración de red compleja, manteniendo un canal de control bidireccional seguro.

## ✨ Características Principales

- **Conexión Inversa (PULL)**: Los nodos se conectan al orquestador para obtener tareas, asegurando la compatibilidad con entornos de red complejos (NAT/Firewalls).
- **Seguridad Zero Trust**: Firma de carga útil a través de HMAC-SHA256 (simétrico) y Ed25519 (firmas digitales asimétricas) con verificación en tiempo constante. Soporte para bubbling chains firmadas, extracción de identidad de certificados mTLS y verificación de firma digital de tareas `sig` (`orchestrator_signature`).
- **Encabezados de Políticas y Costos**: Soporte integrado para restricciones de políticas de trabajo (`policy`), seguimiento de profundidad de holarquía (`depth`), contadores de pasos de transición (`step`), vinculación de hash primario (`parent_hash`) e informes de costos de ejecución de tareas (`costs`).
- **Restauración Profunda de Modelos**: Utilidad `from_dict` robusta potenciada por `msgspec.convert` que restaura recursivamente tipos complejos de Python (`msgspec.Struct`, `Enum`, `UUID`, `datetime`) a partir de diccionarios, soportando estructuras anidadas y tipos `Union`.
- **Serialización Segura**: Utilidad `to_dict` que elimina recursivamente los valores `None` para reducir el tamaño y normaliza los valores `float` (ej. `1.0` -> `1`), asegurando la estabilidad de los hashes criptográficos.
- **Validación Automatizada de Contratos**: Motor JSON Schema integrado que infiere automáticamente los esquemas a partir de los tipos de Python y valida los parámetros de `TaskPayload` contra los contratos de `SkillInfo`.
- **Coincidencia de Recursos Avanzada**: Lógica matemática para la asignación de recursos:
  - **Números**: Utiliza la lógica **GE (Greater or Equal)** (Requisito <= Disponible).
  - **Listas**: Utiliza la lógica de **Inclusión** (valor en la lista) o **Intersección** (cualquier elemento común).
  - **Cadenas**: Coincidencia parcial de modelos de hardware sin distinción de mayúsculas y minúsculas.
- **Telemetría Universal**: Los heartbeats incluyen métricas detalladas para cualquier dispositivo personalizado (sensores, GPUs, actuadores) y propiedades del sistema genéricas a través del modelo extensible `HardwareDevice`.
- **Transporte Resiliente**: Implementación HTTP/WebSocket con Secure Token Service (STS) que soporta **Refresh Tokens**, backoff exponencial para reconexiones y manejo nativo de **Rate Limit (HTTP 429)** con soporte para `Retry-After`.

## 🏗 Arquitectura y Lógica

### Validación y Normalización Interna

La biblioteca garantiza la integridad de los datos en varios niveles:

1.  **Estabilidad de Serialización**: RXON utiliza un mecanismo de **JSON Round-trip** con `orjson` para normalizar todos los tipos numéricos (`10.0` -> `10`), forzar las claves de los diccionarios a cadenas y ordenar las claves. Esto asegura que el mismo objeto siempre produzca exactamente el mismo hash HMAC independientemente de pequeñas diferencias de formato.
2.  **Soporte Completo de Tipos**: El soporte nativo para `datetime`, `UUID`, `Enum` y modelos **Pydantic** asegura una integración fluida con los ecosistemas modernos de Python manteniendo la consistencia criptográfica.
3.  **Protección de Recurrencia**: Todas las operaciones recursivas están limitadas a una profundidad de 100 para evitar el desbordamiento de pila o ataques DoS a través de datos maliciosos.
4.  **Cumplimiento de Esquemas**: Antes de la ejecución de la tarea, la biblioteca valida los parámetros de entrada contra el JSON Schema de la habilidad, verificando los campos obligatorios, la corrección de tipos y los valores permitidos (Enums).

### Lógica de Coincidencia Inteligente (Smart Matching)

RXON formaliza las reglas para emparejar tareas con holones:

1.  **Coincidencia de Hardware**: Compara las propiedades de `HardwareDevice`. Si una tarea requiere `vram_gb: 16`, coincidirá con cualquier dispositivo con `vram_gb >= 16`.
2.  **Propiedades de Recursos**: Los recursos genéricos (como la RAM o los núcleos de CPU) se comparan a través del diccionario `properties` utilizando la misma lógica GE.
3.  **Intersección de Capacidades**: Si una tarea acepta múltiples entornos (ej. `["linux", "darwin"]`), un trabajador con `linux` coincidirá correctamente.

### Seguimiento de Políticas, Holarquía y Costos

RXON estandariza la gobernanza de ejecución y el seguimiento de métricas en holones distribuidos:

- **Restricciones de Política (`policy`)**: Diccionario que contiene reglas de ejecución (habilidades permitidas, límites de tokens, presupuesto).
- **Contadores de Holarquía y Pasos (`depth`, `step`, `parent_hash`)**: Seguimiento de la profundidad de anidamiento (`depth`), índice de paso de transición (`step`) y enlace criptográfico con el evento primario (`parent_hash`).
- **Firma de Tarea (`sig`)**: Firma criptográfica de la tarea proveniente del orquestador.
- **Informe de Costos (`costs`)**: Campo `TaskResult.costs` para reportar métricas de recursos consumidos (tokens, costo en USD, tiempo de CPU/GPU, por ejemplo `{"tokens": 1500, "usd": 0.02}`).

## 🛡️ Manejo de Errores

RXON define un conjunto de códigos de error estandarizados para asegurar un comportamiento consistente:

- `CONTRACT_VIOLATION_ERROR`: Los datos no coinciden con el esquema negociado.
- `SECURITY_ERROR`: Error de autenticación o verificación de firma.
- `RESOURCE_EXHAUSTED_ERROR`: Recursos físicos insuficientes (RAM, VRAM).
- `DEPENDENCY_ERROR`: Un servicio o artefacto requerido no está disponible.

## 🧪 Inicio Rápido

### Lado del Trabajador (PULL)

```python
from rxon import create_transport
from rxon.models import Resources, HardwareDevice

# 1. Crear transporte (soporta http, https, ws, wss)
transport = create_transport("ws://api.hln.local", "worker-01", "secret-token")

# 2. Definir recursos del trabajador
my_res = Resources(
    properties={"ram_gb": 64, "cpu_cores": 16},
    devices=[HardwareDevice(type="gpu", model="RTX 4090", properties={"vram_gb": 24})]
)

# 3. Lógica de coincidencia (Requisito: GPU con al menos 16GB VRAM)
req = Resources(devices=[HardwareDevice(type="gpu", properties={"vram_gb": 16})])
if my_res.matches(req):
    print("¡Este holón está listo para la tarea!")
```

### Lado del Orquestador (Servidor)

```python
from aiohttp import web
from rxon import HttpListener

app = web.Application()
listener = HttpListener(app)

# OBLIGATORIO: Registrar rutas RXON antes del inicio de la aplicación
listener.setup_routes()

async def my_handler(action, payload, context):
    if action == "poll":
        return {"job_id": "j-1", "task_id": "t-1", "type": "echo"}
    return {"status": "ok"}

# Iniciar escucha
await listener.start(handler=my_handler)
```

## 📜 Licencia

El proyecto se distribuye bajo la licencia Mozilla Public License 2.0 (MPL 2.0).

---

_Mantra: "The RXON is the medium for the Ghost."_
