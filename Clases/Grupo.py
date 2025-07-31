class Grupo:
    """Representa un grupo de una materia, según el JSON de ejemplo."""
    def __init__(self, grupo, horarios, creditos, cupos=0, profesor=None, duracion=None, jornada=None):
        self.grupo = grupo
        self.horarios = horarios if horarios is not None else []
        self.creditos = creditos
        self.cupos = cupos
        self.profesor = profesor
        self.duracion = duracion
        self.jornada = jornada