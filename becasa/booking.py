"""Lectura de tarifas desde el HTML del motor de reservas.

El motor es un Next.js con App Router: sirve los datos ya resueltos dentro de
la pagina, en los trozos que empuja `self.__next_f.push`. Reconstruirlos da un
JSON plano con las tarifas, sin necesidad de navegador.

Todas las funciones operan sobre texto: no tocan la red.
"""
import json
import re

from .models import Unit

BASE = 'https://book.becasaapartments.com/es/properties/{id}?mu=1'
_MARCA = 'self.__next_f.push([1,'
_DEC = json.JSONDecoder()

_RE_TITULO = re.compile(r'"children":"([^"]{3,80})"\}\],\["\$","meta"')
_RE_RATES = re.compile(r'\{"__typename":"Rates",[^{}]*\}')


def url_unidad(pid):
    return BASE.format(id=pid)


def flight(html):
    """Reconstruye la carga util de React Server Components de la pagina."""
    trozos, i = [], 0
    while True:
        i = html.find(_MARCA, i)
        if i < 0:
            return ''.join(trozos)
        j = i + len(_MARCA)
        try:
            s, _ = _DEC.raw_decode(html, j)
            if isinstance(s, str):
                trozos.append(s)
        except ValueError:
            pass
        i = j


def es_404(payload):
    """Si la pagina es la de "no encontrado".

    No se puede decidir buscando texto suelto en el payload: Next.js empaqueta
    su ruta de error en TODAS las paginas, asi que tanto '404' como la frase
    'could not be found' aparecen tambien en una unidad perfectamente normal.
    Lo que si distingue es el titulo del documento.
    """
    t = titulo(payload) or ''
    return t.startswith('404') or 'could not be found' in t


def tarifas(payload):
    """Devuelve la lista de tarifas crudas encontradas."""
    out = []
    for m in _RE_RATES.finditer(payload):
        try:
            out.append(json.loads(m.group(0)))
        except ValueError:
            continue
    return out


def titulo(payload):
    m = _RE_TITULO.search(payload)
    return m.group(1).strip() if m else None


def mensual(rates):
    """La tarifa mensual, que es la unica que importa para un alquiler largo."""
    for r in rates:
        if r.get('interval') == 'calendar_monthly':
            return r
    return None


def nocturna(rates):
    for r in rates:
        if r.get('interval') == 'nightly':
            return r
    return None


def parse_unidad(pid, html, status=200):
    """HTML de una unidad -> Unit. Funcion pura, apta para tests con fixtures."""
    if status == 404:
        return Unit(id=str(pid), estado='proximamente')

    payload = flight(html)
    rates = tarifas(payload)

    # el criterio de verdad es que haya tarifas; el titulo solo confirma
    if not rates or es_404(payload):
        return Unit(id=str(pid), estado='proximamente')

    mes, noche = mensual(rates), nocturna(rates)
    return Unit(
        id=str(pid),
        nombre=titulo(payload),
        eur_mes=mes['rateAmountCents'] / 100 if mes else None,
        eur_noche=noche['rateAmountCents'] / 100 if noche else None,
        min_stay_dias=mes.get('minStay') if mes else None,
        max_stay_dias=mes.get('maxStay') if mes else None,
        disponible=True,
        estado='reservable',
        fuente='html',
    )
