"""Censo de unidades a partir del buscador del motor de reservas.

Hace falta porque la ficha comercial MIENTE POR OMISION: no enlaza todas las
unidades del edificio. El estudio basico (id 1327, la tipologia mas comun y la
mas barata) no aparece enlazado por ningun lado, y con el se escapaban tambien
1324, 1325 y 1326.

Sacar el censo de aqui y no de los enlaces comerciales es la diferencia entre
vigilar el edificio entero o solo la parte que quieren ensenar.
"""
import re

from . import booking, fetch

URL = 'https://book.becasaapartments.com/es/search?checkIn={ini}&checkOut={fin}'

_RE_PROPIEDAD = re.compile(r'"__typename":"Property","id":(\d+)')
_RE_CIUDAD = re.compile(r'"city":"([^"]{2,60})"')


def _normaliza(s):
    """Compara nombres de ciudad sin depender de tildes ni mayusculas."""
    tabla = str.maketrans('áàäâéèëêíìïîóòöôúùüûñ', 'aaaaeeeeiiiioooouuuun')
    return s.lower().translate(tabla).strip()


def censo(payload, ciudad):
    """IDs de unidad del edificio pedido, extraidos del payload del buscador."""
    objetivo = _normaliza(ciudad)
    marcas = list(_RE_PROPIEDAD.finditer(payload))
    ids = []
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(payload)
        bloque = payload[m.end():fin]
        c = _RE_CIUDAD.search(bloque)
        if c and _normaliza(c.group(1)) == objetivo:
            ids.append(m.group(1))
    # el buscador repite unidades entre secciones de la pagina
    return sorted(set(ids), key=int)


def descubrir(ciudad, check_in, check_out):
    """Consulta el buscador y devuelve los IDs del edificio."""
    _, html = fetch.get_text(URL.format(ini=check_in, fin=check_out))
    return censo(booking.flight(html), ciudad)
