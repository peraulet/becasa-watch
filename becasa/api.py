"""Cliente GraphQL de Lavanda, el backend real del motor de reservas.

Es publico y anonimo: basta la cabecera del sitio. Preferido sobre `booking`
porque devuelve datos estructurados en vez de HTML, e incluye disponibilidad y
tasas de limpieza.

Dos trampas aprendidas a base de sondearlo, importantes al mantener esto:

1. `accommodationFare` devuelve SIEMPRE la tarifa por noche, nunca la mensual,
   sea cual sea la duracion pedida. Hay que leer `rates`.
2. La tarifa mensual solo aparece en `rates` si la estancia consultada cae
   entre `minStay` y `maxStay` (61 y 362 noches). Fuera de ese rango solo
   queda la nocturna, que multiplicada da una cifra absurda.
"""
import datetime as dt

from . import fetch
from .models import Unit

ENDPOINT = 'https://api.lavanda.app/api/graphql'
SITE_CODE = 'a6180e15-8715-495f-9039-6264c8041901'

MIN_NOCHES, MAX_NOCHES = 61, 362

CONSULTA = '''
query($id:Int!,$site:String!,$in:ISO8601Date!,$out:ISO8601Date!,$coupon:String){
  property(id:$id, siteCode:$site, checkIn:$in, checkOut:$out,
           numberOfGuests:1, locale:"es", couponCode:$coupon){
    title available currency cleaningFee
    rates { rateAmountCents interval minStay maxStay }
    couponDiscount { valid code amount rejectionReason }
  }
}'''


class RangoInvalido(ValueError):
    pass


def ventana(estancia_dias, inicio=None):
    """Convierte una duracion en (checkIn, checkOut) validando el rango util."""
    if not MIN_NOCHES <= estancia_dias <= MAX_NOCHES:
        raise RangoInvalido(
            f'estancia_dias={estancia_dias} fuera de [{MIN_NOCHES}, {MAX_NOCHES}]: '
            'la API no devolveria tarifa mensual y el precio saldria mal')
    ini = inicio or (dt.date.today() + dt.timedelta(days=30))
    return ini.isoformat(), (ini + dt.timedelta(days=estancia_dias)).isoformat()


def _cabeceras():
    return {'X-Hanami-Direct-Bookings-Site-Code': SITE_CODE,
            'Origin': 'https://book.becasaapartments.com',
            'apollographql-client-name': 'lavanda-dbw'}


def consultar(pid, check_in, check_out, cupon=None):
    """Consulta cruda; devuelve el objeto `property` o None."""
    r = fetch.post_json(ENDPOINT, {
        'query': CONSULTA,
        'variables': {'id': int(pid), 'site': SITE_CODE,
                      'in': check_in, 'out': check_out, 'coupon': cupon},
    }, headers=_cabeceras())
    if r.get('errors'):
        return None
    return (r.get('data') or {}).get('property')


def parse_property(pid, prop):
    """`property` de la API -> Unit. Pura, testeable con respuestas guardadas."""
    if not prop:
        # la API responde con error cuando la unidad aun no es reservable
        return Unit(id=str(pid), estado='proximamente', fuente='api')

    rates = prop.get('rates') or []
    mes = next((r for r in rates if r.get('interval') == 'calendar_monthly'), None)
    noche = next((r for r in rates if r.get('interval') == 'nightly'), None)
    return Unit(
        id=str(pid),
        nombre=prop.get('title'),
        eur_mes=mes['rateAmountCents'] / 100 if mes else None,
        eur_noche=noche['rateAmountCents'] / 100 if noche else None,
        min_stay_dias=(mes or {}).get('minStay'),
        max_stay_dias=(mes or {}).get('maxStay'),
        disponible=prop.get('available'),
        limpieza_eur=prop.get('cleaningFee'),
        estado='reservable',
        fuente='api',
    )


def unidad(pid, check_in, check_out, cupon=None):
    return parse_property(pid, consultar(pid, check_in, check_out, cupon))


def validar_cupon(pid, codigo, check_in, check_out):
    """Comprueba un codigo concreto. No enumera: valida el que le des."""
    prop = consultar(pid, check_in, check_out, cupon=codigo)
    return (prop or {}).get('couponDiscount')
