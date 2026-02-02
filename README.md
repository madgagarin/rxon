# RXON (Reverse Axon) Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Typing: Typed](https://img.shields.io/badge/Typing-Typed-brightgreen.svg)](https://peps.python.org/pep-0561/)

> **[RU](https://github.com/madgagarin/rxon/blob/main/README_RU.md)**

**RXON** (Reverse Axon) is a lightweight reverse-connection inter-service communication protocol designed for the **[HLN (Hierarchical Logic Network)](https://github.com/avtomatika-ai/hln)** architecture.

It serves as the "nervous system" for distributed multi-agent systems, connecting autonomous nodes (Holons) into a single hierarchical network.

## 🧬 The Biological Metaphor

The name **RXON** is derived from the biological term *Axon* (the nerve fiber). In classic networks, commands typically flow "top-down" (Push model). In RXON, the connection initiative always comes from the subordinate node (Worker/Shell) to the superior node (Orchestrator/Ghost). This is a "Reverse Axon" that grows from the bottom up, creating a channel through which commands subsequently descend.

## ✨ Key Features

-   **Pluggable Transports**: Full abstraction from the network layer. The same code can run over HTTP, WebSocket, gRPC, or Tor.
-   **Zero Dependency Core**: The protocol core has no external dependencies (standard transports use `aiohttp` and `orjson`).
-   **Strictly Typed**: All messages (tasks, results, heartbeats) are defined via strictly typed models for maximum performance and correctness.
-   **Blob Storage Native**: Built-in support for offloading heavy data via S3-compatible storage (`rxon.blob`).

## 🏗 Architecture

The protocol is divided into two main interfaces:

1.  **Transport (Worker side)**: Interface for initiating connections, retrieving tasks, and sending results.
2.  **Listener (Orchestrator side)**: Interface for accepting incoming connections and routing messages to the orchestration engine.

### Usage Example (Worker side)

```python
from rxon import create_transport, WorkerRegistration

# 1. Create transport (automatically selects HttpTransport based on URL scheme)
transport = create_transport(
    url="https://orchestrator.local",
    worker_id="gpu-01",
    token="secret-token"
)

await transport.connect()

# 2. Register
await transport.register(reg_payload)

# 3. Poll for tasks
task = await transport.poll_task(timeout=30)
```

### Usage Example (Orchestrator side)

```python
from rxon import HttpListener, TaskPayload

async def my_handler(message_type, payload, context):
    if message_type == "poll":
        # Task dispatch logic
        return TaskPayload(...)
    return True

# Listener attaches to a web application or starts its own server
listener = HttpListener(app)
await listener.start(handler=my_handler)
```

## 🛡️ Error Handling

RXON uses a dedicated exception hierarchy grounded in `RxonError`. Transports raise specific exceptions instead of returning error codes or `None`.

```python
from rxon import create_transport
from rxon.exceptions import RxonNetworkError, RxonAuthError

try:
    await transport.poll_task()
except RxonNetworkError:
    # Handle connection failures (e.g., exponential backoff)
    pass
except RxonAuthError:
    # Handle critical auth failures (e.g., invalid token)
    pass
```

## 🧪 Testing

The library includes a `MockTransport` to simplify testing Workers in isolation without running a real Orchestrator.

```python
from rxon.testing import MockTransport

# Use standard factory with mock:// scheme
transport = create_transport("mock://", "test-worker", "token")
await transport.connect()

# Inject tasks directly
transport.push_task(my_task_payload)
```

## 📦 Package Structure

-   **`rxon.models`**: DTOs for registrations, tasks, heartbeats, and results.
-   **`rxon.constants`**: Standardized error codes (TIMEOUT, RESOURCE_EXHAUSTED, etc.) and API endpoints.
-   **`rxon.transports`**: Abstract base classes and implementations (HTTP, WebSocket).
-   **`rxon.blob`**: Unified interface for blob storage operations (S3 URI parsing, hashing).
-   **`rxon.security`**: Helpers for mTLS and access tokens.

## 🚀 Installation

```bash
pip install rxon
```

For developers (local):
```bash
pip install -e packages/rxon
```

## 📜 License

The project is distributed under the MIT License.

---
*Mantra: "The RXON is the medium for the Ghost."*
