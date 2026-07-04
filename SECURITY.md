# SECURITY.md

**EN** | [ES](https://github.com/madgagarin/rxon/blob/main/docs/es/SECURITY.md) | [RU](https://github.com/madgagarin/rxon/blob/main/docs/ru/SECURITY.md)

## Reporting a Vulnerability

Please report any vulnerabilities in the RXON protocol library to [madgagarin@gmail.com].

## Core Principles

RXON is designed to be the secure "nerve system" of the Hierarchical Logic Network (HLN). It enforces:

### 🔐 Digital Signatures and HMAC

The protocol supports message signing via HMAC-SHA256 (symmetric) and Ed25519 (asymmetric digital signatures) (the `security.signature` field). This ensures:

- **Integrity**: Messages cannot be altered in transit.
- **Authenticity**: Only a worker with the secret token can send data.
- **Stable Serialization**: The **JSON Round-trip** mechanism ensures that the same data always produces the same byte sequence for signature verification.

### ⏱️ Replay Protection

Every signed message must include an integer `timestamp`. The Orchestrator rejects messages that:

- Are older than 60 seconds (default).
- Contain a time from the future.
- Re-use an already processed `event_id` or `task_id` within the validity window.

### 🛡️ Zero Trust Identity Chain

Every event emitted from a subordinate node includes an `origin_worker_id` and a `bubbling_chain`. This prevents spoofing and allows the Orchestrator to audit the entire path of a signal through the holarchy. The HMAC signature covers the entire message, including the chain, making identity spoofing mathematically impossible without the secret key.

### 📝 Formal Interface Contracts

All communication (Registration, Heartbeats, Skills) is strictly validated against JSON Schemas. This prevents injection attacks and ensures that malformed data is rejected before it reaches the execution engine.

### 🧬 Reverse Connection (Axon Flow)

Initiative always comes from the subordinate node (Worker/Shell). This eliminates the need for open incoming ports on workers, making them invisible to external network scans and direct attacks.

### ⏳ Task Ownership & Deadlines

Results are only accepted from the worker currently assigned to the task. Built-in `deadline` fields prevent the processing of stale tasks and mitigate certain types of replay or delay attacks.

### 📊 Resource-Aware Telemetry

Granular resource reporting in Heartbeats allows Orchestrators to detect and mitigate resource exhaustion (DoS) before it causes a system-wide failure.
