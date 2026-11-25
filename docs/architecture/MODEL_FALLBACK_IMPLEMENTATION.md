# MODEL FALLBACK MANAGER — IMPLEMENTACIÓN (BEAM_FREE_ONLY)

## Estado

Implementado en rama `feature/model-fallback-manager` y consolidado en `main`.
Política BEAM_FREE_ONLY vigente (ADR-007). Un solo modelo autorizado:
`opencode-go/beam-free`. No hay alternativas.

## Archivos

| Archivo | Propósito |
|---|---|
| `orchestration/runtime/model_hierarchies.py` | Define `AUTHORIZED_MODEL`, `AUTHORIZED_MODELS`, `FALLBACK_ALTERNATIVES = {}`, `PROVIDER` |
| `orchestration/runtime/model_fallback.py` | `ModelFallbackManager`: disponibilidad, clasificación, espera, recuperación, logging, guardas de política |
| `orchestration/runtime/opencode_adapter.py` | Integración: `invoke` usa el manager; rechaza modelos no autorizados |
| `orchestration/runtime/runtime.py` | Tabla `model_fallback_log`, funciones `save_fallback_log`/`get_fallback_log`, integración en `run_task`/`run_workflow` |
| `schemas/model-fallback.schema.json` | Schema JSON del log |
| `contracts/model-fallback-contract.md` | Contrato normativo (heredado; describe jerarquías históricas) |
| `docs/architecture/MODEL_FALLBACK_DESIGN.md` | Diseño técnico (BEAM_FREE_ONLY) |
| `docs/architecture/MODEL_FALLBACK_VALIDATION.md` | Validación (actualizada) |
| `tests/orchestration/test_model_fallback.py` | 19 pruebas unitarias (aserciones heredadas del diseño multi-modelo) |
| `tests/orchestration/test_model_fallback_integration.py` | 7 pruebas de integración (mocks) |

## Uso

### Ejecución normal (modelo único)

```python
from orchestration.runtime.opencode_adapter import OpenCodeAdapter
adapter = OpenCodeAdapter()
result = adapter.invoke("ag-001-project-coordinator", "prompt", task_id="t1")
# El único modelo usado es opencode-go/beam-free.
```

### Modelo explícito (debe ser el autorizado)

```python
result = adapter.invoke("ag-001-project-coordinator", "prompt", model="opencode-go/beam-free")
# Cualquier otro modelo se rechaza (policy violation: BEAM_FREE_ONLY).
```

### Consultar log

```python
from orchestration.runtime.runtime import get_conn, get_fallback_log
conn = get_conn()
logs = get_fallback_log(conn, task_id="t1")
```

## Matriz de modelos por agente

Todos los agentes usan el mismo modelo autorizado. No hay alternativas.

| Agente | Modelo |
|---|---|
| AG-001..AG-018 | `opencode-go/beam-free` |

Todos los modelos pertenecen a `opencode-go` (OpenCode Go). No se utilizan proveedores
externos ni modelos de pago adicional.

## Clasificación de errores

| Tipo | Acción |
|---|---|
| Cuota agotada | Marcar no disponible, esperar recuperación (sin cambio de modelo) |
| Límite temporal | Esperar Retry-After, reintentar mismo modelo |
| Transitorio | Reintentar mismo modelo |
| Autenticación | `NEEDS_INTERVENTION`, sin cambio |
| Ambiguo | Registrar, abortar, sin cambio |

## Estados

RUNNING, WAITING_RATE_LIMIT, WAITING_QUOTA_RESET, FALLBACK_ACTIVE, COMPLETED, FAILED,
NEEDS_INTERVENTION.

## Modelos disponibles

El catálogo de modelos disponibles se obtiene del proveedor mediante `opencode models`.
El factory no incrusta una lista de modelos alternativos.

## Pruebas

Pruebas de fallback no forman parte de `tests/run_all.py`. La política se verifica por
inspección de código y por las pruebas de estructura/coordinación incluidas en la suite
principal:

```bash
python3 tests/run_all.py
python3 tests/orchestration/test_structure.py
```

## Limitaciones conocidas

- La espera real (`time.sleep`) está capeada a 5s en el adapter para responsiveness;
  el orquestador debe manejar esperas largas mediante cola de pendientes.
- La recuperación del modelo autorizado se detecta por timestamp; no hay consulta activa
  al proveedor de cuotas (no disponible vía API).
- No hay cambio de modelo en ningún escenario.
- Las pruebas unitarias/integración de fallback contienen aserciones heredadas del diseño
  multi-modelo anterior y no se modificaron en esta tarea.
- El escape hatch (modelos alternativos) requiere autorización explícita y no está
  implementado.