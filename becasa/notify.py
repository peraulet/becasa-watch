"""Envio de avisos por correo.

Las credenciales llegan por variables de entorno, nunca por fichero: asi el
repositorio puede ser publico sin exponer nada.
"""
import os
import re
import smtplib
from email.message import EmailMessage

from .booking import url_unidad


def destinatarios(valor):
    """ALERT_TO admite varias direcciones separadas por coma o punto y coma.

    Se limpian los huecos y las comas sobrantes en vez de confiar en que la
    cabecera se parsee bien: una direccion con un espacio de mas se convierte
    en un correo que nunca llega y de cuya perdida no te enteras.
    """
    partes = [x.strip() for x in re.split(r'[;,]', valor or '')]
    return [x for x in partes if '@' in x]


def config_smtp():
    """Lee la configuracion SMTP del entorno. Devuelve None si falta algo."""
    cfg = {
        'host': os.environ.get('SMTP_HOST', '').strip(),
        'port': int(os.environ.get('SMTP_PORT', '587') or 587),
        'user': os.environ.get('SMTP_USER', '').strip(),
        # las contrasenas de aplicacion de Gmail se copian con espacios y
        # asi no funcionan; quitarlos aqui evita un fallo silencioso tipico
        'pwd': os.environ.get('SMTP_PASS', '').replace(' ', ''),
        'to': destinatarios(os.environ.get('ALERT_TO', '')),
    }
    if not all((cfg['host'], cfg['user'], cfg['pwd'], cfg['to'])):
        return None
    return cfg


def _cuerpo(avisos, snap, cfg_app):
    renta = cfg_app.get('renta_actual_eur')
    lineas = ['Novedades en Be Casa San Sebastian de los Reyes:', '']
    for a in avisos:
        lineas.append(f'  * {a["texto"]}')
        u = a.get('unidad')
        if u is not None:
            lineas.append(f'    {url_unidad(u.id)}')
        elif a.get('url'):
            lineas.append(f'    {a["url"]}')
        lineas.append('')

    lineas += ['', 'Estado actual del edificio:', '']
    for u in sorted(snap.reservables(), key=lambda x: x.eur_mes):
        marca = ''
        if renta and u.eur_mes < renta:
            marca = f'   <-- {renta - u.eur_mes:,.0f} EUR/mes menos de lo que pagas'
        lineas.append(f'  {u.eur_mes:>8,.0f} EUR/mes   {u.nombre or u.id}{marca}')

    if renta:
        lineas += ['', f'Tu renta actual: {renta:,.0f} EUR/mes.']
    lineas += ['', f'Consulta: {snap.ts}',
               'Recuerda: las bases legales de sus promociones admiten a '
               'residentes que renuevan contrato.']
    return '\n'.join(lineas)


def enviar(avisos, snap, cfg_app, dry_run=False):
    """Envia un correo con las novedades. Devuelve True si se envio."""
    if not avisos:
        return False

    cabecera = avisos[0]['texto']
    if len(avisos) > 1:
        cabecera += f' (+{len(avisos) - 1} mas)'

    smtp = config_smtp()
    cuerpo = _cuerpo(avisos, snap, cfg_app)

    if dry_run or not smtp:
        print('--- correo (no enviado) ---')
        print('Asunto:', f'[Be Casa] {cabecera}')
        print(cuerpo)
        print('--- fin ---')
        if not smtp and not dry_run:
            print('AVISO: faltan variables SMTP; no se ha enviado nada.')
        return False

    msg = EmailMessage()
    msg['Subject'] = f'[Be Casa] {cabecera}'
    msg['From'] = smtp['user']
    msg['To'] = ', '.join(smtp['to'])
    msg.set_content(cuerpo)

    with smtplib.SMTP(smtp['host'], smtp['port'], timeout=30) as s:
        s.starttls()
        s.login(smtp['user'], smtp['pwd'])
        # los destinatarios van explicitos, no deducidos de la cabecera
        s.send_message(msg, to_addrs=smtp['to'])
    print(f'Correo enviado a {len(smtp["to"])} destinatario(s).')
    return True
