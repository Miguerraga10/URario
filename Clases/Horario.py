# Importamos librerías necesarias
from tabulate import tabulate

class Horario:
    """Representa un horario semanal con clases organizadas por día y hora.
    Permite agregar y eliminar clases o grupos, verificar restricciones y
    mostrar el horario en formato de tabla.

    """
    def __init__(self):
        """Inicializa un horario vacío con todos los días de la semana y
        24 horas por día. También mantiene un registro de los grupos añadidos.

        """
        self.dias = {
            dia: {hora: None for hora in self.horas()}
            for dia in ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
        }
        self.grupos = []


    def horas(self):
        """Genera una lista de horas en formato HH:00 desde las 00:00 hasta
        las 23:00.

        Returns:
            list: Lista de strings con horas.

        """
        return [f"{h:02d}:00" for h in range(0, 24)]


    def agregar_clase(self, clase, grupo):
        """Intenta agregar una clase al horario si las horas están disponibles.

        Args:
            clase (Clase): Clase a agregar.
            grupo (Grupo): Grupo al que pertenece la clase.

        Returns:
            bool: True si se agregó correctamente, False si hubo conflicto.

        """
        hora_inicio = int(clase.hora_inicio.split(":")[0])
        hora_fin = int(clase.hora_fin.split(":")[0])

        # Verificar disponibilidad en el horario
        for hora in range(hora_inicio, hora_fin):
            hora_formateada = f"{hora:02d}:00"
            if self.dias[clase.dia].get(hora_formateada) is not None:
                return False

        # Asignar clase a las horas disponibles
        for hora in range(hora_inicio, hora_fin):
            hora_formateada = f"{hora:02d}:00"
            self.dias[clase.dia][hora_formateada] = f"{clase.nombre} ({clase.lugar[:2]})"

        if grupo not in self.grupos:
            self.grupos.append(grupo)

        return True


    def eliminar_clase(self, clase):
        """Elimina una clase del horario y actualiza los grupos si es
        necesario.

        Args:
            clase (Clase): Clase a eliminar.

        """
        hora_inicio = int(clase.hora_inicio.split(":")[0])
        hora_fin = int(clase.hora_fin.split(":")[0])

        # Liberar las horas correspondientes
        for hora in range(hora_inicio, hora_fin):
            hora_formateada = f"{hora:02d}:00"
            if self.dias[clase.dia].get(hora_formateada) is not None:
                self.dias[clase.dia][hora_formateada] = None

        # Verificar si el grupo ya no tiene clases activas
        grupo_remover = None
        for grupo in self.grupos:
            if clase in grupo.horarios:
                if not any(
                    self.dias[c.dia][f"{int(c.hora_inicio.split(':')[0]):02d}:00"] is not None
                    for c in grupo.horarios
                ):
                    grupo_remover = grupo
                    break

        if grupo_remover in self.grupos:
            self.grupos.remove(grupo_remover)


    def validar_ubicacion(self, clase):
        """Valida si la ubicación de una clase cumple con las restricciones
        entre sedes.

        Args:
            clase (Clase): Clase cuya ubicación se quiere validar.

        Returns:
            bool: True si la ubicación es válida.

        """
        # Descomentar este bloque para activar restricciones entre sedes.
        """
        horas = self.horas()
        indice_hora = horas.index(clase.hora_inicio)
        if indice_hora > 0:
            hora_anterior = horas[indice_hora - 1]
            clase_anterior = self.dias[clase.dia][hora_anterior]
            if clase_anterior:
                lugar_anterior = clase_anterior.split('(')[-1].strip(')')
                lugar_actual = clase.lugar[0:2]

                if lugar_anterior == "Ud" and lugar_actual == "Mi":
                    return False
        """
        return True


    def verificar_grupo(self, grupo):
        """Verifica si todas las clases de un grupo pueden ser agregadas al
        horario.

        Args:
            grupo (Grupo): Grupo a verificar.

        Returns:
            bool: True si todas las clases pueden agregarse sin conflicto.

        """
        for clase in grupo.horarios:
            horas_ocupadas = [
                f"{hora:02d}:00"
                for hora in range(
                    int(clase.hora_inicio[:2]), int(clase.hora_fin[:2])
                )
            ]

            if any(self.dias[clase.dia].get(hora) is not None for hora in horas_ocupadas):
                return False

            if not self.validar_ubicacion(clase):
                return False

        return True


    def agregar_grupo(self, grupo):
        """Intenta agregar todas las clases de un grupo al horario.

        Args:
            grupo (Grupo): Grupo a agregar.

        Returns:
            bool: True si el grupo fue agregado exitosamente, sino False.

        """
        if not self.verificar_grupo(grupo):
            return False

        clases_agregadas = []

        for clase in grupo.horarios:
            if self.agregar_clase(clase, grupo):
                clases_agregadas.append(clase)
            else:
                for clase_revertir in clases_agregadas:
                    self.eliminar_clase(clase_revertir)
                return False

        return True


    def contar_huecos(self):
        """Cuenta los huecos (espacios vacíos entre clases) en el horario.

        Returns:
            int: Número total de huecos en el horario.

        """
        huecos = 0
        for dia, horas in self.dias.items():
            clases_en_dia = [hora for hora, clase in horas.items() if clase is not None]
            if clases_en_dia:
                primera_clase = min(clases_en_dia)
                ultima_clase = max(clases_en_dia)
                horas_con_clases = [hora for hora in self.horas() if primera_clase <= hora <= ultima_clase]

                for hora in horas_con_clases:
                    if horas[hora] is None:
                        huecos += 1
        return huecos


    def imprimir(self):
        """Imprime el horario en formato de tabla con tabulate.

        """
        tabla = []
        headers = ["Hora"] + [
            "LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"
        ]
        horas = self.horas()

        for hora in horas:
            fila = [hora]
            for dia in headers[1:]:
                fila.append(self.dias[dia].get(hora, ""))
            tabla.append(fila)

        print("\n" + "=" * 20)
        print("Cronograma Semanal")
        print("=" * 20)
        print(tabulate(tabla, headers=headers, tablefmt="grid"))
        print("=" * 20)