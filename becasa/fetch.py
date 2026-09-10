"""HTTP con reintentos y espaciado educado.

Todo el trafico de red del proyecto pasa por aqui, para que el resto de modulos
sean funciones puras sobre texto y se puedan testear sin red.
"""
import json
import time
import urllib.error
import urllib.request

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
TIMEOUT = 45
REINTENTOS = 3
PAUSA = 1.0          # segundos entre peticiones, para no martillear su servidor


class FetchError(RuntimeError):
    pass


def _abrir(req, reintentos=REINTENTOS):
    ultimo = None
    for intento in range(reintentos):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            # 404 es informacion valida (unidad no publicada), no un fallo
            if e.code == 404:
                return 404, b''
            ultimo = e
        except Exception as e:                          # noqa: BLE001
            ultimo = e
        time.sleep(PAUSA * (2 ** intento))
    raise FetchError(f'{req.full_url}: {ultimo}')


def get_text(url, headers=None):
    """Descarga una URL y devuelve (status, texto)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept-Language': 'es-ES,es;q=0.9', **(headers or {})})
    status, body = _abrir(req)
    time.sleep(PAUSA)
    return status, body.decode('utf-8', 'replace')


def get_bytes(url, headers=None):
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    status, body = _abrir(req)
    time.sleep(PAUSA)
    return status, body


def post_json(url, payload, headers=None):
    """POST de JSON; devuelve el objeto decodificado."""
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        'User-Agent': UA, 'Content-Type': 'application/json',
        'Accept': 'application/json', **(headers or {})})
    status, body = _abrir(req)
    time.sleep(PAUSA)
    try:
        return json.loads(body.decode('utf-8', 'replace'))
    except ValueError as e:
        raise FetchError(f'{url}: respuesta no es JSON ({e})') from e
