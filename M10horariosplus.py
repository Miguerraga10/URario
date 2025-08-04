# Librerías
import time
import json
import os
import textwrap
import random
import copy
import streamlit as st
from itertools import product, combinations
from Clases.Clase import Clase
from Clases.Grupo import Grupo
from Clases.Horario import Horario
from Clases.Materia import Materia
from Revisa_Materias import materias_posibles_desde_historial
# Llamada a la ventana de horario generado
## Eliminar dependencias de interfaces tradicionales
from constantes import (
    niveles_unal,
    sedes_unal,
    facultades_unal,
    carreras_por_facultad
)

# Cargar carreras y facultades de UNAL
DATA_PATH = os.path.join(os.path.dirname(__file__), 'sia-extractor-main', 'data', 'carreras.json')
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"No se encontró el archivo de carreras en {DATA_PATH}. Por favor, verifica la ruta y que el archivo exista.")
with open(DATA_PATH, encoding='utf-8') as f:
    carreras_data = json.load(f)

def obtener_facultades_por_sede(sede):
    return sorted(set(item['facultad'] for item in carreras_data if item['sede'] == sede))

def obtener_carreras_por_facultad_nivel_sede(facultad, nivel, sede):
    return [item['carrera'] for item in carreras_data if item['facultad'] == facultad and item['nivel'] == nivel and item['sede'] == sede]

niveles_unal = [
    "Pregrado",
    "Doctorado",
    "Posgrados y másteres"
]
sedes_unal = [
    "1125 SEDE AMAZONIA", "1101 SEDE BOGOTÁ", "1126 SEDE CARIBE",
    "9933 SEDE DE LA PAZ", "1103 SEDE MANIZALES", "1102 SEDE MEDELLÍN",
    "1124 SEDE ORINOQUIA", "1104 SEDE PALMIRA", "9920 SEDE TUMACO"
]

# Funciones para horario óptimo
def generar_horarios(materias, mincreditos=8, maxcreditos=float('inf'),
                    minmaterias=1, maxmaterias=float('inf'),
                    hora_inicio="08:00", hora_fin="20:00", usar_cupos=False,
                    maxdias=7, usar_virtuales=True, horas_libres=None):
    """Genera horarios óptimos considerando restricciones, incluyendo
    intervalos de horas libres obligatorias.
    Args:
        materias (list): Lista de objetos Materia.
        mincreditos, maxcreditos, minmaterias, maxmaterias, hora_inicio, hora_fin, usar_cupos, maxdias, usar_virtuales: Restricciones generales.
        horas_libres (list): Lista de dicts con 'inicio', 'fin', 'dias' para intervalos de descanso.
    Returns:
        Horario óptimo o None.
    """
    inicio = time.time()
    creditos_minimos_en_materia = min(m.creditos for m in materias)
    creditos_maximos_en_materia = max(m.creditos for m in materias)
    maxmaterias_posibles = maxcreditos / creditos_minimos_en_materia
    maxcreditos_posibles = maxmaterias * creditos_maximos_en_materia
    if maxmaterias_posibles < maxmaterias:
        maxmaterias = int(maxmaterias_posibles // 1)
    if maxcreditos_posibles < maxcreditos:
        maxcreditos = int(maxcreditos_posibles)
    # Trabajar siempre sobre copias profundas para no modificar los objetos originales
    materias = copy.deepcopy(materias)
    
    def hora_a_minutos(hora):
        # Convierte 'HH:MM' a minutos desde las 00:00
        h, m = map(int, hora.split(':'))
        return h * 60 + m

    def grupo_fuera_de_intervalo(grupo):
        # Si alguna clase del grupo se traslapa (total o parcialmente) con un intervalo de horas libres, el grupo debe eliminarse
        if horas_libres:
            for clase in grupo.horarios:
                dia_clase = clase.dia.strip().lower()
                inicio_clase = hora_a_minutos(clase.hora_inicio)
                fin_clase = hora_a_minutos(clase.hora_fin)
                for intervalo in horas_libres:
                    dias_libres = [d.strip().lower() for d in intervalo['dias']]
                    if dia_clase in dias_libres:
                        inicio_libre = hora_a_minutos(intervalo['inicio'])
                        fin_libre = hora_a_minutos(intervalo['fin'])
                        if inicio_clase < fin_libre and fin_clase > inicio_libre:
                            return True

        # Restricción de horario general
        for clase in grupo.horarios:
            if not (hora_inicio <= clase.hora_inicio < hora_fin and hora_inicio < clase.hora_fin <= hora_fin):
                return True

        return False

    def incompatible(incompatibles, comb):
        return any(
            frozenset((g1, g2)) in incompatibles for g1, g2 in combinations(comb, 2)
        )

    verificacion_cache = {}

    def verificar_con_cache(horario, grupo):
        key = (id(horario), id(grupo))
        if key in verificacion_cache:
            return verificacion_cache[key]
        resultado = horario.verificar_grupo(grupo)
        verificacion_cache[key] = resultado
        return resultado

    materias_filtradas = []
    materias_obligatorias_faltantes = []

    for m in materias:
        # Guardar copia de los grupos originales antes de cualquier filtrado
        if not hasattr(m, 'grupos_originales'):
            m.grupos_originales = list(m.grupos)
        grupos_validos = [
            g for g in m.grupos_originales if (
                (not usar_cupos or g.cupos > 0) and
                (not grupo_fuera_de_intervalo(g)) and
                (usar_virtuales or not any(c.lugar == "Virtual" for c in g.clases))
            )
        ]
        # Nunca modificar m.grupos_originales ni m.grupos del objeto original
        m_copia = copy.deepcopy(m)
        m_copia.grupos = grupos_validos
        if m.obligatoria and not grupos_validos:
            materias_obligatorias_faltantes.append(m.nombre)
        if grupos_validos:
            materias_filtradas.append(m_copia)

    if materias_obligatorias_faltantes:
        st.error(
            "No hay grupos disponibles para las materias obligatorias:\n- " +
            "\n- ".join(materias_obligatorias_faltantes)
        )
        return None

    materias_obligatorias = [m for m in materias_filtradas if m.obligatoria]
    materias_optativas = [m for m in materias_filtradas if not m.obligatoria]

    horario_base = Horario()
    hubo_cambios = True
    materias_asignadas = []

    while hubo_cambios:
        hubo_cambios = False
        # Refiltrar obligatorias por las que aún no se han asignado
        materias_pendientes = [m for m in materias_obligatorias if m.nombre not in materias_asignadas]
        materias_solo_un_grupo = [m for m in materias_pendientes if len(m.grupos) == 1]
        materias_varios_grupos = [m for m in materias_pendientes if len(m.grupos) > 1]
        for materia in materias_solo_un_grupo:
            grupo = materia.grupos[0]
            if horario_base.verificar_grupo(grupo):
                horario_base.agregar_grupo(grupo)
                materias_asignadas.append(materia.nombre)
                hubo_cambios = True
            else:
                st.error(
                    f"No se pudo asignar el grupo único de la materia obligatoria: {materia.nombre}"
                )
                return None
        for materia in materias_varios_grupos:
            grupos_compatibles = [g for g in materia.grupos if horario_base.verificar_grupo(g)]
            if len(grupos_compatibles) != len(materia.grupos):
                hubo_cambios = True
            materia.grupos = grupos_compatibles
        # Eliminar materias sin grupos válidos
        materias_filtradas = [m for m in materias_filtradas if m.grupos]


    if len(materias_obligatorias) > maxmaterias:
        st.warning(
            "Hay más materias obligatorias que la cantidad máxima permitida."
        )
        return None

    # Finalmente, filtrar optativas
    for materia in materias_optativas:
        grupos_compatibles = [g for g in materia.grupos if horario_base.verificar_grupo(g)]
        materia.grupos = grupos_compatibles

    materias_filtradas = [m for m in materias_filtradas if m.grupos]
    materias_obligatorias = [m for m in materias_filtradas if m.obligatoria]
    materias_optativas = [m for m in materias_filtradas if not m.obligatoria]

    grupos_incompatibles = set()
    combinaciones_obligatorias_viables = []

    # Buscar combinaciones viables solo con materias obligatorias
    for combinacion_obligatorias in product(*[m.grupos for m in materias_obligatorias]):
        if any(frozenset((g1, g2)) in grupos_incompatibles for g1, g2 in combinations(combinacion_obligatorias, 2)):
            continue

        horario = Horario()
        es_viable = True

        for grupo in combinacion_obligatorias:
            if not horario.verificar_grupo(grupo):
                es_viable = False
                horario_temp = Horario() 
                horario.agregar_grupo(grupo)
                for g1 in combinacion_obligatorias:
                    if grupo != g1 and not horario_temp.verificar_grupo(g1) and not((frozenset((grupo, g1)) in grupos_incompatibles) or (frozenset((g1, grupo)) in grupos_incompatibles)):
                        grupos_incompatibles.add(frozenset((grupo, g1)))
                break
            horario.agregar_grupo(grupo)

        if es_viable:
            combinaciones_obligatorias_viables.append(combinacion_obligatorias)

    if not combinaciones_obligatorias_viables:
        st.warning("No hay forma de organizar un horario con todas las materias obligatorias.")
        return None

    mejor_horario = None
    max_materias = 0
    max_creditos = 0
    menor_dias_ocupados = float('inf')
    menor_huecos = float('inf')
    materias_seleccionadas_final = []
    grupos_final_incompatibles = set()
    mejor_encontrado = False

    for num_materias_optativas in range(maxmaterias - len(materias_obligatorias), -1, -1):
        combinaciones_optativas_viables = []
        if mejor_encontrado:
            break
        
        for combinacion_optativas in combinations(materias_optativas, num_materias_optativas):
            for combinacion_grupos in product(*[m.grupos for m in combinacion_optativas]):
                if any(frozenset((g1, g2)) in grupos_incompatibles for g1, g2 in combinations(combinacion_grupos, 2)):
                    continue
                
                horario = Horario()
                es_viable = True
                for grupo in combinacion_grupos:
                    if not horario.verificar_grupo(grupo):
                        es_viable = False
                        horario_temp = Horario() 
                        horario_temp.agregar_grupo(grupo)
                        for g1 in combinacion_grupos:
                            if grupo != g1 and not horario_temp.verificar_grupo(g1) and not((frozenset((grupo, g1)) in grupos_incompatibles) or (frozenset((g1, grupo)) in grupos_incompatibles)):
                                grupos_incompatibles.add(frozenset((grupo, g1)))
                        break
                    horario.agregar_grupo(grupo)

                if es_viable:
                    combinaciones_optativas_viables.append(combinacion_grupos)

        for combinacion_total in product(combinaciones_obligatorias_viables, combinaciones_optativas_viables):
            combinacion_final = list(combinacion_total[0]) + list(combinacion_total[1])

            if any(frozenset((g1, g2)) in grupos_final_incompatibles for g1, g2 in combinations(combinacion_final, 2)):
                continue

            horario = Horario()
            es_viable = True

            for grupo in combinacion_final:
                if not horario.verificar_grupo(grupo):
                    es_viable = False
                    horario_temp = Horario() 
                    horario_temp.agregar_grupo(grupo)
                    for g1 in combinacion_final:
                        if grupo != g1 and not horario.verificar_grupo(g1) and not((frozenset((grupo, g1)) in grupos_final_incompatibles) or (frozenset((g1, grupo)) in grupos_final_incompatibles)):
                            grupos_final_incompatibles.add(frozenset((grupo, g1)))
                    break
                    
                horario.agregar_grupo(grupo)

            if es_viable:
                creditos_asignados = sum(grupo.creditos for grupo in combinacion_final)
                if creditos_asignados > maxcreditos or creditos_asignados < mincreditos:
                    continue  

                dias_ocupados = sum(1 for dia in horario.dias if any(horario.dias[dia].values()))
                if dias_ocupados > maxdias:
                    continue  
                huecos = horario.contar_huecos()

                if ((len(combinacion_final) > max_materias) or
                    (len(combinacion_final) == max_materias and dias_ocupados < menor_dias_ocupados) or
                    (len(combinacion_final) == max_materias and dias_ocupados == menor_dias_ocupados and creditos_asignados > max_creditos) or
                    (len(combinacion_final) == max_materias and dias_ocupados == menor_dias_ocupados and creditos_asignados == max_creditos and huecos < menor_huecos)):
                    
                    mejor_horario = horario
                    mejor_encontrado = True
                    max_materias = len(combinacion_final)
                    max_creditos = creditos_asignados
                    menor_dias_ocupados = dias_ocupados
                    menor_huecos = huecos
                    materias_seleccionadas_final = [(grupo.horarios[0].nombre, grupo.grupo) for grupo in combinacion_final]

    fin = time.time()
    print(f"Tiempo de ejecución: {fin - inicio:.4f} segundos")

    # 🎯 Mostrar resultado final
    if mejor_horario:
        st.success("Materias seleccionadas:")
        for materia, grupo in materias_seleccionadas_final:
            st.write(f"- {materia} - Grupo: {grupo}")
        st.write(f"Total de materias seleccionadas: {max_materias}")
        st.write(f"Total de créditos seleccionados: {max_creditos}")
        st.write("Mejor horario encontrado:")
        # Puedes adaptar mejor_horario.imprimir() para mostrar en Streamlit
        st.write(str(mejor_horario))
        # Aquí podrías mostrar una tabla o gráfico con el horario
        return mejor_horario
    else:
        st.error("No se pudo generar un horario óptimo.")
        return None
    

## El punto de entrada ahora será app.py con Streamlit
