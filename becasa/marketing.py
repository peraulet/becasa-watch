"""Lectura de la ficha comercial de becasaapartments.com.

Sirve para dos cosas: los tramos de precio por duracion de estancia, y los
banners de promocion, que a veces anuncian un ahorro que todavia no se refleja
en la tarifa del motor de reservas.

Ojo: esta pagina va desactualizada respecto al buscador (llego a anunciar
1.123 EUR por una unidad que la API daba a 921 EUR). Nunca es fuente de precio;
es fuente de promociones y de contraste.
"""
import html as _html
import json
import re

URL = 'https://www.becasaapartments.com/flex-living-madrid/{edificio}/'

_RE_CONTEXT = re.compile(r'var becasaPageContext\s*=\s*(\{.*?\});', re.S)
_RE_EUR = re.compile(r'([\d.,]+)\s*(?:&euro;|€)')
# Reclamos concretos. Nada de ventanas de N caracteres: la maquetacion repite
# el mismo texto en varios nodos y una ventana ciega devuelve frases cortadas
# por la mitad y duplicadas.
_RE_PROMO = re.compile(
    r'(?:ahorra(?:r)?\s+hasta\s+[\d.,]+\s*(?:€|EUR)(?:\s*/\s*mes)?'
    r'|[\d.,]+\s*%\s*de\s+descuento'
    r'|(?:1|un)\s+mes\s+(?:de\s+renta\s+)?gratis)', re.I)
# condicion que suele acompanar al reclamo ("+ de 10 meses")
_RE_CONDICION = re.compile(r'^\s*\+?\s*de\s+(\d+)\s+meses', re.I)


def url_edificio(edificio):
    return URL.format(edificio=edificio)


def _num(s):
    """'1.123' -> 1123.0 ; '937' -> 937.0"""
    s = s.strip().rstrip('.,')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif s.count('.') == 1 and len(s.split('.')[1]) == 3:
        s = s.replace('.', '')            # separador de millar
    else:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def contexto(html_txt):
    """El objeto JS con los tramos de precio por duracion."""
    m = _RE_CONTEXT.search(html_txt)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except ValueError:
        return {}


def tramos_duracion(html_txt):
    """{'m10_12': 893.0, 'm7_9': 1024.0, ...} en euros al mes."""
    labels = (contexto(html_txt).get('price_labels') or {})
    out = {}
    for clave, texto in labels.items():
        if not texto:
            continue
        m = _RE_EUR.search(_html.unescape(texto))
        if m:
            v = _num(m.group(1))
            if v:
                out[clave] = v
    return out


def texto_visible(html_txt):
    """Aplana el marcado a texto corrido.

    Imprescindible: maquetan los reclamos partidos entre etiquetas
    ('<span>Ahorra</span><span> hasta 248 EUR/mes</span>'), asi que buscar sobre
    el HTML crudo no encuentra nunca la frase completa.
    """
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html_txt, flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'[ \t ]+', ' ', _html.unescape(t))


def promos(html_txt):
    """Textos de promocion visibles en la pagina, deduplicados."""
    texto = texto_visible(html_txt)
    vistos, out = set(), []
    for m in _RE_PROMO.finditer(texto):
        s = re.sub(r'\s+', ' ', m.group(0)).strip(' .;:')
        cond = _RE_CONDICION.match(texto[m.end():m.end() + 30])
        if cond:
            s += f' (a partir de {cond.group(1)} meses)'
        clave = s.lower()
        if clave not in vistos:
            vistos.add(clave)
            out.append(s)
    return out


def ids_unidades(html_txt):
    """IDs de las unidades enlazadas hacia el motor de reservas."""
    ids = re.findall(r'book\.becasaapartments\.com/[a-z]{2}/properties/(\d+)',
                     _html.unescape(html_txt))
    return sorted(set(ids), key=int)
