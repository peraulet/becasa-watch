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
- **Hay una API GraphQL pública y sin autenticación.** El motor de reservas es un Next.js
  sobre Lavanda. La API acepta consultas anónimas con solo una cabecera de sitio:

  ```
  POST https://api.lavanda.app/api/graphql
  X-Hanami-Direct-Bookings-Site-Code: a6180e15-8715-495f-9039-6264c8041901

  query($id:Int!,$site:String!,$in:ISO8601Date!,$out:ISO8601Date!,$coupon:String){
    property(id:$id, siteCode:$site, checkIn:$in, checkOut:$out,
             numberOfGuests:1, locale:"es", couponCode:$coupon){
      title available currency cleaningFee
      rates { rateAmountCents interval minStay maxStay }
      couponDiscount { valid code amount rejectionReason }
    }
  }
  ```

  **No hace falta Playwright ni navegador headless.** La introspección está abierta, así
  que el esquema es verificable sin adivinar.

- **Estado del edificio verificado por API el 2026-09-10** (10 tipologías, 4 reservables):

  | ID | Unidad | `calendar_monthly` | €/mes |
  |---|---|---|---|
  | 1328 | Estudio adaptado | 92100 | **921** |
  | 1329 | Estudio con terraza | 92100 | **921** |
  | 1322 | Apto. 2 dorm. con terraza | 154300 | 1.543 |
  | 1323 | Apto. 2 dorm. terraza + twin | 160300 | 1.603 |
  | 1330, 1331, 1332, 1333, 1607, 13077 | «Próximamente» | — | no existen como unidad reservable |

  Todas con `available: true`, `minStay: 61`, `maxStay: 362`. Estas cifras coinciden con
  las extraídas del HTML por una vía independiente, de modo que ambas fuentes se validan
  entre sí. El bot usará la API como fuente primaria y el HTML como control cruzado: una
  discrepancia entre ambas es señal de que algo ha cambiado y merece revisión.

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
| `becasa/api.py` | Cliente GraphQL de Lavanda → `Unit(id, nombre, eur_mes, min_stay, max_stay, disponible, limpieza, fianza)` | — |
| `becasa/booking.py` | Decodifica el payload Next.js del HTML; control cruzado de `api.py` | — |
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
  "estancia_dias": 335,
  "vigilar_tipos": "todos",
  "avisar_por_debajo_del_umbral": true,
  "avisar_bajada_de_precio": true,
  "avisar_unidad_nueva": true,
  "avisar_promocion_nueva": true
}
```

`estancia_dias` (por defecto **335**, once meses) fija la ventana `checkIn`/`checkOut` de
la consulta y se registra en cada snapshot, de modo que el histórico siempre indica a qué
duración se refiere el precio guardado. **Se valida contra el rango 61-362**: fuera de él
la API no devuelve tarifa mensual, así que un valor inválido en `config.json` debe fallar
de forma ruidosa al arrancar, nunca degradarse en silencio a la tarifa por noche.

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

## Limitaciones conocidas

Se documentan aquí para que nadie las descubra a medias dentro de seis meses.

1. **No hay cotización en vivo para fechas concretas.** El campo `accommodationFare` de la
   API devuelve siempre la tarifa por noche (100 €/noche), no la mensual, con
   independencia de la duración solicitada. No se ha identificado qué parámetro activa el
   cálculo mensual; se sospecha del contexto multi-unidad (`mu=1`), sin confirmar.

   **Es irrelevante para el objetivo**: el array `rates` de esa misma respuesta sí trae la
   tarifa `calendar_monthly` autoritativa, que es el dato que el bot necesita. Se lee
   `rates`, no `accommodationFare`.

2. **La tarifa mensual solo aparece si la estancia consultada cae entre 61 y 362 noches.**
   Fuera de ese rango, `rates` solo devuelve la tarifa por noche. Por eso `estancia_dias`
   se limita a ese intervalo.

3. **Un año natural completo no es contratable.** El `maxStay` de 362 noches lo impide. Un
   contrato de 365 días requiere hablar con el comercial, no pasa por el motor de reservas.

4. **Los seis tipos «Próximamente» no existen todavía como unidad reservable.** La API
   responde `Couldn't find Spaces::MultiUnitGroup`. El bot trata esa respuesta como estado
   esperado, y su desaparición es precisamente el disparador de «unidad nueva disponible».

## Validación de códigos promocionales

El tipo `StayCouponDiscount` expone `valid`, `code`, `amount` y `rejectionReason`, y el
argumento `couponCode` se puede pasar a `property`. Esto permite **comprobar si un código
concreto sigue vigente y cuánto descuenta**, sin simular una reserva.

Se implementa como comando manual (`python -m becasa.cupon CODIGO`), para códigos que el
usuario reciba por email, boletín o convenio (por ejemplo, el acuerdo de AICA con Be Casa).

**No se implementará enumeración de códigos.** Probar códigos a ciegas contra la API de un
tercero es tráfico abusivo, y además sería inútil: Be Casa no usa cupones públicos.
