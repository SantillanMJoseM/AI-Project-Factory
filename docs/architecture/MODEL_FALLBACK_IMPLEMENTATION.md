# MODEL FALLBACK MANAGER — IMPLEMENTACIÓN

## Estado

Implementado en rama `feature/model-fallback-manager`. Todas las pruebas unitarias (19) e integración (7) pasan.

## Archivos

| Archivo | Propósito |
|---|---|
| `orchestration/runtime/model_hierarchies.py` | Jerarquías ordenadas de modelos por agente |
| `orchestration/runtime/model_fallback.py` | `ModelFallbackManager`, clasificación de errores, selección, esperas, recuperación |
| `orchestration/runtime/opencode_adapter.py` | Integración: `invoke` usa manager cuando `model=None` |
| `orchestration/runtime/runtime.py` | Tabla `model_fallback_log`, funciones `save_fallback_log`/`get_fallback_log`, integración en `run_task` |
| `schemas/model-fallback.schema.json` | Schema JSON del log |
| `contracts/model-fallback-contract.md` | Contrato normativo |
| `docs/architecture/MODEL_FALLBACK_DESIGN.md` | Diseño técnico |
| `tests/orchestration/test_model_fallback.py` | 19 pruebas unitarias |
| `tests/orchestration/test_model_fallback_integration.py` | 7 pruebas de integración (mocks) |

## Uso

### Ejecución normal (con fallback automático)

```python
from orchestration.runtime.opencode_adapter import OpenCodeAdapter
adapter = OpenCodeAdapter()
result = adapter.invoke("ag-001-project-coordinator", "prompt", task_id="t1")
# El manager selecciona el modelo principal; si falla por cuota, usa alternativa.
```

### Modelo explícito (sin fallback)

```python
result = adapter.invoke("ag-001-project-coordinator", "prompt", model="opencode-go/qwen3.8-flash")
```

### Consultar log

```python
from orchestration.runtime.runtime import get_conn, get_fallback_log
conn = get_conn()
logs = get_fallback_log(conn, task_id="t1")
```

## Matriz de modelos por agente

| Agente | Principal | Alternativa 1 | Alternativa 2 | Alternativa 3 |
|---|---|---|---|---|
| AG-001 | qwen4-max | qwen3.8-max | kimi-k3.1-pro | glm-5.3 |
| AG-002 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |
| AG-003 | qwen4-max | qwen3.8-max | kimi-k3.1-pro | glm-5.3 |
| AG-004 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |
| AG-005 | qwen4-max | qwen3.8-max | kimi-k3.1-pro | glm-5.3 |
| AG-006 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |
| AG-007 | kimi-k2.7-code | kimi-k3.1-pro | qwen3.8-max | glm-5.3 |
| AG-008 | kimi-k2.7-code | kimi-k3.1-pro | qwen3.8-max | glm-5.3 |
| AG-009 | kimi-k2.7-code | kimi-k3.1-pro | qwen3.8-max | glm-5.3 |
| AG-010 | kimi-k2.7-code | kimi-k3.1-pro | qwen3.8-max | glm-5.3 |
| AG-011 | kimi-k2.7-code | kimi-k3.1-pro | qwen3.8-max | glm-5.3 |
| AG-012 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |
| AG-013 | qwen4-max | qwen3.8-max | kimi-k3.1-pro | glm-5.3 |
| AG-014 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |
| AG-015 | qwen4-max | qwen3.8-max | kimi-k3.1-pro | glm-5.3 |
| AG-016 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |
| AG-017 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |
| AG-018 | qwen3.8-flash | qwen3.8-max | glm-5.3-flash | mimo-v2.6-flash |

Todos los modelos pertenecen a `opencode-go` (OpenCode Go). No se utilizan proveedores externos ni modelos de pago adicional.

## Clasificación de errores

| Tipo | Acción |
|---|---|
| Cuota agotada | Marcar no disponible, seleccionar alternativa |
| Límite temporal | Esperar Retry-After, reintentar mismo modelo |
| Transitorio | Backoff exponencial, reintentar mismo modelo |
| Autenticación | NEEDS_INTERVENTION, no cambiar |
| Ambiguo | Registrar, no cambiar |

## Estados

RUNNING, WAITING_RATE_LIMIT, WAITING_QUOTA_RESET, FALLBACK_ACTIVE, COMPLETED, FAILED, NEEDS_INTERVENTION.

## Pruebas

```bash
python3 -m unittest tests.orchestration.test_model_fallback -v
python3 -m unittest tests.orchestration.test_model_fallback_integration -v
```

## Limitaciones conocidas

- La espera real (`time.sleep`) está capeada a 5s en el adapter para responsiveness; el orquestador debe manejar esperas largas mediante cola de pendientes.
- La recuperación del modelo principal se detecta por timestamp; no hay consulta activa al proveedor de cuotas (no disponible vía API).
- Las alternativas están hardcodeadas en `model_hierarchies.py`; deben actualizarse si el catálogo de OpenCode Go cambia.
