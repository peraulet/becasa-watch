"""Estructuras de datos compartidas."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Unit:
    """Una tipologia de alojamiento del edificio."""
    id: str
    nombre: Optional[str] = None
    eur_mes: Optional[float] = None
    eur_noche: Optional[float] = None
    min_stay_dias: Optional[int] = None
    max_stay_dias: Optional[int] = None
    disponible: Optional[bool] = None
    limpieza_eur: Optional[float] = None
    estado: str = 'reservable'          # reservable | proximamente | error
    fuente: str = 'html'                # html | api

    def dict(self):
        return asdict(self)


@dataclass
class Snapshot:
    """Fotografia completa del edificio en un instante."""
    ts: str
    estancia_dias: int
    check_in: str = ''
    check_out: str = ''
    unidades: list = field(default_factory=list)
    tramos_duracion: dict = field(default_factory=dict)
    promos_web: list = field(default_factory=list)
    promos_cms: list = field(default_factory=list)

    def dict(self):
        d = asdict(self)
        d['unidades'] = [u.dict() if isinstance(u, Unit) else u for u in self.unidades]
        return d

    @property
    def por_id(self):
        return {u.id: u for u in self.unidades}

    def reservables(self):
        return [u for u in self.unidades if u.estado == 'reservable' and u.eur_mes]
