"""Tests sin red: todo corre contra HTML guardado en fixtures.

Su trabajo real no es comprobar que hoy funciona, sino avisar el dia que Be Casa
cambie el formato de sus paginas y el vigilante se quede ciego en silencio.
"""
import pathlib

import pytest

from becasa import api, booking, diff, marketing
from becasa.models import Snapshot, Unit

FIXTURES = pathlib.Path(__file__).parent / 'fixtures'
CFG = {'umbral_eur': 960, 'avisar_por_debajo_del_umbral': True,
       'avisar_bajada_de_precio': True, 'avisar_unidad_nueva': True,
       'avisar_promocion_nueva': True}


def leer(nombre):
    return (FIXTURES / nombre).read_text(encoding='utf-8', errors='replace')


# --- lectura del motor de reservas ---------------------------------------
def test_unidad_reservable_da_tarifa_mensual():
    u = booking.parse_unidad('1328', leer('booking-1328-reservable.html'))
    assert u.estado == 'reservable'
    assert u.nombre == 'Estudio adaptado'
    assert u.eur_mes == 921.0
    assert (u.min_stay_dias, u.max_stay_dias) == (61, 362)


def test_un_404_http_no_es_un_error():
    u = booking.parse_unidad('1330', '', status=404)
    assert u.estado == 'proximamente'
    assert u.eur_mes is None


def test_pagina_sin_tarifas_no_se_toma_por_reservable():
    """El payload de Next.js contiene '404' en TODAS las paginas.

    Por eso el criterio es que existan tarifas, no que aparezca ese texto.
    """
    u = booking.parse_unidad('1331', '<html>404 could not be found</html>')
    assert u.estado == 'proximamente'


# --- ficha comercial ------------------------------------------------------
def test_tramos_por_duracion():
    tramos = marketing.tramos_duracion(leer('marketing-ssr.html'))
    assert tramos.get('m10_12') == 893.0
    assert tramos['m10_12'] < tramos['m2_3']       # mas meses, menos precio


def test_censo_de_unidades():
    ids = marketing.ids_unidades(leer('marketing-ssr.html'))
    assert '1328' in ids and '1329' in ids
    assert len(ids) >= 4


def test_banners_de_promocion():
    assert any('horra' in p for p in marketing.promos(leer('marketing-ssr.html')))


# --- ventana de consulta --------------------------------------------------
@pytest.mark.parametrize('dias', [1, 60, 363, 365])
def test_rango_invalido_falla_ruidosamente(dias):
    """Fuera de 61-362 la API no da tarifa mensual: mejor romper que mentir."""
    with pytest.raises(api.RangoInvalido):
        api.ventana(dias)


def test_rango_valido():
    ini, fin = api.ventana(335)
    assert ini < fin


# --- decision de avisar ---------------------------------------------------
def _snap(precio, estado='reservable', ts='2026-09-10T00:00:00+00:00'):
    return Snapshot(ts=ts, estancia_dias=335, unidades=[
        Unit(id='1', nombre='Estudio', eur_mes=precio, estado=estado)])


def test_avisa_al_cruzar_el_umbral():
    avisos = diff.comparar(_snap(940), _snap(980), CFG)
    assert [a['tipo'] for a in avisos] == ['bajo_umbral']


def test_no_repite_el_aviso_de_umbral_si_ya_estaba_por_debajo():
    """De 950 a 940 no hay noticia de umbral: ya estaba cruzado.

    Si que hay noticia de bajada, que es otra cosa y se avisa aparte.
    """
    tipos = [a['tipo'] for a in diff.comparar(_snap(940), _snap(950), CFG)]
    assert 'bajo_umbral' not in tipos
    assert tipos == ['bajada']


def test_sin_cambios_no_hay_nada_que_contar():
    assert diff.comparar(_snap(940), _snap(940), CFG) == []


def test_avisa_de_bajada_aunque_siga_por_encima():
    avisos = diff.comparar(_snap(1000), _snap(1100), CFG)
    assert [a['tipo'] for a in avisos] == ['bajada']


def test_una_subida_no_genera_aviso():
    assert diff.comparar(_snap(1100), _snap(1000), CFG) == []


def test_no_avisa_dos_veces_de_la_misma_unidad():
    """Bajar y cruzar el umbral a la vez es una sola noticia, no dos."""
    avisos = diff.comparar(_snap(940), _snap(990), CFG)
    assert len(avisos) == 1


def test_avisa_cuando_una_unidad_pasa_a_reservable():
    avisos = diff.comparar(_snap(1500), _snap(None, estado='proximamente'), CFG)
    assert 'unidad_nueva' in [a['tipo'] for a in avisos]


def test_primera_ejecucion_avisa_de_lo_que_ya_esta_barato():
    avisos = diff.comparar(_snap(921), None, CFG)
    assert [a['tipo'] for a in avisos] == ['bajo_umbral']


def test_avisa_de_campana_nueva_solo_una_vez():
    viejo = _snap(921)
    nuevo = _snap(921)
    nuevo.promos_cms = [{'url': 'x.pdf', 'titulo': 'Campana', 'menciona_edificio': True}]
    assert [a['tipo'] for a in diff.comparar(nuevo, viejo, CFG)] == ['promocion']

    viejo.promos_cms = nuevo.promos_cms
    assert diff.comparar(nuevo, viejo, CFG) == []


# --- destinatarios --------------------------------------------------------
@pytest.mark.parametrize('valor,esperado', [
    ('a@x.com', ['a@x.com']),
    ('a@x.com,b@y.com', ['a@x.com', 'b@y.com']),
    ('a@x.com, b@y.com', ['a@x.com', 'b@y.com']),
    ('  a@x.com ; b@y.com , ', ['a@x.com', 'b@y.com']),
    ('', []),
    ('   ', []),
    ('no-es-un-correo', []),
])
def test_alert_to_admite_varias_direcciones(valor, esperado):
    from becasa.notify import destinatarios
    assert destinatarios(valor) == esperado


# --- tipologias que solo existen en la ficha comercial ---------------------
def test_ficha_comercial_incluye_el_estudio_basico():
    """El estudio sin terraza no existe en el motor: su pagina devuelve 404.

    Es la tipologia mas comun del edificio, asi que sin leer la ficha se
    quedaba sin vigilar.
    """
    cards = {c['nombre']: c['eur_mes'] for c in marketing.tarjetas(leer('marketing-ssr.html'))}
    assert cards['Estudio'] == 999.0
    assert cards['Estudio con terraza'] == 1123.0
    # y no duplica la misma tipologia escrita de dos maneras
    assert 'Apartamento de 2 dormitorios' not in cards
