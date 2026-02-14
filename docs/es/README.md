# Protocolo RXON (Reverse Axon)

[EN](https://github.com/madgagarin/rxon/blob/main/README.md) | **ES** | [RU](https://github.com/madgagarin/rxon/blob/main/docs/ru/README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Typing: Typed](https://img.shields.io/badge/Typing-Typed-brightgreen.svg)](https://peps.python.org/pep-0561/)

**RXON** (Reverse Axon) es un protocolo de comunicación entre servicios de conexión inversa y ligero, diseñado para la arquitectura **[HLN (Hierarchical Logic Network)](https://github.com/avtomatika-ai/hln)**.

## ✨ Características Principales

-   **Transportes Modulares**: Abstracción total de la capa de red.
-   **Core sin Dependencias**: El núcleo no tiene dependencias externas.
-   **Estrictamente Tipado**: Modelos basados en `NamedTuple` para máximo rendimiento.
-   **Nativo para Blobs**: Soporte integrado para S3 (`rxon.blob`).

## 🛡️ Manejo de Errores

RXON define códigos de error estandarizados para los resultados de las tareas:
-   `TIMEOUT_ERROR`: El trabajador no pudo terminar a tiempo.
-   `LATE_RESULT`: El orquestador rechazó el resultado porque el plazo ha expirado.
-   `STALE_TASK`: El orquestador rechazó el resultado porque la tarea ha sido reasignada.
-   `RESOURCE_EXHAUSTED_ERROR`: Fallo temporal por falta de recursos locales.

## 🧪 Pruebas

La biblioteca incluye un `MockTransport` para simplificar las pruebas de los Workers en aislamiento.

```python
from rxon.testing import MockTransport

# Usar el esquema mock://
transport = create_transport("mock://", "test-worker", "token")
await transport.connect()

# Inyectar tareas directamente
transport.push_task(my_task_payload)
```

## 📜 Licencia

El proyecto se distribuye bajo la Licencia MIT.

---
*Mantra: "The RXON is the medium for the Ghost."*
