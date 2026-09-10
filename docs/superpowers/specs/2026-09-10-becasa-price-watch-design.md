# Vigilante de precios y promociones — Be Casa San Sebastián de los Reyes

**Fecha:** 2026-09-10
**Estado:** diseño aprobado pendiente de revisión del usuario

## Contexto y objetivo

El usuario **ya reside** en Be Casa San Sebastián de los Reyes (Av. de los Pirineos, 33),
paga aproximadamente 1.000 €/mes por un estudio sin terraza y **renueva contrato en unos
meses**. El objetivo real no es encontrar piso: es **pagar menos en la renovación**.

De ahí que el sistema tenga dos misiones, y la segunda importe tanto como la primera:

1. **Vigilar el precio** de todas las tipologías del edificio y avisar cuando alguna baje
   de 960 €/mes.
2. **Vigilar las promociones** publicadas por Be Casa, porque sus bases legales admiten
   expresamente a residentes que renuevan.

### Hallazgos de la investigación previa

Estos hechos están verificados contra la web real y condicionan todo el diseño:

- **El precio de escaparate miente.** La ficha comercial anuncia el estudio con terraza
  «desde 1.123 €», pero el motor de reservas lo da a **921 €/mes**. La web de marketing va
  desactualizada respecto al buscador. Vigilar solo la ficha comercial daría datos falsos.
- **El motor de reservas es un Next.js sobre GraphQL (Lavanda).** Sirve las tarifas ya
  estructuradas dentro del HTML, en el payload de React Server Components:
  `{"__typename":"Rates","rateAmountCents":92100,"interval":"calendar_monthly","minStay":61}`.
  Se lee con HTTP plano. **No hace falta Playwright ni navegador headless.**
- **Estado actual del edificio** (10 tipologías, 4 reservables):

  | ID | Unidad | Precio real |
  |---|---|---|
  | 1328 | Estudio adaptado | 921 €/mes |
  | 1329 | Estudio con terraza | 921 €/mes |
  | 1322 | Apto. 2 dorm. con terraza | 1.543 €/mes |
  | 1323 | Apto. 2 dorm. terraza + twin | 1.603 €/mes |
  | 1330, 1331, 1332, 1333, 1607, 13077 | «Próximamente» | 404 (no reservables) |

- **Tarifas por duración de estancia** (de `becasaPageContext` en la ficha comercial):
  10-12 meses → 893 €/mes · 7-9 meses → 1.024 € · 2-6 meses → 1.111 €.
- **No existen códigos de cupón públicos.** El campo `couponCode` de la API es
  funcionalidad genérica de Lavanda. Be Casa aplica sus descuentos firmando un **anexo al
  contrato**, no introduciendo un código en la web.
- **Las promociones se publican como PDF** en `cmseditor.becasaapartments.com/wp-content/uploads/AAAA/MM/`,
  con bases legales completas. Y sus condiciones dicen literalmente que pueden acogerse
  «residentes que ya vivan en Be Casa San Sebastián de los Reyes y que **renueven su
  contrato**». Campañas observadas: 50% de descuento en la primera mensualidad (estancia
  4-9 meses) o en las dos primeras (10-12 meses); y en otra campaña, 10% sobre la renta
  mensual para estudios con estancia superior a 10 meses.

### Fuera de alcance, deliberadamente

**No se construirá un probador automático de códigos promocionales.** Enumerar códigos
contra la API de un tercero es tráfico abusivo, y además aquí no encontraría nada porque
Be Casa no usa cupones. El equivalente legítimo y más útil es vigilar el CMS de promociones,
que sí está en alcance.

## Arquitectura

```
GitHub Actions (cron cada 30 min)
  └─ python -m becasa.watch
      ├─ Fuente A · ficha comercial      → tarifas por duración + banners de promo
      ├─ Fuente B · motor de reservas    → tarifa exacta por unidad + disponibilidad
      ├─ Fuente C · CMS de promociones   → PDFs nuevos de campañas
      ├─ diff contra state/latest.json
      ├─ append a history/AAAA-MM.jsonl
      ├─ dispara avisos por email (SMTP)
      └─ regenera docs/data.json
  └─ commit + push  →  GitHub Pages sirve docs/
```

Repositorio **público** (necesario para que Pages sea gratuito). Ningún dato personal vive
en el repo: el destinatario del correo y las credenciales SMTP van en *Secrets* de Actions,
que son privados aunque el repositorio no lo sea.

## Componentes

Cada módulo tiene una responsabilidad y es testeable sin red: las funciones de parseo
reciben texto, no URLs.

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `becasa/fetch.py` | HTTP con reintentos, cabeceras y backoff | stdlib |
| `becasa/booking.py` | Decodifica el payload Next.js → `Unit(id, nombre, precio, min_stay, estado)` | — |
| `becasa/marketing.py` | Extrae `becasaPageContext` y banners de promo | — |
| `becasa/promos.py` | Descubre PDFs nuevos en el CMS y extrae su texto | `pypdf` |
| `becasa/diff.py` | Compara snapshots y decide qué merece aviso | — |
| `becasa/notify.py` | Compone y envía el correo | stdlib `smtplib` |
| `becasa/watch.py` | Orquesta; único módulo que toca red y disco | todos |
| `docs/` | Panel estático | — |

Única dependencia externa: `pypdf`, para leer los PDFs de promociones.

## Configuración

`config.json` en la raíz, editable desde la web de GitHub:

```json
{
  "edificio": "san-sebastian-reyes",
  "umbral_eur": 960,
  "renta_actual_eur": 1000,
  "estancia_dias": 365,
  "vigilar_tipos": "todos",
  "avisar_por_debajo_del_umbral": true,
  "avisar_bajada_de_precio": true,
  "avisar_unidad_nueva": true,
  "avisar_promocion_nueva": true
}
```

`estancia_dias` (por defecto **365**) selecciona el tramo de tarifa por duración
correspondiente y se registra en cada snapshot, de modo que el histórico siempre indica a
qué duración se refiere el precio guardado.

`renta_actual_eur` es lo que paga hoy el usuario. No afecta a los avisos: alimenta la línea
de referencia del panel, para ver de un vistazo cuánto se paga de más frente a un
inquilino nuevo.

## Modelo de datos

Un snapshot por ejecución, añadido a `history/AAAA-MM.jsonl` (append-only, una línea por
snapshot, fácil de versionar en git):

```json
{
  "ts": "2026-09-10T09:00:00Z",
  "estancia_dias": 365,
  "unidades": [
    {"id": "1329", "nombre": "Estudio con terraza", "eur_mes": 921.0,
     "min_stay_dias": 61, "estado": "reservable"}
  ],
  "tramos_duracion": {"m10_12": 893, "m7_9": 1024, "m2_6": 1111},
  "promos_web": ["Ahorra hasta 248 €/mes"],
  "promos_cms": [{"url": "...", "publicado": "2026-03", "menciona_edificio": true}]
}
```

`state/latest.json` guarda el último snapshot correcto, para comparar y para no
sobrescribir datos buenos cuando una ejecución falla.

## Avisos

Se envía correo cuando **cambia el estado**, nunca en cada ejecución. Cuatro disparadores,
todos desactivables desde `config.json`:

1. Cualquier unidad por debajo de `umbral_eur`.
2. Cualquier bajada de precio, aunque siga por encima del umbral.
3. Una unidad que pasa de 404 a reservable (las de «Próximamente»).
4. Un PDF de promoción nuevo en el CMS, marcando si menciona el edificio del usuario.

El correo incluye siempre el precio anterior junto al nuevo, y el enlace directo a la
unidad, para poder actuar sin abrir el panel.

## Panel

`docs/index.html`, estático, sin dependencias de red salvo la librería de gráficos, con
`data.json` generado por el workflow:

- Tabla del estado actual: unidad, precio, mínimo de estancia, disponibilidad, variación
  frente al snapshot anterior.
- **Gráfico de evolución por tipología**, una serie por unidad, con una línea horizontal
  de referencia en `renta_actual_eur` y otra en `umbral_eur`.
- Panel de promociones detectadas, con enlace al PDF y las fechas de vigencia.
- Marca de tiempo de la última comprobación correcta, para saber si el bot está vivo.

## Manejo de errores

El modo de fallo peligroso es que el scraper se rompa en silencio y el usuario crea que no
hay noticias cuando en realidad está ciego. Por tanto:

- Fallo de red o de parseo → se conserva `state/latest.json`; no se escribe un snapshot
  corrupto ni se dispara ningún aviso.
- Un 404 en una unidad «Próximamente» es un estado esperado, no un error.
- Tres ejecuciones consecutivas fallidas → correo de alerta «el vigilante está ciego».
- El workflow solo hace commit si hay cambios reales, para no ensuciar el historial.

## Pruebas

- Fixtures: los HTML ya descargados (ficha comercial, página de unidad reservable, página
  404) se guardan en `tests/fixtures/`. Los tests de parseo corren sin red y detectan el
  día que Be Casa cambie el formato.
- Tests del comparador: cruce de umbral, bajada, subida, unidad que aparece, unidad que
  desaparece, y ausencia de aviso cuando nada cambia.
- `--dry-run` imprime el correo por consola en lugar de enviarlo.

## Frecuencia y coste

Cron cada 30 minutos. GitHub retrasa los cron en horas punta, así que la cadencia real
ronda los 30-60 minutos, suficiente de sobra para un precio de alquiler. En repositorio
público los minutos de Actions son gratuitos e ilimitados.

## Secrets requeridos

`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_TO`.

> Si se usa una contraseña de aplicación de Gmail, hay que **pegarla sin espacios**.

## Decisión pendiente

**Consulta directa a la API GraphQL de Lavanda.** El endpoint
(`https://api.lavanda.app/api/graphql`, cabecera
`X-Hanami-Direct-Bookings-Site-Code: a6180e15-8715-495f-9039-6264c8041901`, sin API key)
permitiría pedir `PropertyBookingSummary` con `checkIn`/`checkOut` reales y obtener el
**precio exacto para las fechas del usuario**, en lugar de la tarifa base publicada.

El clasificador de seguridad del entorno bloqueó esta llamada durante la investigación. El
diseño actual **no depende de ella**: funciona con la tarifa base, que ya es el dato bueno
(921 €/mes). Si el usuario autoriza la llamada, se añade como refinamiento en una fase
posterior, con una consulta por ejecución para no generar carga innecesaria.
