"""Orquestador: la unica pieza que toca red y disco.

    python -m becasa.watch [--dry-run] [--fuente api|html] [--sin-promos]
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

from . import (api, booking, buscador, diff, fetch, marketing, notify, panel,
               promos)
from .models import Snapshot, Unit

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONFIG = RAIZ / 'config.json'
ESTADO = RAIZ / 'state' / 'latest.json'
FALLOS = RAIZ / 'state' / 'fallos.json'
HISTORIA = RAIZ / 'history'
DOCS = RAIZ / 'docs'

EDIFICIO_NOMBRE = 'San Sebastián de los Reyes'


def cargar_config():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    dias = cfg.get('estancia_dias', 335)
    if not api.MIN_NOCHES <= dias <= api.MAX_NOCHES:
        raise SystemExit(
            f'config.json: estancia_dias={dias} esta fuera de '
            f'[{api.MIN_NOCHES}, {api.MAX_NOCHES}]. Fuera de ese rango la API no '
            'devuelve tarifa mensual y el precio saldria mal. Corrigelo.')
    return cfg


def cargar_estado():
    if not ESTADO.exists():
        return None
    d = json.loads(ESTADO.read_text(encoding='utf-8'))
    d['unidades'] = [Unit(**u) for u in d.get('unidades', [])]
    return Snapshot(**d)


def guardar(snap: Snapshot):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(snap.dict(), ensure_ascii=False, indent=2),
                      encoding='utf-8')
    HISTORIA.mkdir(parents=True, exist_ok=True)
    mes = snap.ts[:7]
    with (HISTORIA / f'{mes}.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(snap.dict(), ensure_ascii=False) + '\n')


def historia():
    """Todos los snapshots guardados, en orden."""
    out = []
    if HISTORIA.exists():
        for p in sorted(HISTORIA.glob('*.jsonl')):
            for linea in p.read_text(encoding='utf-8').splitlines():
                if linea.strip():
                    try:
                        out.append(json.loads(linea))
                    except ValueError:
                        continue
    return out


def contar_fallo(reset=False):
    FALLOS.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    if FALLOS.exists():
        try:
            n = json.loads(FALLOS.read_text(encoding='utf-8')).get('seguidos', 0)
        except ValueError:
            n = 0
    n = 0 if reset else n + 1
    FALLOS.write_text(json.dumps({'seguidos': n}), encoding='utf-8')
    return n


def recoger_unidades(ids, cfg, fuente):
    """Lee cada unidad, con la API como fuente preferida y el HTML de respaldo."""
    check_in, check_out = api.ventana(cfg['estancia_dias'])
    unidades, errores = [], 0

    for pid in ids:
        u = None
        if fuente in ('api', 'auto'):
            try:
                u = api.unidad(pid, check_in, check_out)
            except fetch.FetchError as e:
                print(f'  api {pid}: {e}', file=sys.stderr)
        if (u is None or u.eur_mes is None) and fuente in ('html', 'auto'):
            try:
                status, html_txt = fetch.get_text(booking.url_unidad(pid))
                alt = booking.parse_unidad(pid, html_txt, status)
                # el HTML solo sustituye a la API si aporta precio
                if alt.eur_mes or u is None:
                    u = alt
            except fetch.FetchError as e:
                print(f'  html {pid}: {e}', file=sys.stderr)
                errores += 1
        unidades.append(u or Unit(id=str(pid), estado='error'))

    return unidades, errores


def ejecutar(dry_run=False, fuente='auto', sin_promos=False):
    cfg = cargar_config()
    previo = cargar_estado()
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    # ficha comercial: tramos por duracion, banners y el censo de unidades
    tramos, banners, ids = {}, [], list(cfg.get('ids', []))
    tarjetas_ficha = []
    try:
        _, html_txt = fetch.get_text(marketing.url_edificio(cfg['edificio']))
        tramos = marketing.tramos_duracion(html_txt)
        banners = marketing.promos(html_txt)
        tarjetas_ficha = marketing.tarjetas(html_txt)
        descubiertos = marketing.ids_unidades(html_txt)
        if descubiertos:
            ids = descubiertos
    except fetch.FetchError as e:
        print(f'ficha comercial: {e}', file=sys.stderr)

    # El censo bueno sale del buscador, no de la ficha: la ficha no enlaza
    # todas las unidades del edificio. El estudio basico, que es el mas
    # barato, no aparece enlazado por ningun lado. Se unen las dos fuentes:
    # el buscador aporta lo reservable y la ficha, los "proximamente".
    try:
        check_in, check_out = api.ventana(cfg['estancia_dias'])
        del_buscador = buscador.descubrir(EDIFICIO_NOMBRE, check_in, check_out)
        if del_buscador:
            ids = sorted(set(ids) | set(del_buscador), key=int)
            print(f'Censo: {len(del_buscador)} del buscador, '
                  f'{len(ids)} en total.')
    except fetch.FetchError as e:
        print(f'buscador: {e}', file=sys.stderr)

    if not ids:
        raise SystemExit('No hay unidades que vigilar: revisa "ids" en config.json')

    unidades, errores = recoger_unidades(ids, cfg, fuente)

    # No todas las tipologias existen en el motor de reservas: el estudio
    # basico se anuncia en la ficha pero su pagina de reserva devuelve 404.
    # Sin esto, la tipologia mas comun del edificio se quedaba sin vigilar.
    ya = {(u.nombre or '').strip().lower() for u in unidades if u.nombre}
    for c in tarjetas_ficha:
        if c['nombre'].strip().lower() in ya:
            continue
        unidades.append(Unit(id=f'ficha:{c["nombre"]}', nombre=c['nombre'],
                             eur_mes=c['eur_mes'], estado='reservable',
                             fuente='ficha'))

    if errores == len(ids):
        n = contar_fallo()
        print(f'Todas las unidades fallaron ({n} ciclos seguidos).', file=sys.stderr)
        if n >= 3 and previo:
            notify.enviar([{'tipo': 'ciego', 'unidad': None, 'antes': None,
                            'texto': f'El vigilante lleva {n} ciclos sin poder leer '
                                     'los precios. Puede que hayan cambiado la web.'}],
                          previo, cfg, dry_run)
        return 1
    contar_fallo(reset=True)

    vistos = {p.get('url') for p in (previo.promos_cms if previo else [])}
    promos_cms = [] if sin_promos else promos.revisar(EDIFICIO_NOMBRE, vistos)
    if previo and not sin_promos:
        # conservamos el historico de campanas ya conocidas
        promos_cms = list(previo.promos_cms) + promos_cms

    ini, fin = api.ventana(cfg['estancia_dias'])
    snap = Snapshot(ts=ahora, estancia_dias=cfg['estancia_dias'],
                    check_in=ini, check_out=fin, unidades=unidades,
                    tramos_duracion=tramos, promos_web=banners, promos_cms=promos_cms)

    avisos = diff.comparar(snap, previo, cfg)
    if avisos:
        notify.enviar(avisos, snap, cfg, dry_run)
    else:
        print('Sin novedades.')

    if not dry_run:
        guardar(snap)
        panel.generar(DOCS, snap, historia(), cfg)
        print(f'Panel regenerado en {DOCS / "index.html"}')

    for u in sorted(snap.reservables(), key=lambda x: x.eur_mes):
        print(f'  {u.eur_mes:>8,.0f} EUR/mes  {u.nombre or u.id}')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description='Vigilante de precios de Be Casa')
    p.add_argument('--dry-run', action='store_true',
                   help='no envia correo ni escribe nada')
    p.add_argument('--fuente', choices=['api', 'html', 'auto'], default='auto')
    p.add_argument('--sin-promos', action='store_true',
                   help='salta la revision del CMS de campanas')
    a = p.parse_args(argv)
    return ejecutar(a.dry_run, a.fuente, a.sin_promos)


if __name__ == '__main__':
    sys.exit(main())
