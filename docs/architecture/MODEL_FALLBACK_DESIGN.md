# MODEL FALLBACK MANAGER — DISEÑO TÉCNICO

## 1. Objetivo

Sistema centralizado de selección, sustitución y recuperación automática de modelos para los 18 agentes AG-001 a AG-018, integrado con `OpenCodeAdapter` y la orquestación existente.

## 2. Principios

- Todos los modelos pertenecen a `opencode-go` (OpenCode Go).
- No se utilizan modelos de pago adicional, proveedores externos ni créditos extra.
- La continuidad nunca justifica costos adicionales.
- No se duplica lógica de selección en cada agente.

## 3. Componentes

### 3.1 ModelFallbackManager

Clase en `orchestration/runtime/model_fallback.py`.

Responsabilidades:
- Mantener jerarquías ordenadas de modelos por agente.
- Clasificar errores (cuota agotada, límite temporal, transitorio, autenticación, ambiguo).
- Seleccionar alternativas cuando el modelo principal no está disponible.
- Administrar esperas (Retry-After, backoff exponencial).
- Recuperar el modelo principal cuando vuelva a estar disponible.
- Registrar cada cambio en un historial auditable.

### 3.2 Integración con OpenCodeAdapter

`OpenCodeAdapter.invoke` delega la selección de modelo al `ModelFallbackManager`:
- Si no se pasa `model`, el manager devuelve el modelo principal del agente.
- Si la invocación falla por cuota agotada, el manager selecciona la siguiente alternativa y reintenta.
- Si falla por límite temporal, el manager espera y reintenta con el mismo modelo.
- Si falla por error transitorio, aplica backoff exponencial.
- Si falla por autenticación/configuración, registra y devuelve `NEEDS_INTERVENTION`.

### 3.3 Persistencia

Tabla `model_fallback_log` en `runtime.db`:
- `log_id` (PK)
- `execution_id` (FK a executions)
- `task_id`
- `agent_id`
- `primary_model`
- `effective_model`
- `fallback_model` (si aplica)
- `reason` (quota_exhausted, rate_limit, transient, auth, ambiguous)
- `provider`
- `started_at`
- `wait_seconds`
- `retries`
- `status` (RUNNING, WAITING_RATE_LIMIT, WAITING_QUOTA_RESET, FALLBACK_ACTIVE, COMPLETED, FAILED, NEEDS_INTERVENTION)
- `error_message`
- `created_at`

### 3.4 Jerarquías por agente

Definidas en `orchestration/runtime/model_hierarchies.py` (diccionario).

Cada agente tiene una lista ordenada:
1. Modelo principal (actualmente asignado).
2. Segunda alternativa compatible con su especialidad.
3. Tercera alternativa.
4. Alternativas adicionales.

## 4. Clasificación de errores

| Tipo | Indicadores | Acción |
|---|---|---|
| Cuota agotada | "quota", "usage limit reached", "free usage limit" | Marcar no disponible, seleccionar alternativa |
| Límite temporal | "rate limit", "Retry-After", "hourly limit", "window" | Esperar Retry-After, reintentar mismo modelo |
| Transitorio | timeout, 5xx, network, "unavailable" | Backoff exponencial, reintentar mismo modelo |
| Autenticación | "auth", "invalid key", "unauthorized", "forbidden" | Registrar, NEEDS_INTERVENTION |
| Ambiguo | no clasificable | Registrar, comprobación controlada, no cambiar modelo |

## 5. Flujo de ejecución

1. `run_task` → `adapter.invoke(agent_id, prompt, model=None)`.
2. Adapter consulta `ModelFallbackManager.get_model(agent_id)`.
3. Si modelo principal disponible, lo usa.
4. Si falla, clasifica error.
5. Según clasificación:
   - Cuota: selecciona alternativa, reintenta.
   - Límite temporal: espera, reintenta mismo.
   - Transitorio: backoff, reintenta mismo.
   - Auth: NEEDS_INTERVENTION.
6. Registra en `model_fallback_log`.
7. Si todas las alternativas agotadas, tarea queda WAITING_QUOTA_RESET.
8. Cola de pendientes reintenta periódicamente.
9. Cuando principal se recupera, se prioriza en siguiente tarea.

## 6. Compatibilidad

- No modifica responsabilidades normativas de los agentes.
- No rompe contratos existentes.
- Mantiene compatibilidad con los 18 agentes actuales.
- Los agentes siguen usando `model:` en front-matter como fuente de verdad del modelo principal.
- El manager lee el front-matter para construir la jerarquía (modelo principal + alternativas).

## 7. Pruebas

- Unitarias: clasificación de errores, selección de alternativas, esperas.
- Integración: mocks de OpenCodeAdapter con errores simulados.
- No consumen cuotas reales.
