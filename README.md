# Vigía Be Casa

Vigila el precio de las tipologías de **Be Casa San Sebastián de los Reyes** y las
campañas promocionales que publica la marca, y avisa por correo cuando algo cambia.

Nació de una situación concreta: ser residente, pagar ~1.000 €/mes por un estudio sin
terraza y tener la renovación encima. El objetivo no es mudarse, es **pagar menos**.

## Lo que ya sabe

- El precio de escaparate miente. La ficha comercial anunciaba «desde 1.123 €» para una
  unidad que el motor de reservas daba a **921 €/mes**.
- El motor de reservas corre sobre una **API GraphQL pública** (Lavanda), sin
  autenticación. Se leen las tarifas estructuradas, sin navegador headless.
- **Be Casa no usa códigos de cupón.** Publica cada campaña como PDF con bases legales en
  su CMS y aplica el descuento firmando un anexo. Por eso el bot vigila ese CMS.

## Uso local

```bash
pip install -r requirements.txt
python -m becasa.watch --dry-run          # no envía nada ni escribe nada
python -m becasa.watch                    # ejecución normal
python -m becasa.watch --fuente html      # sin tocar la API
python -m becasa.watch --sin-promos       # salta la revisión de campañas
```

El panel queda en `docs/index.html`.

## Configuración

`config.json`:

| Clave | Qué hace |
|---|---|
| `umbral_eur` | Por debajo de esto, avisa |
| `renta_actual_eur` | Lo que pagas hoy; dibuja la línea de referencia del panel |
| `estancia_dias` | Duración a consultar. **Obligatorio entre 61 y 362** |
| `avisar_*` | Activa o desactiva cada tipo de aviso |

## Desplegar en GitHub (gratis)

1. Crea un repositorio **público** vacío llamado `becasa-watch`.
2. Conéctalo y sube el código:

   ```bash
   git remote add origin https://github.com/TU_USUARIO/becasa-watch.git
   git branch -M main
   git push -u origin main
   ```

3. En *Settings → Secrets and variables → Actions*, añade cinco secretos:
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_TO`.

   > Con una contraseña de aplicación de Gmail, **pégala sin espacios**. El código ya los
   > quita por si acaso, pero es el fallo silencioso clásico.

4. En *Settings → Pages*, elige *Deploy from a branch* → rama `main`, carpeta `/docs`.
   El panel queda en `https://TU_USUARIO.github.io/becasa-watch/`.

Los secretos **no son públicos** aunque el repositorio lo sea: no aparecen en el código,
ni en el historial, ni en los registros de ejecución.

## Trampas ya pagadas

Si algún día hay que tocar el parseo, esto ahorra una tarde:

- `accommodationFare` de la API devuelve **siempre** la tarifa por noche, nunca la
  mensual. Hay que leer `rates` y quedarse con `interval == "calendar_monthly"`.
- Esa tarifa mensual **solo aparece si la estancia consultada cae entre 61 y 362 noches**.
  Fuera de ese rango desaparece del array y el cálculo sale disparatado.
- Para saber si una unidad existe, **no busques «404» en el HTML**: Next.js empaqueta su
  ruta de error en el payload de todas las páginas. El criterio es que haya tarifas.
- Un año natural completo no es contratable: el `maxStay` son 362 noches.

## Pruebas

```bash
python -m pytest -q
```

Los tests corren contra HTML guardado en `tests/fixtures/`, sin red, y avisan el día que
Be Casa cambie el formato de sus páginas.
