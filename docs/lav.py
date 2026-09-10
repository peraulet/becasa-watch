"""Cliente mnimo contra la API GraphQL de Lavanda usado por Be Casa."""
import json, urllib.request, urllib.error

SITE = 'a6180e15-8715-495f-9039-6264c8041901'
DATA_API = 'https://api.lavanda.app/api/graphql'
OPS_API = f'https://dbw-api.lavanda.app/api/graphql?X-Hanami-Direct-Bookings-Site-Id={SITE}'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'


def gql(url, query, variables=None, op=None):
    payload = {'query': query, 'variables': variables or {}}
    if op:
        payload['operationName'] = op
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        'User-Agent': UA,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': 'https://book.becasaapartments.com',
        'Referer': 'https://book.becasaapartments.com/',
        'X-Hanami-Direct-Bookings-Site-Code': SITE,
        'apollographql-client-name': 'lavanda-dbw',
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return {'httpError': e.code, 'body': e.read().decode('utf-8', 'replace')[:600]}
    except Exception as e:
        return {'error': str(e)}


if __name__ == '__main__':
    for name, url in (('DATA', DATA_API), ('OPS', OPS_API)):
        print('=' * 72)
        print(name, url[:70])
        r = gql(url, '{__typename}')
        print('  ping:', json.dumps(r)[:220])
        r = gql(url, '{__schema{queryType{fields{name}}}}')
        s = json.dumps(r)
        print('  introspection:', s[:400])
