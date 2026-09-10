"""Generacion del panel estatico.

Escribe docs/data.json y docs/index.html. El HTML es autocontenido salvo las
tipografias: sin librerias, sin peticiones a la hora de verlo.

La idea de la pagina: los precios no se leen solos, se leen contra dos rectas
-- lo que pagas hoy y el umbral que te has puesto. Por eso ambas son el
esqueleto del grafico y no una anotacion al margen.
"""
import json
import pathlib

TITULO = 'Vigía Be Casa'

CSS = """
:root{
  --ground:#F5F6F4; --surface:#FFFFFF; --sunken:#ECEEEA;
  --ink:#181C1A; --ink-2:#48524D; --muted:#77817C; --line:#DDE1DC;
  --accent:#1F5F4B; --accent-soft:#DCE9E2;
  --alert:#A8402C; --alert-soft:#F3E1DC;
  --shadow:0 1px 2px rgba(24,28,26,.06), 0 8px 24px -16px rgba(24,28,26,.25);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#101312; --surface:#181C1A; --sunken:#1F2422;
    --ink:#ECEFEC; --ink-2:#B3BCB7; --muted:#8A948F; --line:#2C3230;
    --accent:#63B394; --accent-soft:#1B2E27;
    --alert:#E08A72; --alert-soft:#33211C;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"]{
  --ground:#101312; --surface:#181C1A; --sunken:#1F2422;
  --ink:#ECEFEC; --ink-2:#B3BCB7; --muted:#8A948F; --line:#2C3230;
  --accent:#63B394; --accent-soft:#1B2E27;
  --alert:#E08A72; --alert-soft:#33211C;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;
  font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:themax; margin:0 auto; padding:40px 24px 72px;
  display:flex; flex-direction:column; gap:34px}
@media(max-width:640px){ .wrap{padding:26px 16px 56px; gap:26px} }

h1,h2,h3{font-family:Newsreader,Georgia,"Times New Roman",serif; font-weight:500;
  text-wrap:balance; margin:0; letter-spacing:-.01em}
h1{font-size:clamp(30px,5vw,42px); line-height:1.1}
h2{font-size:20px}
.eyebrow{font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); font-weight:600}
.num{font-family:"IBM Plex Mono",ui-monospace,monospace; font-variant-numeric:tabular-nums}
p{margin:0}
a{color:var(--accent)}

header{display:flex; flex-direction:column; gap:8px;
  border-bottom:1px solid var(--line); padding-bottom:22px}
header .sub{color:var(--ink-2); max-width:62ch}

/* --- veredicto ------------------------------------------------------- */
.verdict{display:grid; gap:1px; background:var(--line);
  grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  border:1px solid var(--line); border-radius:3px; overflow:hidden}
.cell{background:var(--surface); padding:18px 20px;
  display:flex; flex-direction:column; gap:5px}
.cell .big{font-size:29px; line-height:1.1; font-weight:600}
.cell .foot{font-size:12.5px; color:var(--muted)}
.good{color:var(--accent)} .bad{color:var(--alert)}

/* --- bloques --------------------------------------------------------- */
.block{background:var(--surface); border:1px solid var(--line); border-radius:3px;
  padding:24px; display:flex; flex-direction:column; gap:16px; box-shadow:var(--shadow)}
.block > .head{display:flex; flex-direction:column; gap:3px}
.block .note{font-size:13px; color:var(--muted); max-width:70ch}
.scroll{overflow-x:auto}

/* --- tabla ----------------------------------------------------------- */
table{border-collapse:collapse; width:100%; font-size:14px; min-width:520px}
th{text-align:left; font-size:11px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--muted); font-weight:600; padding:0 12px 9px 0;
  border-bottom:1px solid var(--line); white-space:nowrap}
td{padding:11px 12px 11px 0; border-bottom:1px solid var(--line); vertical-align:baseline}
tr:last-child td{border-bottom:none}
td.r,th.r{text-align:right; padding-right:0}
.pill{display:inline-flex; align-items:center; gap:6px; font-size:11.5px;
  padding:2px 9px; border-radius:2px; font-weight:600; white-space:nowrap}
.pill.ok{background:var(--accent-soft); color:var(--accent)}
.pill.no{background:var(--sunken); color:var(--muted)}
.pill.hot{background:var(--alert-soft); color:var(--alert)}

/* --- graficos -------------------------------------------------------- */
svg{display:block; width:100%; height:auto}
svg text{font-family:"IBM Plex Mono",ui-monospace,monospace; font-variant-numeric:tabular-nums}
.bar{transition:opacity .12s}
.bar:hover{opacity:.78}

.btn{display:inline-flex; align-items:center; gap:8px; align-self:flex-start;
  background:var(--accent); color:var(--surface); text-decoration:none;
  padding:11px 18px; border-radius:3px; font-weight:600; font-size:14px;
  border:1px solid var(--accent)}
.btn:hover{opacity:.9}
.btn:focus-visible{outline:2px solid var(--ink); outline-offset:2px}

/* --- promos ---------------------------------------------------------- */
.promos{display:flex; flex-direction:column; gap:11px}
.promo{display:flex; gap:12px; align-items:baseline; padding:12px 14px;
  background:var(--sunken); border-radius:3px; border-left:2px solid var(--line)}
.promo.mine{border-left-color:var(--accent); background:var(--accent-soft)}
.promo .txt{flex:1; min-width:0}
footer{color:var(--muted); font-size:13px; border-top:1px solid var(--line);
  padding-top:20px; display:flex; flex-direction:column; gap:8px}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
""".replace('themax', '980px')

FUENTES = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
           '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
           'family=Newsreader:opsz,wght@6..72,400;6..72,500&'
           'family=IBM+Plex+Mono:wght@400;600&'
           'family=IBM+Plex+Sans:wght@400;500;600&display=swap">')


def _esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _eur(v, dec=0):
    if v is None:
        return '—'
    return f'{v:,.{dec}f}'.replace(',', ' ')


# --------------------------------------------------------------------------
# grafico de barras: precio actual de cada unidad contra tus dos rectas
# --------------------------------------------------------------------------
def _barras(unidades, renta, umbral):
    if not unidades:
        return '<p class="note">Todavía no hay unidades reservables.</p>'

    W, FILA, TOP, BOT = 720, 42, 26, 34
    IZQ, DER = 226, 74
    H = TOP + FILA * len(unidades) + BOT
    ancho = W - IZQ - DER
    tope = max([u['eur_mes'] for u in unidades] + [renta or 0, umbral or 0]) * 1.12
    x = lambda v: IZQ + (v / tope) * ancho                        # noqa: E731

    p = [f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Precio mensual de cada tipología frente a tu renta y tu umbral">']

    # reglas de referencia: la espina de la lectura
    for val, etiqueta, color, guion in (
            (umbral, 'umbral', 'var(--accent)', '4 3'),
            (renta, 'tu renta', 'var(--alert)', None)):
        if not val:
            continue
        xv = x(val)
        p.append(f'<line x1="{xv:.1f}" y1="{TOP - 12}" x2="{xv:.1f}" y2="{H - BOT + 6}" '
                 f'stroke="{color}" stroke-width="1.5"'
                 + (f' stroke-dasharray="{guion}"' if guion else '') + '/>')
        p.append(f'<text x="{xv:.1f}" y="{TOP - 17}" fill="{color}" font-size="11.5" '
                 f'font-weight="600" text-anchor="middle">{etiqueta} '
                 f'{_eur(val)} €</text>')

    for i, u in enumerate(unidades):
        y = TOP + i * FILA
        yb = y + 9
        bajo = umbral and u['eur_mes'] < umbral
        color = 'var(--accent)' if bajo else 'var(--ink-2)'
        nombre = _esc((u.get('nombre') or u['id'])[:30])
        p.append(f'<text x="{IZQ - 14}" y="{yb + 13}" fill="var(--ink)" font-size="12.5" '
                 f'text-anchor="end" font-family="IBM Plex Sans,sans-serif">{nombre}</text>')
        p.append(f'<rect class="bar" x="{IZQ}" y="{yb}" width="{max(x(u["eur_mes"]) - IZQ, 2):.1f}" '
                 f'height="18" rx="4" fill="{color}">'
                 f'<title>{nombre}: {_eur(u["eur_mes"])} €/mes</title></rect>')
        p.append(f'<text x="{x(u["eur_mes"]) + 9:.1f}" y="{yb + 13}" fill="var(--ink)" '
                 f'font-size="12.5" font-weight="600">{_eur(u["eur_mes"])}</text>')

    p.append(f'<line x1="{IZQ}" y1="{H - BOT + 6}" x2="{W - DER}" y2="{H - BOT + 6}" '
             f'stroke="var(--line)" stroke-width="1"/>')
    p.append(f'<text x="{IZQ}" y="{H - BOT + 24}" fill="var(--muted)" font-size="11">'
             f'€/mes</text>')
    p.append('</svg>')
    return ''.join(p)


# --------------------------------------------------------------------------
# evolucion temporal: solo tiene sentido con dos o mas lecturas
# --------------------------------------------------------------------------
def _evolucion(hist, renta, umbral):
    series, sellos = {}, []
    for snap in hist:
        sellos.append(snap['ts'])
        for u in snap.get('unidades', []):
            if u.get('eur_mes'):
                series.setdefault(u['id'], {'nombre': u.get('nombre') or u['id'],
                                            'puntos': []})
                series[u['id']]['puntos'].append((snap['ts'], u['eur_mes']))

    if len(sellos) < 2:
        return ('<p class="note">El gráfico de evolución aparecerá en cuanto haya dos '
                'lecturas. Cada ejecución añade un punto; a partir de ahí verás si los '
                'precios se mueven y en qué dirección.</p>')

    W, H = 720, 300
    IZQ, DER, TOP, BOT = 56, 130, 20, 34
    vals = [v for s in series.values() for _, v in s['puntos']]
    lo = min(vals + [umbral or min(vals), renta or min(vals)]) * .96
    hi = max(vals + [umbral or max(vals), renta or max(vals)]) * 1.04
    orden = {t: i for i, t in enumerate(sorted(set(sellos)))}
    n = max(len(orden) - 1, 1)
    x = lambda t: IZQ + orden[t] / n * (W - IZQ - DER)             # noqa: E731
    y = lambda v: TOP + (hi - v) / (hi - lo) * (H - TOP - BOT)     # noqa: E731

    p = [f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Evolución del precio mensual por tipología">']
    for val in (lo, (lo + hi) / 2, hi):
        p.append(f'<line x1="{IZQ}" y1="{y(val):.1f}" x2="{W - DER}" y2="{y(val):.1f}" '
                 f'stroke="var(--line)" stroke-width="1"/>')
        p.append(f'<text x="{IZQ - 9}" y="{y(val) + 4:.1f}" fill="var(--muted)" '
                 f'font-size="11" text-anchor="end">{_eur(val)}</text>')
    for val, color in ((umbral, 'var(--accent)'), (renta, 'var(--alert)')):
        if val and lo <= val <= hi:
            p.append(f'<line x1="{IZQ}" y1="{y(val):.1f}" x2="{W - DER}" y2="{y(val):.1f}" '
                     f'stroke="{color}" stroke-width="1.5" stroke-dasharray="4 3"/>')

    for s in series.values():
        pts = sorted(s['puntos'], key=lambda t: t[0])
        d = ' '.join(f'{x(t):.1f},{y(v):.1f}' for t, v in pts)
        p.append(f'<polyline points="{d}" fill="none" stroke="var(--accent)" '
                 f'stroke-width="2" stroke-linejoin="round"/>')
        for t, v in pts:
            p.append(f'<circle cx="{x(t):.1f}" cy="{y(v):.1f}" r="3.5" '
                     f'fill="var(--accent)" stroke="var(--surface)" stroke-width="2">'
                     f'<title>{_esc(s["nombre"])} · {t[:10]}: {_eur(v)} €/mes</title></circle>')
        tf, vf = pts[-1]
        p.append(f'<text x="{x(tf) + 10:.1f}" y="{y(vf) + 4:.1f}" fill="var(--ink)" '
                 f'font-size="11.5" font-family="IBM Plex Sans,sans-serif">'
                 f'{_esc(s["nombre"][:16])}</text>')

    p.append('</svg>')
    return ''.join(p)


# --------------------------------------------------------------------------
def generar(docs: pathlib.Path, snap, hist, cfg):
    docs.mkdir(parents=True, exist_ok=True)
    d = snap.dict() if hasattr(snap, 'dict') else snap
    renta = cfg.get('renta_actual_eur')
    umbral = cfg.get('umbral_eur')

    (docs / 'data.json').write_text(
        json.dumps({'actual': d, 'historia': hist, 'config': cfg},
                   ensure_ascii=False, indent=2), encoding='utf-8')

    reservables = sorted([u for u in d['unidades']
                          if u.get('estado') == 'reservable' and u.get('eur_mes')],
                         key=lambda u: u['eur_mes'])
    barato = reservables[0] if reservables else None
    bajo_umbral = [u for u in reservables if umbral and u['eur_mes'] < umbral]
    ahorro = (renta - barato['eur_mes']) if (renta and barato) else None

    # --- veredicto
    celdas = []
    if barato:
        celdas.append(
            f'<div class="cell"><span class="eyebrow">Más barato ahora</span>'
            f'<span class="big num {"good" if bajo_umbral else ""}">'
            f'{_eur(barato["eur_mes"])} €</span>'
            f'<span class="foot">{_esc(barato.get("nombre") or barato["id"])}</span></div>')
    if ahorro is not None:
        signo = 'good' if ahorro > 0 else 'bad'
        verbo = 'menos que tu renta' if ahorro > 0 else 'más que tu renta'
        celdas.append(
            f'<div class="cell"><span class="eyebrow">Diferencia mensual</span>'
            f'<span class="big num {signo}">{"−" if ahorro > 0 else "+"}'
            f'{_eur(abs(ahorro))} €</span>'
            f'<span class="foot">{verbo} de {_eur(renta)} € · '
            f'{_eur(abs(ahorro) * 12)} € al año</span></div>')
    celdas.append(
        f'<div class="cell"><span class="eyebrow">Bajo tu umbral</span>'
        f'<span class="big num {"good" if bajo_umbral else "bad"}">{len(bajo_umbral)}'
        f'<span style="font-size:16px;color:var(--muted)"> de {len(reservables)}</span></span>'
        f'<span class="foot">umbral de {_eur(umbral)} €/mes</span></div>')

    # --- tabla
    filas = []
    for u in sorted(d['unidades'], key=lambda u: (u.get('eur_mes') is None,
                                                  u.get('eur_mes') or 0)):
        if u.get('estado') == 'reservable' and u.get('eur_mes'):
            if umbral and u['eur_mes'] < umbral:
                pill = '<span class="pill ok">bajo umbral</span>'
            elif renta and u['eur_mes'] < renta:
                pill = '<span class="pill ok">menos que pagas</span>'
            else:
                pill = '<span class="pill hot">por encima</span>'
            precio = f'{_eur(u["eur_mes"])} €'
            estancia = (f'{u.get("min_stay_dias") or "—"}–{u.get("max_stay_dias") or "—"}'
                        if u.get('min_stay_dias') else '—')
        else:
            pill = '<span class="pill no">próximamente</span>'
            precio, estancia = '—', '—'
        origen = ('<span class="pill no" title="Precio anunciado en la ficha comercial, '
                  'no cotizado por el motor de reservas">ficha</span>'
                  if u.get('fuente') == 'ficha' else
                  '<span class="pill no" title="Tarifa del motor de reservas">motor</span>')
        nombre = _esc(u.get('nombre') or 'Unidad ' + u['id'])
        if not u['id'].startswith('ficha:'):
            nombre = (f'<a href="https://book.becasaapartments.com/es/properties/'
                      f'{u["id"]}?mu=1">{nombre}</a>')
        filas.append(
            f'<tr><td>{nombre}</td>'
            f'<td class="r num">{precio}</td>'
            f'<td class="r num">{estancia}</td>'
            f'<td class="r">{origen}</td>'
            f'<td class="r">{pill}</td></tr>')

    # --- promociones
    promos = []
    for p in d.get('promos_cms', []):
        marcas = []
        if p.get('admite_renovaciones'):
            marcas.append('admite renovaciones')
        if p.get('descuentos_pct'):
            marcas.append(f'hasta {max(p["descuentos_pct"])}% dto')
        if p.get('mes_gratis'):
            marcas.append('mes gratis')
        mio = ' mine' if p.get('menciona_edificio') else ''
        promos.append(
            f'<div class="promo{mio}"><div class="txt">'
            f'<a href="{_esc(p.get("url", "#"))}">'
            f'{_esc(p.get("titulo") or "Campaña sin título")}</a>'
            + (f'<div class="foot num" style="font-size:12.5px;color:var(--muted)">'
               f'{" · ".join(marcas)}</div>' if marcas else '')
            + '</div></div>')
    for b in d.get('promos_web', []):
        promos.append(f'<div class="promo"><div class="txt">{_esc(b)}</div></div>')
    if not promos:
        promos.append('<p class="note">Ninguna campaña detectada en esta lectura.</p>')

    tramos = d.get('tramos_duracion') or {}
    ETQ = {'m10_12': '10–12 meses', 'm7_9': '7–9 meses', 'm4_6': '4–6 meses',
           'm2_3': '2–3 meses', 'none': 'sin definir'}
    tramos_html = ''.join(
        f'<tr><td>{ETQ.get(k, k)}</td><td class="r num">{_eur(v)} €</td></tr>'
        for k, v in sorted(tramos.items(), key=lambda kv: kv[1]) if k != 'none')

    ci = d.get('check_in') or ''
    co = d.get('check_out') or ''
    html = f'''<title>{TITULO}</title>{FUENTES}<style>{CSS}</style>
<div class="wrap">
<header>
  <span class="eyebrow">Be Casa · San Sebastián de los Reyes</span>
  <h1>Lo que cuesta hoy tu edificio</h1>
  <p class="sub">Tarifas del motor de reservas, más las tipologías que solo existen
     en la ficha comercial — el estudio básico entre ellas. Cada fila indica de dónde
     sale su precio. Última lectura
     <span class="num">{_esc(d["ts"][:16].replace("T", " "))}</span> UTC,
     para una estancia de <span class="num">{d.get("estancia_dias")}</span> noches.</p>
</header>

<div class="verdict">{''.join(celdas)}</div>

<section class="block">
  <div class="head"><h2>Verlo en su web</h2>
    <p class="note">Estas tarifas no se muestran en la ficha de cada alojamiento:
       la web solo las calcula al buscar con fechas de estancia larga. Este enlace
       abre su buscador con el mismo periodo que usa el panel
       (<span class="num">{ci}</span> a <span class="num">{co}</span>), que es
       donde aparecen escritas.</p></div>
  <a class="btn" href="https://book.becasaapartments.com/es/search?checkIn={ci}&amp;checkOut={co}">
     Abrir el buscador con estas fechas →</a>
</section>

<section class="block">
  <div class="head"><h2>Precio frente a tus dos líneas</h2>
    <p class="note">Cada barra es una tipología. Las dos verticales son lo que pagas hoy
       y el umbral que te has fijado: la lectura útil es de qué lado cae cada barra.</p></div>
  <div class="scroll">{_barras(reservables, renta, umbral)}</div>
</section>

<section class="block">
  <div class="head"><h2>Evolución</h2></div>
  <div class="scroll">{_evolucion(hist, renta, umbral)}</div>
</section>

<section class="block">
  <div class="head"><h2>Todas las tipologías</h2>
    <p class="note">Dos procedencias, y <strong>no son equiparables sin más</strong>.
       «Motor» es la tarifa de alojamiento que cotiza el buscador de reservas.
       «Ficha» es el precio anunciado en la web comercial, presentado como coste
       total: puede incluir servicios que la otra cifra no lleva. Compara dentro
       de la misma columna, no entre columnas.</p></div>
  <div class="scroll"><table>
    <thead><tr><th>Tipología</th><th class="r">€/mes</th>
      <th class="r">Estancia (noches)</th><th class="r">Fuente</th>
      <th class="r">Estado</th></tr></thead>
    <tbody>{''.join(filas)}</tbody>
  </table></div>
</section>

{'<section class="block"><div class="head"><h2>Tarifa según duración</h2>'
 '<p class="note">Publicado en la ficha comercial. Firmar más meses baja el precio.</p></div>'
 '<div class="scroll"><table><tbody>' + tramos_html + '</tbody></table></div></section>'
 if tramos_html else ''}

<section class="block">
  <div class="head"><h2>Campañas detectadas</h2>
    <p class="note">Be Casa no usa códigos de cupón: publica cada campaña como PDF con
       bases legales. Las marcadas en verde mencionan tu edificio.</p></div>
  <div class="promos">{''.join(promos)}</div>
</section>

<footer>
  <p><strong>Al renovar, comprueba la cláusula de renovaciones.</strong> Algunas campañas
     admiten expresamente a «residentes que ya vivan en Be Casa San Sebastián de los Reyes
     y que renueven su contrato»; otras no la mencionan. Depende de la campaña, así que hay
     que leer las bases de la vigente. El panel marca arriba cuáles la incluyen.</p>
  <p>Un año natural completo no es contratable por su motor: el máximo son 362 noches.</p>
</footer>
</div>'''

    (docs / 'index.html').write_text(html, encoding='utf-8')
    return docs / 'index.html'
