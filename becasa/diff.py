"""Comparacion entre dos fotografias del edificio.

Aqui vive la decision de que merece un correo. La regla de fondo: se avisa
cuando algo CAMBIA, no cada vez que el vigilante mira. Si el estudio sigue a
921 EUR manana, no hay noticia.
"""
from .models import Snapshot


def _u(snap, uid):
    return snap.por_id.get(uid) if snap else None


def comparar(nuevo: Snapshot, viejo: Snapshot, cfg):
    """Devuelve la lista de novedades dignas de aviso."""
    umbral = cfg.get('umbral_eur', 960)
    avisos = []

    for u in nuevo.unidades:
        prev = _u(viejo, u.id)

        # 1. cruza el umbral (a la baja, o aparece ya por debajo)
        if cfg.get('avisar_por_debajo_del_umbral', True) and u.eur_mes:
            antes = prev.eur_mes if prev else None
            if u.eur_mes < umbral and (antes is None or antes >= umbral):
                avisos.append({
                    'tipo': 'bajo_umbral',
                    'unidad': u,
                    'antes': antes,
                    'texto': f'{u.nombre or u.id} a {u.eur_mes:,.0f} EUR/mes, '
                             f'por debajo de tu umbral de {umbral:,.0f} EUR',
                })

        # 2. cualquier bajada, aunque siga por encima del umbral
        if (cfg.get('avisar_bajada_de_precio', True) and prev
                and prev.eur_mes and u.eur_mes and u.eur_mes < prev.eur_mes):
            baja = prev.eur_mes - u.eur_mes
            if not any(a['tipo'] == 'bajo_umbral' and a['unidad'].id == u.id
                       for a in avisos):
                avisos.append({
                    'tipo': 'bajada',
                    'unidad': u,
                    'antes': prev.eur_mes,
                    'texto': f'{u.nombre or u.id} baja {baja:,.0f} EUR: '
                             f'{prev.eur_mes:,.0f} -> {u.eur_mes:,.0f} EUR/mes',
                })

        # 3. una unidad que no era reservable ahora lo es
        if (cfg.get('avisar_unidad_nueva', True) and prev
                and prev.estado == 'proximamente' and u.estado == 'reservable'):
            precio = f' a {u.eur_mes:,.0f} EUR/mes' if u.eur_mes else ''
            avisos.append({
                'tipo': 'unidad_nueva',
                'unidad': u,
                'antes': None,
                'texto': f'Nueva unidad reservable: {u.nombre or u.id}{precio}',
            })

    # 4. campanas nuevas en el CMS
    if cfg.get('avisar_promocion_nueva', True):
        antes = {p.get('url') for p in (viejo.promos_cms if viejo else [])}
        for p in nuevo.promos_cms:
            if p.get('url') in antes:
                continue
            marcas = []
            if p.get('menciona_edificio'):
                marcas.append('MENCIONA TU EDIFICIO')
            if p.get('admite_renovaciones'):
                marcas.append('admite renovaciones')
            if p.get('descuentos_pct'):
                marcas.append(f"hasta {max(p['descuentos_pct'])}% dto")
            if p.get('mes_gratis'):
                marcas.append('mes gratis')
            avisos.append({
                'tipo': 'promocion',
                'unidad': None,
                'antes': None,
                'texto': f"Nueva campana: {p.get('titulo') or p['url'].split('/')[-1]}"
                         + (f" ({', '.join(marcas)})" if marcas else ''),
                'url': p.get('url'),
            })

    return avisos


def hay_cambio_de_precio(nuevo: Snapshot, viejo: Snapshot):
    """Para decidir si merece la pena escribir un snapshot nuevo."""
    if viejo is None:
        return True
    a = {u.id: u.eur_mes for u in nuevo.unidades}
    b = {u.id: u.eur_mes for u in viejo.unidades}
    return a != b
