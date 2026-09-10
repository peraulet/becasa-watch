"""Precio real por unidad, construyendo la consulta desde el esquema.

Uso:  python lav4.py [checkIn AAAA-MM-DD] [checkOut AAAA-MM-DD] [CUPON]
"""
import json, sys
from lav import gql, DATA_API, SITE

CHECK_IN = sys.argv[1] if len(sys.argv) > 1 else '2026-12-01'
CHECK_OUT = sys.argv[2] if len(sys.argv) > 2 else '2027-11-30'
COUPON = sys.argv[3] if len(sys.argv) > 3 else None
IDS = [1328, 1329, 1322, 1323, 1330, 1331, 1332, 1333, 1607, 13077]


def q(query, variables=None):
    return gql(DATA_API, query, variables)


def kind_of(t):
    while t and t.get('kind') in ('NON_NULL', 'LIST'):
        t = t.get('ofType')
    return (t or {}).get('kind'), (t or {}).get('name')


r = q('''{__type(name:"Property"){fields{name type{kind name
        ofType{kind name ofType{kind name}}}}}}''')
allf = ((r.get('data') or {}).get('__type') or {}).get('fields') or []
if not allf:
    print(json.dumps(r)[:600]); sys.exit(1)

scalars = {}
for f in allf:
    k, n = kind_of(f['type'])
    if k in ('SCALAR', 'ENUM'):
        scalars[f['name']] = n

print('#' * 72)
print(f'# LOS {len(allf)} CAMPOS DE Property   (escalares: {len(scalars)})')
print('#' * 72)
print('  escalares :', ', '.join(sorted(scalars)))
print('  objetos   :', ', '.join(sorted(f['name'] for f in allf if f['name'] not in scalars)))

# de los escalares, los que nos interesan si existen
WISH = ['title', 'displayName', 'propertyName', 'internalReference', 'propertyType',
        'reference', 'slug', 'available', 'currency', 'numberOfNights', 'nightlyPrice',
        'accommodationFare', 'totalFare', 'totalFareWithoutSecurityDeposit',
        'maxOccupants', 'city']
sel = [w for w in WISH if w in scalars]
print('\n  seleccionados:', ', '.join(sel))

QUERY = ('query($id:Int!,$site:String!,$in:ISO8601Date!,$out:ISO8601Date!,$coupon:String){'
         'property(id:$id, siteCode:$site, checkIn:$in, checkOut:$out,'
         ' numberOfGuests:1, locale:"es", couponCode:$coupon){'
         + ' '.join(sel) +
         ' rates{ rateAmountCents interval minStay maxStay }'
         ' couponDiscount{ valid code amount rejectionReason'
         ' accommodationFareAfterDiscount totalFareAfterDiscount }'
         '}}')

print()
print('#' * 72)
print(f'# PRECIO REAL   {CHECK_IN} -> {CHECK_OUT}' + (f'   cupon={COUPON}' if COUPON else ''))
print('#' * 72)
label = next((s for s in ('title', 'displayName', 'internalReference', 'propertyType') if s in sel), None)

for pid in IDS:
    r = q(QUERY, {'id': pid, 'site': SITE, 'in': CHECK_IN, 'out': CHECK_OUT, 'coupon': COUPON})
    if 'errors' in r or r.get('httpError'):
        msg = (r.get('errors') or [{}])[0].get('message', str(r.get('body', r)))[:170]
        print(f'  {pid}: ERROR {msg}')
        continue
    p = (r.get('data') or {}).get('property')
    if not p:
        print(f'  {pid}: sin datos')
        continue
    nights = p.get('numberOfNights') or 0
    acc = p.get('accommodationFare')
    pm = f'{acc / nights * 30.44:,.0f} EUR/mes' if (acc and nights) else '-'
    print(f'  {pid}: {str(p.get(label) if label else "")[:44]:<44} '
          f'disp={p.get("available")} {pm:>16} '
          f'total={acc} noches={nights}')
    if p.get('rates'):
        print(f'        rates: {json.dumps(p["rates"], ensure_ascii=False)}')
    if p.get('couponDiscount'):
        print(f'        cupon: {json.dumps(p["couponDiscount"], ensure_ascii=False)}')
