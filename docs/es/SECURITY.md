# Política de Seguridad de RXON

[EN](https://github.com/madgagarin/rxon/blob/main/SECURITY.md) | **ES** | [RU](https://github.com/madgagarin/rxon/blob/main/docs/ru/SECURITY.md)

## Reportar una Vulnerabilidad

Por favor, reporte cualquier vulnerabilidad en la biblioteca del protocolo RXON a [madgagarin@gmail.com].

## Principios Fundamentales

RXON está diseñado para ser el "nervio" seguro de la red lógica jerárquica (HLN). Proporciona:

### 🔐 Firmas Digitales y HMAC

El protocolo admite la firma de mensajes a través de HMAC-SHA256 (simétrico) y Ed25519 (firmas digitales asimétricas) (campo `security.signature`). Esto garantiza:

- **Integridad**: Los mensajes no pueden ser alterados en tránsito.
- **Autenticidad**: Solo un trabajador con el token secreto puede enviar datos.
- **Serialización Estable**: El mecanismo **JSON Round-trip** asegura que los mismos datos siempre produzcan la misma secuencia de bytes para la verificación de la firma.

### ⏱️ Protección contra Ataques de Repetición (Replay Protection)

Cada mensaje firmado debe incluir una marca de tiempo entera (`timestamp`). El Orquestador rechaza los mensajes que:

- Son más antiguos de 60 segundos (por defecto).
- Contienen una hora del futuro.
- Reutilizan un `event_id` o `task_id` ya procesado dentro de la ventana de validez.

### 🛡️ Cadena de Identidad Zero Trust

Cada evento emitido por un nodo subordinado incluye un `origin_worker_id` и una `bubbling_chain`. Esto previene suplantaciones y permite al Orquestador auditar toda la ruta de una señal a través de la holarquía. La firma HMAC cubre todo el mensaje, incluida la cadena, lo que hace que la suplantación de identidad sea matemáticamente imposible sin la clave secreta.

### 📝 Contratos de Interfaz Formales (Contract Enforcement)

Toda la comunicación (Registro, Heartbeats, Habilidades) es estrictamente validada contra esquemas JSON.

- **Protección contra Inyección**: Esto previene ataques de inyección y asegura que los datos mal formados sean rechazados antes de llegar al motor de ejecución.
- **Protección contra Inyección de Estado**: El uso de `additionalProperties: false` en los esquemas de habilidades garantiza que un trabajador no pueda inyectar campos adicionales en la memoria del orquestador que podrían influir en la lógica de los pasos posteriores del pipeline.

### 🧬 Conexión Inversa (Flujo Axon)

La iniciativa siempre proviene del nodo subordinado (Worker/Shell). Esto elimina la necesidad de abrir puertos de entrada en los trabajadores, haciéndolos invisibles a los escaneos de red externos.

### ⏳ Propiedad de Tareas y Deadlines

Los resultados solo se aceptan del trabajador asignado actualmente a la tarea. Los campos integrados `deadline` previenen el procesamiento de tareas obsoletas y mitigan ataques de retraso o repetición.

### 📊 Telemetría de Recursos

El reporte granular de recursos en los Heartbeats permite a los Orquestadores detectar y mitigar el agotamiento de recursos (DoS) antes de que cause una falla en todo el sistema.
