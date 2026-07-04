# CONTRIBUTING.md

**EN** | [ES](https://github.com/madgagarin/rxon/blob/main/docs/es/CONTRIBUTING.md) | [RU](https://github.com/madgagarin/rxon/blob/main/docs/ru/CONTRIBUTING.md)

As the shared protocol layer, changes here affect the entire ecosystem. Please be extra careful.

## Setup

1.  Clone the repository and navigate to this directory.
2.  Install in editable mode:
    ```bash
    pip install -e .[dev]
    ```

## Testing

Run tests to ensure protocol integrity:

```bash
pytest tests/
```

## Guidelines

- **Breaking Changes**: Any change to `rxon.models` is potentially a breaking change. Consult with the maintainers before submitting.
- **Dependencies**: Keep the core dependency-free. Network-heavy code should go into `rxon.transports`.
- **Typing**: Static typing is strictly required for all protocol models.
