# STAGE 2G — CORRECCIÓN INTEGRAL DE ARQUITECTURA

## OBJETIVO

Corregir integralmente el enrutamiento de modelos y la delegación multiagente de AI-Project-Factory V2.

El sistema debe funcionar con Ollama como proveedor principal cuando exista un modelo compatible, y utilizar proveedores alternativos mediante un Model Fallback Manager centralizado.

AG-001 debe poder coordinar y delegar tareas reales en los agentes especializados, sin que las ejecuciones eludan el administrador central de modelos.

## REGLAS DE SEGURIDAD

- Trabajar exclusivamente en el repositorio y branch actuales.
- Preservar todos los cambios existentes, incluidos archivos no versionados.
- Realizar backups mediante COPIA, nunca mediante movimientos.
- Verificar integridad de los backups mediante SHA256.
- No sobrescribir informes anteriores.
- No eliminar ni reemplazar agentes.
- Preservar especializaciones, instrucciones, herramientas y permisos.
- No modificar configuración global de OpenCode.
- No reiniciar servicios activos.
- No instalar plugins, skills ni dependencias externas sin autorización.
- No realizar commits, merges ni publicaciones.
- No simular ejecuciones, delegaciones ni resultados.
- No declarar PASS sin evidencia.
- Detenerse ante cualquier acción destructiva o fuera del alcance autorizado.

## FASE A — INVENTARIO Y BACKUP

Leer primero:
- docs/execution/EXECUTION_ARCHITECTURE.md
- Todos los informes existentes de Stage 2A a 2F.
- Código actual de orquestación.
- Configuración y frontmatter de los 18 agentes.
- Tests y schemas.
- SESSION_LOG.md.

Detectar contradicciones entre la arquitectura existente y este encargo.

Generar backup completo del estado de trabajo, incluidos archivos no versionados, sin modificar ni mover los originales.

Verificar SHA256 y restaurabilidad del backup.

Ejecutar la línea base de pruebas y registrar resultados.

## FASE B — DISEÑO ARQUITECTÓNICO

Diseñar e implementar, de forma coherente con EXECUTION_ARCHITECTURE.md:

AG-001
  -> Delegation Execution Runtime
  -> Model Fallback Manager
  -> Model Capability Registry
  -> OpenCode / Ollama / proveedores alternativos
  -> Persistencia y auditoría

El Model Fallback Manager debe gobernar toda ejecución de agentes.

No eliminar las especializaciones de los agentes para resolver el enrutamiento.

## FASE C — MODEL CAPABILITY REGISTRY

Implementar un catálogo configurable con:
- Provider y Model ID.
- Prioridad.
- Capacidades verificadas.
- Context window.
- Uso de herramientas.
- Compatibilidad por agente y tarea.
- Disponibilidad.
- Límites de uso.
- Estado de autenticación.
- Timeouts.

Modelos locales conocidos:
- ollama/gpt-oss:20b
- ollama/qwen3:14b

Endpoint conocido:
http://192.168.1.17:11434/v1

Verificar disponibilidad antes de utilizar los modelos. No asumir capacidades que no hayan sido comprobadas.

## FASE D — MODEL FALLBACK MANAGER

Centralizar selección, disponibilidad, jerarquías y recuperación.

Diferenciar:
1. Cuota semanal agotada: excluir hasta el reset conocido y elegir el siguiente modelo compatible.
2. Límite horario: respetar Retry-After o el tiempo de recuperación y reintentar.
3. Error transitorio: backoff controlado.
4. Error de autenticación: bloquear proveedor y reportar.
5. Incompatibilidad: excluir modelo para la tarea.
6. Error ambiguo: no asumir que es una cuota agotada.

Implementar estado persistente, circuit breaker, recuperación efectiva y registro de decisiones.

No utilizar cooldown fijo como sustituto de una comprobación real.

## FASE E — DELEGATION EXECUTION RUNTIME

Implementar delegaciones reales en sesiones independientes.

Cada ejecución debe:
- Identificar agente y tarea.
- Resolver capacidades necesarias.
- Solicitar el modelo al manager.
- Crear sesión OpenCode.
- Invocar agente con modelo explícito.
- Transmitir contexto.
- Respetar permisos y herramientas.
- Capturar y verificar resultados.
- Registrar evidencias.
- Devolver resultados a AG-001.

Investigar las capacidades reales de OpenCode CLI y SDK instalados. No asumir APIs no verificadas.

No permitir que delegaciones nativas con modelos fijos eludan el manager.

## FASE F — INTEGRACIÓN CENTRAL

Auditar e integrar:
- orchestration/runtime/model_hierarchies.py
- orchestration/runtime/model_fallback.py
- orchestration/runtime/opencode_adapter.py
- orchestration/task_orchestration/model_fallback_integration.py
- orchestration/task_orchestration/delegation.py
- Persistencia y schemas.
- Los 18 agentes.
- Configuración del proyecto.

AG-001 y los subagentes deben utilizar el mismo mecanismo central.

## FASE G — PERSISTENCIA

Registrar:
- Execution ID y Parent Execution ID.
- Session ID.
- Agent ID y Task ID.
- Provider y modelo.
- Estado y tiempos.
- Reintentos y errores.
- Motivo del fallback.
- Modelo anterior y nuevo.
- Resultado.

Los registros deben sobrevivir a reinicios. No guardar credenciales ni secretos.

Reutilizar los mecanismos de persistencia existentes cuando corresponda.

## FASE H — RESILIENCIA

Resolver interrupciones, fallos parciales, proveedores inaccesibles, errores de subagentes y reinicios.

Evitar duplicar tareas y operaciones no idempotentes.

No declarar una tarea completada sin verificar el resultado.

## FASE I — PRUEBAS

Implementar pruebas unitarias, integración, contratos y LIVE.

Validar:
- Selección Ollama.
- Compatibilidad por agente.
- Fallback.
- Cuota semanal.
- Límite horario.
- Retry-After.
- Recuperación real.
- Autenticación.
- Errores transitorios y ambiguos.
- Delegación real.
- Permisos.
- Persistencia.
- Recuperación de ejecuciones.
- Ausencia de bypass del manager.

Los mocks no constituyen evidencia LIVE.

Evitar consumir cuotas externas innecesariamente.

## FASE J — AUDITORÍA INDEPENDIENTE AG-015

AG-015 debe inspeccionar código, seguridad, permisos, aislamiento, delegación, fallback, cuotas, persistencia y evidencias.

Debe ejecutar sus propias validaciones y emitir un informe independiente.

No aceptar como evidencia suficiente el informe de AG-001.

## FASE K — DOCUMENTACIÓN Y CIERRE

Documentar arquitectura, interfaces, capacidades, jerarquías, cuotas, delegación, recuperación, seguridad y resultados.

Crear informes nuevos sin sobrescribir los anteriores.

Informe final previsto:
010_STAGE2G_FINAL_REPORT.md

Respetar la secuencia documental existente si corresponde otro número.

## CRITERIOS DE ACEPTACIÓN

- Los 18 agentes preservados.
- Especializaciones y permisos verificados.
- Ollama principal cuando sea compatible.
- Proveedores alternativos integrados.
- Toda ejecución pasa por el manager.
- AG-001 delega realmente.
- Selección dinámica de modelos.
- Gestión diferenciada de cuotas.
- Persistencia efectiva.
- Pruebas reales y evidencia verificable.
- Auditoría independiente AG-015.
- Sin pérdida de datos ni cambios destructivos.

Estados permitidos:
PASS
PASS_WITH_OBSERVATIONS
BLOCKED
FAIL

No declarar PASS sin evidencia.

## INFORME FINAL

Entregar resumen ejecutivo, arquitectura, archivos modificados y nuevos, backups SHA256, agentes invocados, sesiones, modelos, pruebas, evidencia LIVE, auditoría AG-015, bloqueos y estado de cada criterio.

PRINCIPIO FINAL:

El sistema debe planificar, delegar, seleccionar modelos, gestionar cuotas, recuperarse de errores y completar trabajos complejos mediante autonomía supervisada, segura, auditable y verificable.
