# Cómo contribuir a RXON

[EN](https://github.com/madgagarin/rxon/blob/main/CONTRIBUTING.md) | **ES** | [RU](https://github.com/madgagarin/rxon/blob/main/docs/ru/CONTRIBUTING.md)

Al ser la capa de protocolo compartida, los cambios aquí afectan a todo el ecosistema. Por favor, sea extra cuidadoso.

## Configuración

1.  Clone el repositorio y navegue a este directorio.
2.  Instale en modo editable:
    ```bash
    pip install -e .[dev]
    ```

## Pruebas

Ejecute las pruebas para asegurar la integridad del protocolo:

```bash
pytest tests/
```

## Guías

- **Cambios Críticos**: Cualquier cambio en `rxon.models` es potencialmente un cambio crítico. Consulte con los mantenedores antes de enviarlo.
- **Dependencias**: Mantenga el núcleo libre de dependencias. El código de red debe ir en `rxon.transports`.
- **Tipado**: El tipado estático es estrictamente requerido para todos los modelos del protocolo.
