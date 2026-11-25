# MODEL FALLBACK MANAGER — VALIDACIÓN (BEAM_FREE_ONLY)

## Fecha

2026-11-23 (reconciliación de documentación, RECON-018-DOCS-003).

## Rama

`main` (consolidado desde `feature/model-fallback-manager`).

## Política

BEAM_FREE_ONLY (`opencode-go/beam-free`). Un solo modelo autorizado; sin alternativas;
sin cambio de modelo en ningún escenario.

## Pruebas ejecutadas (suite principal)

```
python3 tests/run_all.py
ALL TESTS PASSED
```

31 suites incluidas en `tests/run_all.py`. Adicionalmente:

```
python3 tests/orchestration/test_structure.py
PASS (8 tests)
```

## Escenarios bajo política actual

| # | Escenario | Resultado esperado |
|---|---|---|
| 1 | Ejecución normal | `opencode-go/beam-free` |
| 2 | Cuota agotada del modelo autorizado | Marcar no disponible, `WAITING_QUOTA_RESET`, sin cambio de modelo |
| 3 | Límite temporal por hora | Esperar `Retry-After`, reintentar mismo modelo |
| 4 | Error transitorio de red | Reintentar mismo modelo |
| 5 | Error de autenticación | `NEEDS_INTERVENTION`, sin cambio |
| 6 | Error ambiguo | Abortar, sin cambio |
| 7 | Recuperación por timestamp | `recover_primary` devuelve disponibilidad |
| 8 | Modelo explícito no autorizado | Rechazado (policy violation) |

## Compatibilidad

- Los 18 agentes mantienen sus responsabilidades normativas.
- `OpenCodeAdapter` mantiene compatibilidad con `model="opencode-go/beam-free"`.
- `run_task`/`run_workflow` rechazan modelos no autorizados.
- Tabla `model_fallback_log` añadida sin modificar tablas existentes.

## Restricciones económicas

- El único modelo es `opencode-go/beam-free`.
- No se utilizan proveedores externos, modelos de pago ni Extra Usage.
- Las pruebas de fallback usan mocks; no consumen cuota real.

## Pruebas de fallback (heredadas)

`tests/orchestration/test_model_fallback.py` y
`tests/orchestration/test_model_fallback_integration.py` contienen aserciones del diseño
multi-modelo anterior a BEAM_FREE_ONLY. No forman parte de `tests/run_all.py` y no se
modificaron en esta tarea. Su actualización requiere autorización y está fuera del alcance
de RECON-018-DOCS-003.

## Estado

Documentación reconciliada con la implementación BEAM_FREE_ONLY. No se modificó código ni
pruebas. No se realizaron commits, merges, releases ni despliegues.