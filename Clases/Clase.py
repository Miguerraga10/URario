class Clase:
    """Representa un horario dentro de un grupo (según el JSON: elemento
    de la lista 'horarios').
    
    """
    def __init__(self, nombre, dia, hora_inicio, hora_fin, lugar):
        self.nombre = nombre
        self.dia = dia
        self.hora_inicio = hora_inicio
        self.hora_fin = hora_fin
        self.lugar = lugar