# MODEL FALLBACK MANAGER — DISEÑO TÉCNICO (BEAM_FREE_ONLY)

## 1. Objetivo

Gestionar la disponibilidad del único modelo autorizado (`opencode-go/beam-free`) para los
18 agentes AG-001..AG-018, integrado con `OpenCodeAdapter` y la orquestación existente,
sin cambiar de modelo en ningún caso.

## 2. Política (ADR-007)

- Todos los agentes, sesiones, workflows y subprocesos usan exclusivamente
  `opencode-go/beam-free`.
- No existen modelos alternativos ni proveedores externos.
- La continuidad nunca justifica costos adicionales ni cambio de modelo.
- `FALLBACK_ALTERNATIVES` está vacío; `AUTHORIZED_MODELS = {opencode-go/beam-free}`.

## 3. Componentes

### 3.1 ModelFallbackManager

Clase en `orchestration/runtime/model_fallback.py`.

Responsabilidades:
- Mantener la disponibilidad del modelo autorizado (marcado no disponible por tiempo).
- Clasificar errores (cuota agotada, límite temporal, transitorio, autenticación, ambiguo).
- Administrar esperas (Retry-After, backoff implícito por clasificación).
- Recuperar el modelo autorizado cuando vuelva a estar disponible (por timestamp).
- Registrar cada evento en un historial auditable (`model_fallback_log`).
- Rechazar cualquier modelo no autorizado.

### 3.2 Integración con OpenCodeAdapter

`OpenCodeAdapter.invoke` delega la selección de modelo al `ModelFallbackManager`:
- El único modelo seleccionable es `opencode-go/beam-free` si está disponible.
- Si no está disponible, `select_model` devuelve `None` (sin alternativa).
- Si la invocación falla por cuota agotada, se marca no disponible y se espera
  recuperación (no se cambia de modelo).
- Si falla por límite temporal, se espera `Retry-After` y se reintenta el mismo modelo.
- Si falla por error transitorio, se reintenta el mismo modelo.
- Si falla por autenticación/configuración, se registra y devuelve `NEEDS_INTERVENTION`.
- Si falla por error ambiguo, se registra y se aborta.

### 3.3 Persistencia

Tabla `model_fallback_log` en `runtime.db` (sin cambios de esquema en esta fase):
- `log_id` (PK), `execution_id`, `task_id`, `agent_id`, `primary_model`,
  `effective_model`, `fallback_model` (siempre `None` bajo esta política), `reason`,
  `provider`, `started_at`, `wait_seconds`, `retries`, `status`, `error_message`,
  `created_at`.

### 3.4 Modelos disponibles

- El catálogo de modelos disponibles se obtiene del proveedor mediante `opencode models`.
- El factory no incrusta una lista de modelos alternativos.
- El conjunto autorizado se define en `orchestration/runtime/model_hierarchies.py`
  (`AUTHORIZED_MODEL`, `AUTHORIZED_MODELS`).

## 4. Clasificación de errores

| Tipo | Indicadores | Acción |
|---|---|---|
| Cuota agotada | "quota", "usage limit reached", "free usage limit", "exhausted" | Marcar no disponible, esperar recuperación (sin cambio de modelo) |
| Límite temporal | "rate limit", "Retry-After", "hourly limit", "429" | Esperar Retry-After, reintentar mismo modelo |
| Transitorio | timeout, 5xx, network, "unavailable" | Reintentar mismo modelo |
| Autenticación | "auth", "invalid key", "unauthorized", "401", "403" | Registrar, `NEEDS_INTERVENTION` |
| Ambiguo | no clasificable | Registrar, abortar, sin cambio de modelo |

## 5. Flujo de ejecución

1. `run_task` → `adapter.invoke(agent_id, prompt, model=None)`.
2. Adapter consulta `ModelFallbackManager.select_model(agent_id)` (solo modelo autorizado).
3. Si está disponible, se usa `opencode-go/beam-free`.
4. Si falla, se clasifica el error.
5. Según clasificación: espera/reintento/abort/intervención (sin cambio de modelo).
6. Se registra en `model_fallback_log`.
7. Si no está disponible, la tarea queda `WAITING_QUOTA_RESET` hasta recuperación.
8. La recuperación se detecta por timestamp; no hay consulta activa al proveedor.

## 6. Compatibilidad

- No modifica responsabilidades normativas de los agentes.
- No rompe contratos existentes.
- Mantiene compatibilidad con los 18 agentes (un modelo para todos).
- Los agentes siguen usando `model: opencode-go/beam-free` en front-matter.
- `run_task`/`run_workflow` rechazan cualquier modelo no autorizado.

## 7. Escape hatch (no implementado)

Cualquier cambio a la política de modelo único (modelos alternativos, proveedores adicionales,
o desactivación de BEAM_FREE_ONLY) requiere autorización explícita del usuario y un nuevo ADR.
No está implementado en esta fase.

## 8. Limitaciones

- La espera real (`time.sleep`) está capeada a 5s en el adapter para responsiveness.
- La recuperación se detecta por timestamp; no hay consulta activa al proveedor de cuotas.
- No hay cambio de modelo en ningún escenario.
- El conjunto autorizado está fijo en código (`AUTHORIZED_MODELS`); cambiarlo requiere
  autorización y ADR.

## 9. Pruebas

- Unitarias/integración de fallback existen en `tests/orchestration/test_model_fallback*.py`,
  pero contienen aserciones heredadas del diseño multi-modelo anterior a BEAM_FREE_ONLY.
  No forman parte de `tests/run_all.py` y no se modificaron en esta tarea.
- La política se verifica indirectamente por `tests/run_all.py` (ALL TESTS PASSED) y por
  la inspección de `model_hierarchies.py` / agent definitions.