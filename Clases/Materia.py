class Materia:
    """Representa una materia, según el JSON de ejemplo."""
    def __init__(self, nombre, codigo, tipologia, creditos, facultad, carrera, fechaExtraccion, cuposDisponibles, grupos=None, obligatoria=False):
        self.nombre = nombre
        self.codigo = codigo
        self.tipologia = tipologia
        self.creditos = creditos
        self.facultad = facultad
        self.carrera = carrera
        self.fechaExtraccion = fechaExtraccion
        self.cuposDisponibles = cuposDisponibles
        self.grupos = grupos if grupos is not None else []
        self.obligatoria = obligatoria