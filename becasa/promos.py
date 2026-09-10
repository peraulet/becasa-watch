"""Descubrimiento de campanas promocionales.

Be Casa no usa codigos de cupon publicos: sus descuentos se aplican firmando un
anexo al contrato, y cada campana se publica como PDF con bases legales en su
CMS. Vigilar ese CMS es, por tanto, el unico "buscador de ofertas" que de
verdad encuentra algo.

Y el dato que justifica todo esto: esas bases admiten expresamente a residentes
que renuevan contrato.
"""
import io
import json
import re

from . import fetch

CMS = 'https://cmseditor.becasaapartments.com'
MEDIA = CMS + '/wp-json/wp/v2/media?per_page={n}&orderby=date&order=desc'

_RE_PDF = re.compile(r'https?://[^\s"\'<>]+\.pdf', re.I)
_RE_RENOVACION = re.compile(r'renueven|renovaci[oó]n|residentes que ya vivan', re.I)
_RE_DESCUENTO = re.compile(r'(\d{1,2})\s*%\s*de\s*descuento', re.I)
_RE_MES_GRATIS = re.compile(r'(1|un)\s*mes\s*(de\s*renta\s*)?gratis', re.I)


def listar_media(n=40):
    """PDFs publicados en el CMS, del mas reciente al mas antiguo."""
    try:
        status, txt = fetch.get_text(MEDIA.format(n=n),
                                     headers={'Accept': 'application/json'})
    except fetch.FetchError:
        return []
    if status != 200:
        return []
    try:
        items = json.loads(txt)
    except ValueError:
        return []
    out = []
    for it in items if isinstance(items, list) else []:
        url = it.get('source_url') or ''
        if url.lower().endswith('.pdf'):
            out.append({'url': url,
                        'titulo': (it.get('title') or {}).get('rendered'),
                        'fecha': it.get('date')})
    return out


def pdfs_en(html_txt):
    """PDFs enlazados desde una pagina, por si el CMS no expone su API."""
    return sorted(set(_RE_PDF.findall(html_txt)))


def texto_pdf(data):
    """Extrae texto de un PDF en memoria. Devuelve '' si no se puede."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return ''
    try:
        lector = PdfReader(io.BytesIO(data))
        return '\n'.join((p.extract_text() or '') for p in lector.pages)
    except Exception:                                    # noqa: BLE001
        return ''


def analizar(texto, edificio_nombre):
    """Resume lo que una campana ofrece y si aplica al edificio del usuario."""
    plano = re.sub(r'\s+', ' ', texto)
    pcts = sorted({int(m) for m in _RE_DESCUENTO.findall(plano)}, reverse=True)
    return {
        'menciona_edificio': edificio_nombre.lower() in plano.lower(),
        'admite_renovaciones': bool(_RE_RENOVACION.search(plano)),
        'descuentos_pct': pcts,
        'mes_gratis': bool(_RE_MES_GRATIS.search(plano)),
    }


def revisar(edificio_nombre, vistos=(), limite=8):
    """PDFs nuevos desde la ultima ejecucion, ya analizados."""
    nuevos = []
    for item in listar_media():
        if item['url'] in vistos:
            continue
        try:
            status, data = fetch.get_bytes(item['url'])
        except fetch.FetchError:
            continue
        if status != 200 or not data:
            continue
        info = analizar(texto_pdf(data), edificio_nombre)
        nuevos.append({**item, **info})
        if len(nuevos) >= limite:
            break
    return nuevos
