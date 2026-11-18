# Informe de Auditoría de Recursos — TESTDESA (LXC 108)

> **Tipo de documento:** Informe de auditoría / diagnóstico (solo lectura).
> **Fecha de emisión:** 2026-11-18.
> **Fuente de datos:** `/tmp/opencode/audit/CONSOLIDATED.md` (auditoría de diagnóstico, Etapa 1 completada).
> **Alcance:** sistema `testdesa` (LXC 108): almacenamiento, backups, RAM, SWAP y procesos.
> **Estado de ejecución:** **no se ha eliminado ni modificado ningún archivo, contenedor, imagen, volumen ni configuración.** Todas las acciones de limpieza y optimización listadas son propuestas pendientes de aprobación.
> **Nota sobre cifras:** los valores provienen de la auditoría consolidada. Los totales recuperables son estimaciones; las cifras marcadas como «aprox.» o rangos requieren verificación antes de ejecutar cualquier operación.

---

## 1. Estado actual del almacenamiento

| Concepto | Valor |
|---|---|
| Hostname | `testdesa` |
| Virtualización | LXC (`systemd-detect-virt = lxc`), LXC 108 |
| Kernel | `7.0.14-25-pve` |
| Usuario de auditoría | `developer` (uid=1000); grupos: `developer`, `sudo`, `users`, `docker` |
| Filesystem root | `/dev/loop12` (ext4) |
| Capacidad total | 112 GB |
| Espacio usado | 93 GB |
| Espacio disponible | 14 GB |
| Porcentaje de uso | **88 %** |
| `/tmp` | `tmpfs`, 63 GB totales, 2,2 GB usados |
| Montajes externos | Ninguno (no hay NFS/SMB/CIFS); solo `lxcfs`. Docker usa `overlay` interno. |

**Lectura:** el filesystem root está al 88 % de ocupación, con 14 GB libres. El espacio lo consumen principalmente capas de Docker (imágenes, build cache y volúmenes), caches reconstruibles y copias duplicadas de migración/release, no datos de usuario irrecuperables.

---

## 2. Distribución del consumo por directorio

### 2.1 Consumo por directorios de primer nivel

| Directorio | Consumo | Observaciones |
|---|---|---|
| `/home` | 6,6 GB | Incluye proyectos, caches y backups del usuario `developer` |
| `/tmp` | 2,2 GB | Casi todo bajo `/tmp/opencode` (tmpfs) |
| `/opt` | 1,5 GB | Plataforma de atención comercial |
| `/usr` | 1,3 GB | Sistema base |
| `/var` | 297 MB | Incluye `/var/log` (41 MB) |
| `/etc` | 4,1 MB | Configuración |
| `/run` | 716 KB | tmpfs volátil |

### 2.2 Desglose de `/home/developer` (6,6 GB)

| Subdirectorio / concepto | Consumo |
|---|---|
| `webl2` | 1,1 GB |
| `projects` | 906 MB (`sistema-taller` 496 MB, `ChatComercial` 411 MB) |
| `taller-postgres` | 71 MB |
| `AI-Project-Factory` | 17 MB |
| `backups` | 876 KB |
| `backups-taller` | 644 KB |
| `prompts` | 16 KB |
| `.cache` | 812 MB (`ms-playwright` 701 MB, `prisma` 105 MB) |
| `.npm` | 3,0 GB (`_cacache` 2,6 GB, `_npx` 367 MB) |
| `.local` | 618 MB (`node` 330 MB, `bin` 194 MB, `share` 95 MB) |
| `.opencode/bin/opencode` | 252 MB |
| `.opencode/opencode.db` | 64 MB |

### 2.3 Desglose de `/opt` (1,5 GB)

| Concepto | Consumo |
|---|---|
| `plataforma-atencion-comercial` | 1,5 GB |
| └ `node_modules` | 1,3 GB |
| └ `apps` | 259 MB (`.next` 257 MB) |
| └ `containerd` | solo root |

### 2.4 Desglose de `/tmp` (2,2 GB)

| Concepto | Consumo |
|---|---|
| `/tmp/opencode` | 2,2 GB |
| └ `vr_final` | 567 MB |
| └ `migrate.log` | 363 MB |
| └ `vr3` | 310 MB |
| └ `vr2` | 310 MB |
| └ `vr` | 310 MB |
| └ `verify_final` | 310 MB |
| └ `captcha.png` | 2,9 MB |
| └ otros archivos pequeños | resto |
| `node-compile-cache` | 11 MB |
| `tsx-1000` | 3,8 MB |

### 2.5 Distribución de Docker (`docker system df`)

| Recurso | Total | Activos | Tamaño | Recuperable |
|---|---|---|---|---|
| Imágenes | 42 | 27 | 33,99 GB | **15,08 GB (44 %)** |
| Contenedores | 36 | 33 | 468,5 MB | 491,5 kB |
| Volúmenes locales | 38 | 18 | 1,642 GB | 588,3 MB (35 %) |
| Build Cache | 178 | 0 | 48,91 GB | **48,91 GB (100 %)** |

### 2.6 `node_modules` (top-level, ~2,3 GB)

| Ruta | Consumo |
|---|---|
| `/opt/plataforma-atencion-comercial/node_modules` | 1,3 GB |
| `/home/developer/projects/sistema-taller/node_modules` | 377 MB |
| `/home/developer/projects/ChatComercial/node_modules` | 275 MB |
| `/home/developer/projects/ChatComercial/server/node_modules` | 134 MB |
| `/home/developer/.local/node/lib/node_modules` | 162 MB (Supabase CLI 140 MB) |
| `/home/developer/.npm/_npx` | 367 MB (Supabase CLI duplicado 140 MB × 2) |

---

## 3. Inventario de backups

| Ubicación | Tamaño | Contenido | Duplicados / notas |
|---|---|---|---|
| `/home/developer/backups` | 876 KB | 10 archivos `cap-pre-f*.sql.gz`, directorios `cap-f5` y `chatcomercial-legacy` | — |
| `/home/developer/backups-taller` | 644 KB | `supabase_postgres_20261109_112201.sql` (632 KB), `supabase_storage_20261109_112203.tar.gz` (45 bytes) | El `.tar.gz` de storage es sospechosamente pequeño (45 bytes): verificar integridad |
| `/home/developer/webl2/.migration-backup` | 202 MB | `webl2-pre-migration.tar.gz` 134,8 MB; `phase8-csrf-pre.tar.gz` 67,8 MB; `phase8-phpmailer` 106 KB; `phase8-webhooks` 8,7 KB; `phase13-mp` 2,5 KB; `phase15` 61,9 KB; `phase22-xss` 46,7 KB; `phase34` 30,9 KB | Backups de migración: conservar al menos los recientes |
| `/home/developer/webl2/release` | — | `webl2-php84-release.tar.gz` 129 MB; `web12-php84-final-release.tar.gz` 129 MB | Duplicados con `/tmp/opencode/vr_final` |
| `/tmp/opencode/vr_final` | 567 MB | Copias de release `.tar.gz` + engine SQL | Duplicados de `webl2/release` y de los SQL |
| `/tmp/opencode/vr`, `vr2`, `vr3`, `verify_final` | ~310 MB cada | Copias de engine/SQL | Duplicados entre sí |

### 3.1 Hashes duplicados confirmados

| Archivo | Tamaño | Copias | Conservar |
|---|---|---|---|
| `icp_v4_game_server.sql` (l2j) | 73,9 MB | 7 (original + 6 copias) | 1 original |
| `icp_v4_game_server.sql` (l2off) | 73,9 MB | 7 (original + 6 copias) | 1 original |
| `webl2-php84-release.tar.gz` | 129 MB | 2 | 1 |
| `web12-php84-final-release.tar.gz` | 129 MB | 2 | 1 |

**Imágenes Docker duplicadas por ID (5 grupos):**

| Imagen | Tamaño por copia | Copias |
|---|---|---|
| `postgres-meta` (public.ecr + dockerhub) | 569 MB | 2 |
| `gotrue` | 94,4 MB | 2 |
| `edge-runtime` | 1,14 GB | 2 |
| `studio` | 1,79 GB | 2 |
| `chatcomercial:latest` == `chatcomercial:previous` | 74,3 MB | 2 |

---

## 4. Archivos candidatos a eliminación

| # | Candidato | Tamaño | Naturaleza | Reconstruible |
|---|---|---|---|---|
| 1 | Docker Build Cache (`178` entradas, 0 activas) | 48,91 GB | Cache de compilación | Sí |
| 2 | Imágenes Docker no usadas / duplicadas | ~15,08 GB | Imágenes | Sí (re-pull) |
| 3 | Volúmenes Docker huérfanos (`LINKS=0`, hash sin nombre) | ~588 MB (varios de 48–65 MB c/u) | Volúmenes | No — verificar antes |
| 4 | `/tmp/opencode` temporales (`migrate.log` 363 MB, `vr*` 1,2 GB, `vr_final` 567 MB) | ~2,2 GB | Copias de release/migración | Verificar (pueden ser datos de auditoría) |
| 5 | `/home/developer/.npm/_cacache` | 2,6 GB | Cache npm | Sí |
| 6 | `/home/developer/.cache/ms-playwright` | 701 MB | Cache de navegadores | Sí |
| 7 | `/home/developer/webl2/.migration-backup` | 202 MB | Backups de migración | No — conservar recientes |
| 8 | `webl2/release` `.tar.gz` duplicados con `/tmp` | 258 MB | Duplicados | Sí (conservar 1 de cada par) |
| 9 | `icp_v4_game_server.sql` duplicados (6 copias × 2 variantes) | ~443 MB | Duplicados | Sí (conservar original) |
| 10 | `node_modules` (top-level) | ~2,6 GB | Dependencias | Sí, vía `npm install` (riesgo de tiempo) |
| 11 | `.next` cache (`plataforma.../apps/web/.next`) | 257 MB | Cache de build | Sí |
| 12 | `.npm/_npx` | 367 MB | Cache npm (Supabase CLI duplicado) | Sí |
| 13 | `AI-Project-Factory/.venv` | 14 MB | Entorno virtual Python | Sí |

> **Importante:** los elementos 3, 4, 7 y 10 **no deben eliminarse sin verificación/aprobación** (ver sección 13).

---

## 5. Espacio recuperable estimado

| Categoría | Recuperable estimado | Confidence |
|---|---|---|
| Docker Build Cache | 48,91 GB | Alta (100 % reclaimable, 0 activas) |
| Imágenes Docker no usadas / duplicadas | ~15,08 GB | Alta |
| Caches (`_cacache` 2,6 GB + `_npx` 367 MB + playwright 701 MB + `.next` 257 MB) | ~3,9 GB | Alta (rebuildable) |
| Temporales `/tmp/opencode` | ~1,5–2,2 GB | Media (verificar contenido) |
| Duplicados (release 258 MB + SQL ~443 MB) | ~0,7 GB | Alta (hashes confirmados) |
| Volúmenes huérfanos | ~0,6 GB | Media (verificar `LINKS=0`) |
| Backups duplicados / antiguos | ~0,5 GB | Media (conservar recientes) |

**Total recuperable estimado (conservador): ~55–65 GB.**

> El grueso del ahorro (≈64 GB de ≈60 GB) proviene de Docker: build cache (48,9 GB) e imágenes (15,08 GB). El resto son caches, temporales y duplicados. La cifra es una estimación: el espacio real liberado depende de qué elementos se aprueben y de que no haya datos en uso.

---

## 6. Estado de RAM

| Métrica | Valor |
|---|---|
| Memoria total | 8,0 GiB |
| Memoria usada | 4,1 GiB |
| Memoria libre | 71 MiB |
| Buff/cache | 4,3 GiB |
| **MemAvailable** | **3,9 GiB** |
| KReclaimable | 3,38 GiB |
| Slab | 1,07 GiB |

**Lectura:** aunque la memoria «libre» es solo 71 MiB, `MemAvailable` es 3,9 GiB y `buff/cache` (4,3 GiB) es en gran parte reclaimable (KReclaimable 3,38 GiB). No hay señales de presión activa de memoria: el sistema puede liberar cache bajo demanda. El consumo real de procesos es ~4,1 GiB sobre 8 GiB.

---

## 7. Estado de SWAP

| Métrica | Valor |
|---|---|
| Swap total | 4,0 GiB |
| Swap usado | **4,0 GiB (100 %)** |
| Swap libre | 80 KiB |
| `swappiness` | 60 |
| `SwapCached` | 0 |
| `vmstat si/so` | Bajos (19/38 inicial, luego < few hundred) |

**Diagnóstico:** el swap está completamente lleno, pero **no hay thrashing activo**. `si/so` bajos y `SwapCached=0` indican páginas antiguas residentes en swap, no una fuga o presión de memoria en curso. Junto con un `MemAvailable` alto (3,9 GiB), el cuadro es de swap «estancado» con páginas frías, no de memoria agotada. Se justifica reducir `swappiness` a 10–20 para evitar que se use swap prematuramente.

---

## 8. Ranking de procesos consumidores

### 8.1 Top 20 por RSS

| # | Proceso | RSS | % MEM |
|---|---|---|---|
| 1 | `dockerd` | 941 MB | 11,2 % |
| 2 | chromium renderer (waha) | 359 MB | 4,2 % |
| 3 | `opencode serve` | 344 MB | 4,0 % |
| 4 | chromium main (waha) | 291 MB | 3,4 % |
| 5 | `beam.smp` logflare (supabase analytics) | 285 MB | 3,3 % |
| 6 | `opencode` (CLI) | 239 MB | 2,8 % |
| 7 | `puma` (chatwoot) | 180 MB | 2,1 % |
| 8 | `node dist/main` (cap-api?) | 173 MB | 2,0 % |
| 9 | `next-server` | 168 MB | 1,9 % |
| 10 | chromium renderer 2 | 117 MB | 1,3 % |
| 11 | postgres checkpointer | 95 MB | 1,1 % |
| 12 | postgres idle (supabase) | 89 MB | — |
| 13 | postgres idle (supabase) | 86 MB | — |
| 14 | `beam.smp` realtime | 85 MB | — |
| 15 | postgres idle | 84 MB | — |
| 16 | `next-server` (v15.5.29) | 82 MB | — |
| 17 | `node dist/server/server.js` | 75 MB | — |
| 18 | `node dist/start/server.js?` | 56 MB | — |
| 19 | `containerd` | 60 MB | — |
| 20 | `node /app/node_modules/.bin/tsx` | 57 MB | — |

### 8.2 Contenedores Docker por RAM

| Contenedor | RAM usada | Límite |
|---|---|---|
| `cap-waha` | 891 MB | Sin límite (8 GB) |
| `supabase_analytics` | 301 MB | Sin límite (8 GB) |
| `cap-chatwoot` | 211 MB | Sin límite (8 GB) |
| `cap-api` | 202 MB | 512 MB (39,5 %) |
| `supabase_studio` | 183 MB | Sin límite (8 GB) |
| `supabase_db` | 180 MB | Sin límite (8 GB) |
| `supabase_realtime` | 98 MB | Sin límite (8 GB) |
| `supabase_pg_meta` | 78 MB | Sin límite (8 GB) |
| `cap-web` | 68 MB | 512 MB |
| `supabase_storage` | 63 MB | Sin límite (8 GB) |
| `cap-postgres` | 23 MB | 512 MB |
| `cap-redis` | 3,8 MB | 256 MB |

### 8.3 Proceso anómalo

- `opencode` **PID 4039384**, estado `Tl` (**detenido/suspendido**), 12:33 de tiempo CPU. Requiere investigación: podría ser una sesión suspendida; **no matar sin confirmar**.

---

## 9. Diagnóstico de la causa raíz

**Almacenamiento (88 % de uso, 14 GB libres):**

1. **Causa primaria — Docker sin poda:** el build cache acumula 48,91 GB (178 entradas, 0 activas, 100 % recuperable) y las imágenes 33,99 GB con 15,08 GB recuperables, incluyendo 5 grupos de imágenes duplicadas por ID. Docker es responsable de ≈64 GB del espacio recuperable total.
2. **Causa secundaria — copias duplicadas:** los archivos SQL de engine (`icp_v4_game_server.sql`, 73,9 MB × 7 por variante) y los `.tar.gz` de release (129 MB × 2) están replicados en `/tmp/opencode/vr*` y `webl2/release`; ~1,2 GB de temporales en `/tmp`.
3. **Causa terciaria — caches reconstruibles:** `.npm/_cacache` (2,6 GB), `ms-playwright` (701 MB), `.next` (257 MB) y `_npx` (367 MB) suman ~3,9 GB que pueden regenerarse.
4. **Contribuyente — volúmenes huérfanos:** 38 volúmenes, 18 activos, con varios `LINKS=0` sin nombre (~588 MB recuperables).

**Memoria / SWAP:**

5. El swap al 100 % **no** refleja una fuga: `si/so` bajos y `SwapCached=0` muestran páginas antiguas estancadas. La causa es el valor por defecto `swappiness=60`, que permite usar swap antes de agotar la cache reclaimable (KReclaimable 3,38 GiB). Existen 3,9 GiB disponibles, por lo que **no hay presión real de memoria**.
6. El mayor consumidor es `dockerd` (941 MB, 11,2 %), esperable con ~33 contenedores activos; varios contenedores (cap-waha 891 MB) no tienen límite de memoria.

---

## 10. Problemas detectados

| # | Problema | Impacto | Severidad |
|---|---|---|---|
| 1 | Build cache de Docker con 48,91 GB sin uso | Alto consumo de disco | Alta |
| 2 | 15,08 GB de imágenes recuperables y 5 grupos duplicados | Desperdicio de espacio | Alta |
| 3 | Volúmenes Docker huérfanos (`LINKS=0`) con datos de BD sin identificar | Riesgo de pérdida si se limpian a ciegas | Media |
| 4 | Duplicados de SQL/release en `/tmp/opencode` (~1,2 GB + 258 MB + ~443 MB) | Desperdicio; ambigüedad sobre cuál es la copia válida | Media |
| 5 | `supabase_storage_...tar.gz` de 45 bytes | Posible backup corrupto/vacío | Media |
| 6 | Caches reconstructibles (~3,9 GB) sin política de limpieza | Crecimiento sostenido del disco | Media |
| 7 | Swap al 100 % con `swappiness=60` | Uso prematuro de swap; latencia potencial | Media |
| 8 | Contenedores sin límite de memoria (cap-waha 891 MB, etc.) | Riesgo de consumo descontrolado | Media |
| 9 | Proceso `opencode` PID 4039384 en estado `Tl` (suspendido) | Posible sesión colgada; 12:33 CPU acumulado | Baja/Media |
| 10 | `cap-api` al 39,5 % de su límite de 512 MB | Margen acceptable, pero vigilar | Baja |

---

## 11. Recomendaciones

| # | Recomendación | Ahorro / beneficio |
|---|---|---|
| 1 | Limpiar Docker build cache (`docker builder prune`) | 48,9 GB |
| 2 | Eliminar imágenes duplicadas / no usadas (~15 GB reclaimable) | ~15 GB |
| 3 | Eliminar volúmenes huérfanos (`LINKS=0`) **tras verificar** | ~0,6 GB |
| 4 | Limpiar temporales duplicados de `/tmp/opencode` **tras verificar** | ~1,5–2 GB |
| 5 | Limpiar caché npm (`_cacache` + `_npx`) | ~3,0 GB |
| 6 | Limpiar caché de Playwright si no se usa | 0,7 GB |
| 7 | Consolidar backups: conservar últimos 3 por proyecto y eliminar duplicados por hash | ~0,5 GB |
| 8 | Reducir `swappiness` a 10–20 | Evita uso prematuro de swap |
| 9 | Investigar el proceso `opencode` suspendido (PID 4039384) | Clarificar sesión colgada |
| 10 | Establecer límites de memoria en contenedores sin límite (cap-waha, supabase, etc.) | Previene consumo descontrolado |
| 11 | Evitar compilaciones simultáneas (`npm build` en paralelo) | Reduce picos de build cache/RAM |
| 12 | Monitorear `dockerd` RSS (941 MB, normal con muchos contenedores) | Vigilancia, sin acción inmediata |
| 13 | Programar limpieza automática periódica de build cache | Previene recurrencia |

---

## 12. Plan de ejecución por etapas

### Etapa 1 — Diagnóstico
**Estado: COMPLETADA.** Auditoría consolidada de almacenamiento, Docker, backups, RAM/SWAP y procesos. No se realizaron cambios.

### Etapa 2 — Limpieza segura (requiere aprobación)

| Paso | Acción | Ahorro estimado |
|---|---|---|
| 2.1 | `docker builder prune -f` (build cache) | 48,9 GB |
| 2.2 | Eliminar imágenes dangling/duplicadas | 15 GB |
| 2.3 | Eliminar volúmenes huérfanos (`LINKS=0`) tras verificar | 0,6 GB |
| 2.4 | Limpiar duplicados en `/tmp/opencode` | 1,5 GB |
| 2.5 | Limpiar caché npm | 2,6 GB |
| 2.6 | Limpiar caché de Playwright | 0,7 GB |
| 2.7 | Consolidar backups duplicados | 0,5 GB |

### Etapa 3 — Optimización (requiere aprobación)

| Paso | Acción |
|---|---|
| 3.1 | Ajustar `swappiness` a 10–20 |
| 3.2 | Establecer límites de memoria en contenedores sin límite |
| 3.3 | Programar limpieza automática de build cache |
| 3.4 | Revisar el proceso `opencode` suspendido |

### Etapa 4 — Validación

| Paso | Acción |
|---|---|
| 4.1 | Verificar builds/tests tras la limpieza |
| 4.2 | Re-ejecutar `df` y `free` para confirmar espacio y memoria |

---

## 13. Riesgos de cada operación

| Operación | Riesgo | Mitigación |
|---|---|---|
| Poda de build cache (2.1) | Pérdida de cache de compilación → primeros builds más lentos | Aceptable: es 100 % reconstruible; ejecutar en ventana de bajo uso |
| Eliminación de imágenes (2.2) | Imagen en uso por algún contenedor detenido; fallo al reiniciar | Confirmar que no estén referenciadas; conservar `current`/`latest` vigentes; verificar los 5 grupos duplicados |
| Eliminación de volúmenes huérfanos (2.3) | **Pérdida irreversible de datos de bases de datos** si un volumen con `LINKS=0` contiene datos válidos | Inspeccionar contenido y fecha antes de borrar; hacer backup; nunca eliminar volúmenes persistentes sin verificar |
| Limpieza de `/tmp/opencode` (2.4) | Puede contener datos de auditoría/verificación aún útiles | Verificar qué archivos son copias confirmadas por hash; conservar originales y los 4 `.tar.gz` de release válidos |
| Limpieza de caché npm / Playwright / `.next` (2.5, 2.6) | Recarga de dependencias/navegadores; consumo de red y tiempo | Solo en equipos con connectivity; no eliminar `node_modules` de proyectos activos sin confirmar (rebuildable pero lento) |
| Consolidación de backups (2.7) | Eliminar el único backup válido de un proyecto o versión | Identificar proyecto/fecha de cada backup; conservar al menos los 3 más recientes y validar integridad (especialmente el `.tar.gz` de 45 bytes) |
| Ajuste de `swappiness` (3.1) | Cambio de comportamiento de memoria; requiere privilegio y persistencia | Probar en caliente y documentar; valor 10–20; monitorizar `si/so` y `MemAvailable` |
| Límites de memoria en contenedores (3.2) | Si el límite es demasiado bajo, el contenedor puede ser OOM-killed | Medir uso pico antes de fijar el límite (cap-waha 891 MB); aplicar gradualmente |
| Limpieza automática de build cache (3.3) | Poda agresiva recurrente que afecte builds en curso | Programar fuera de horarios de build; excluir cache activa |
| Proceso `opencode` suspendido (3.4) | Matar una sesión de trabajo activa; perder estado | Investigar PID 4039384 (estado `Tl`, 12:33 CPU); **no matar sin confirmar con el usuario** |
| Verificación final (4.1, 4.2) | Builds/tests pueden fallar si se eliminó una dependencia/cache necesaria | Ejecutar suite de tests tras cada etapa; revertir desde el original si aplica |

---

## Resumen ejecutivo

- El root filesystem está al **88 %** (93 GB de 112 GB usados; 14 GB libres).
- Casi todo el espacio recuperable (**~64 de ~65 GB**) está en Docker: build cache 48,91 GB + imágenes 15,08 GB.
- Hay **duplicados confirmados por hash** de SQL (73,9 MB × 7 por variante) y releases (129 MB × 2), además de ~1,2 GB de temporales en `/tmp`.
- La **RAM está sana** (3,9 GiB disponibles, cache reclaimable); el swap al 100 % **no es una fuga**, sino páginas frías con `swappiness=60`.
- El mayor proceso es `dockerd` (941 MB), esperable; hay un proceso `opencode` suspendido a investigar.
- Se proponen **13 recomendaciones** en un plan de **4 etapas**. **No se ejecutó ninguna acción destructiva**: todo requiere aprobación, con énfasis en no tocar volúmenes de BD, backups sin identificar ni el proceso suspendido sin confirmación.

---

## 14. Configuración de modelos y agentes

> **Fuente:** definiciones ejecutables en `.opencode/agents/*.md` (campo `model:` del front-matter), `install/docs/CONFIGURATION_GUIDE.md` y `PROJECT_STATUS.md`. Estado de ejecución de esta auditoría: sesión de trabajo TESTDESA (2026-11-18).

### 14.1 Proveedor

- **Proveedor:** OpenCode Go (`opencode-go`), configurado en OpenCode v2.2.5 mediante la variable de entorno `OPENCODE_API_KEY`.
- Los modelos se asignan por agente en las definiciones ejecutables de `.opencode/agents/`; no hay modelo global hard-codeado en `opencode.json`.

### 14.2 Modelos asignados por agente

| Agente | Rol | Modelo asignado |
|---|---|---|
| AG-001 | Project Coordinator | `opencode-go/qwen4-max` |
| AG-002 | Quality Gatekeeper | `opencode-go/qwen3.8-flash` |
| AG-003 | Security & Risk Manager | `opencode-go/qwen4-max` |
| AG-004 | Business Analyst | `opencode-go/qwen3.8-flash` |
| AG-005 | Software Architect | `opencode-go/qwen4-max` |
| AG-006 | UX/UI Designer | `opencode-go/qwen3.8-flash` |
| AG-007 | Database Architect | `opencode-go/kimi-k2.7-code` |
| AG-008 | Backend Developer | `opencode-go/kimi-k2.7-code` |
| AG-009 | Frontend Developer | `opencode-go/kimi-k2.7-code` |
| AG-010 | Database Developer | `opencode-go/kimi-k2.7-code` |
| AG-011 | Integration Engineer | `opencode-go/kimi-k2.7-code` |
| AG-012 | QA Automation Engineer | `opencode-go/qwen3.8-flash` |
| AG-013 | Code Reviewer | `opencode-go/qwen4-max` |
| AG-014 | Performance Engineer | `opencode-go/qwen3.8-flash` |
| AG-015 | Security Auditor | `opencode-go/qwen4-max` |
| AG-016 | DevOps Engineer | `opencode-go/qwen3.8-flash` |
| AG-017 | Deployment Manager | `opencode-go/qwen3.8-flash` |
| AG-018 | Documentation Engineer | `opencode-go/qwen3.8-flash` |

**Resumen de asignación:** 8 agentes con `qwen3.8-flash`, 5 con `kimi-k2.7-code` (perfiles de código/datos), 5 con `qwen4-max` (coordinación, arquitectura, seguridad y revisión).

### 14.3 Validación AG-002

- **Veredicto: PASS**, ejecutado por AG-002 (Quality Gatekeeper) con el modelo `opencode-go/qwen3.8-flash`, conforme a su definición en `.opencode/agents/ag-002-quality-gatekeeper.md`.
- La validación confirma que la ejecución de agentes sobre el proveedor OpenCode Go es operativa y que las salidas de esta auditoría (secciones 1–13) cumplen los criterios de verificación del quality gate.

### 14.4 Estado de ejecución de agentes en esta auditoría

**Agentes que completaron su tarea:**

| Agente | Tarea completada |
|---|---|
| AG-018 | Generó el informe de auditoría de recursos (este documento, `TESTDESA_AUDITORIA_RECURSOS.md`) |
| AG-002 | Validó la ejecución — veredicto PASS con `qwen3.8-flash` |
| AG-014 | Análisis de rendimiento (RAM, SWAP, procesos consumidores) |
| AG-016 | Análisis DevOps (almacenamiento, Docker, backups) |
| AG-015 | Análisis de seguridad (volúmenes huérfanos, integridad de backups, operación destructiva) |

**Agentes pendientes:** el resto de agentes definidos (AG-001, AG-003 a AG-013, AG-017) no han intervenido en la Etapa 1 de esta auditoría. Su participación corresponde a las etapas 2–4 (limpieza, optimización y validación), que **requieren aprobación humana** antes de ejecutarse.

### 14.5 Errores registrados y resolución

| Error | Impacto | Estado |
|---|---|---|
| Cuota del proveedor LLM anterior agotada (blocker B-05 en `PROJECT_STATUS.md`); causó timeouts de AG-008 y AG-013 en la fase del piloto (`PROJECT_HANDOFF.md`) | Bloqueo externo de ejecución de agentes | **Resuelto / mitigado**: la migración al proveedor OpenCode Go con los modelos de la tabla 14.2 restableció la ejecución; B-05 ya no bloquea el piloto y todos los agentes de esta auditoría operaron sin incidentes de cuota |

---

## 15. Validación integral de los 18 agentes

> **Fuente:** `/home/developer/backups/testdesa-limpieza/AGENT_VALIDATION.md` — validación individual ejecutada el **2026-11-18 15:47:20 UTC** contra el proveedor esperado `opencode-go` (OpenCode Go). Configuración contrastada con los front-matter `model:` de `.opencode/agents/*.md` y con el respaldo previo a la reconfiguración en `/home/developer/backups/testdesa-limpieza/model-config-backup/`.

### 15.1 Tabla de validación — modelo esperado vs. efectivo

| Agente | Rol | Modelo esperado | Modelo efectivo | Proveedor | Resultado |
|---|---|---|---|---|---|
| AG-001 | Project Coordinator | `qwen4-max` | `qwen4-max` | opencode-go | **PASS** |
| AG-002 | Quality Gatekeeper | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |
| AG-003 | Security & Risk Manager | `qwen4-max` | `qwen4-max` | opencode-go | **PASS** |
| AG-004 | Business Analyst | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |
| AG-005 | Software Architect | `qwen4-max` | `qwen4-max` | opencode-go | **PASS** |
| AG-006 | UX/UI Designer | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |
| AG-007 | Database Architect | `kimi-k2.7-code` | `kimi-k2.7-code` | opencode-go | **PASS** |
| AG-008 | Backend Developer | `kimi-k2.7-code` | `kimi-k2.7-code` | opencode-go | **PASS** |
| AG-009 | Frontend Developer | `kimi-k2.7-code` | `kimi-k2.7-code` | opencode-go | **PASS** |
| AG-010 | Database Developer | `kimi-k2.7-code` | `kimi-k2.7-code` | opencode-go | **PASS** |
| AG-011 | Integration Engineer | `kimi-k2.7-code` | `kimi-k2.7-code` | opencode-go | **PASS** |
| AG-012 | QA Automation Engineer | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |
| AG-013 | Code Reviewer | `qwen4-max` | `qwen4-max` | opencode-go | **PASS** |
| AG-014 | Performance Engineer | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |
| AG-015 | Security Auditor | `qwen4-max` | `qwen4-max` | opencode-go | **PASS** |
| AG-016 | DevOps Engineer | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |
| AG-017 | Deployment Manager | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |
| AG-018 | Documentation Engineer | `qwen3.8-flash` | `qwen3.8-flash` | opencode-go | **PASS** |

### 15.2 Resumen de resultados

- **Agentes validados: 18/18 — todos PASS.** El modelo efectivo coincide con el esperado en los 18 casos, sin columnas de error.
- **Agentes WARNING: 0. Agentes FAIL: 0.**
- **Modelos con cuota agotada: ninguno.** Todos los modelos probados (`qwen4-max`, `qwen3.8-flash`, `kimi-k2.7-code`) respondieron OK bajo el proveedor `opencode-go`.
- **Correcciones aplicadas: ninguna fue necesaria** — la configuración ya estaba aplicada al momento de la validación.
- Las proporciones confirman la tabla 14.2: 8 agentes con `qwen3.8-flash`, 5 con `kimi-k2.7-code`, 5 con `qwen4-max`.

### 15.3 Caso AG-001: uso temporal previo a la reconfiguración (Beam Free)

El registro de validación muestra para AG-001 `esperado = efectivo = qwen4-max`, resultado PASS. No obstante, se documenta el antecedente para trazabilidad completa:

- **Estado previo a la reconfiguración:** en el respaldo de configuración conservado en `model-config-backup/`, la definición ejecutable de AG-001 **no declaraba campo `model:`** en su front-matter, y el `opencode.json` de respaldo tampoco fijaba un modelo global. AG-001 resolvía por tanto el modelo por defecto de la sesión, que en ese periodo correspondía al proveedor anterior **Beam en su nivel gratuito ("Beam Free")**.
- **Naturaleza temporal:** ese uso fue una condición transitoria **anterior a la reconfiguración** hacia OpenCode Go, no una desviación detectada por la validación. Los síntomas del nivel gratuito quedaron registrados en la época: `SESSION_LOG.md` consigna "Model: OpenCode Beam (current)" y el `INFORME_ETAPA_2.md` documenta un bloqueo por el error **"Free usage limit reached"** de la cuota gratuita del proveedor anterior (coherente con el blocker B-05 de `PROJECT_STATUS.md` y con la sección 14.5 de este informe).
- **Estado actual:** tras la reconfiguración, `.opencode/agents/ag-001-project-coordinator.md` declara explícitamente `model: opencode-go/qwen4-max`, y la validación del 2026-11-18 confirmó que el modelo efectivo en ejecución es `qwen4-max` sobre `opencode-go` (**PASS**). El caso queda cerrado: no hay ninguna acción pendiente sobre AG-001.

### 15.4 Confirmación de herencia

- **Herencia de proveedor:** los 18 agentes resolvieron contra `opencode-go` en la validación; ningún agente mostró herencia de un proveedor distinto o residual del proveedor anterior.
- **Herencia de modelo:** verificado que **los 18 archivos ejecutables** `.opencode/agents/ag-0XX-*.md` contienen hoy un campo `model:` explícito con valor `opencode-go/...`. Por tanto ningún agente depende ya de la herencia de un modelo global/default (situación en la que estaba AG-001 antes de la reconfiguración, véase 15.3).
- **Coherencia esperada–efectiva:** la coincidencia 18/18 entre modelo esperado y modelo efectivo confirma que la cadena de resolución de OpenCode (front-matter del agente → proveedor → modelo) está aplicando la configuración declarada sin herencias no intencionadas.
- **Alineamiento con la auditoría:** los modelos efectivos validados coinciden exactamente con la tabla de asignación 14.2 de este informe.
