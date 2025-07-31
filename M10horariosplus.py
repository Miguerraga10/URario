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
with open(r'd:\Miguel\Universidad\Gen_Horario\sia-extractor-main\data\carreras.json', encoding='utf-8') as f:
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
    """
    Genera horarios óptimos considerando restricciones, incluyendo intervalos de horas libres obligatorias.
    Args:
        materias (list): Lista de objetos Materia.
        mincreditos, maxcreditos, minmaterias, maxmaterias, hora_inicio, hora_fin, usar_cupos, maxdias, usar_virtuales: Restricciones generales.
        horas_libres (list): Lista de dicts con 'inicio', 'fin', 'dias' para intervalos de descanso.
    Returns:
        Horario óptimo o None.
    """
    print(horas_libres)
    inicio = time.time()
    creditos_minimos_en_materia = min(m.creditos for m in materias)
    creditos_maximos_en_materia = max(m.creditos for m in materias)
    maxmaterias_posibles = maxcreditos / creditos_minimos_en_materia
    maxcreditos_posibles = maxmaterias * creditos_maximos_en_materia
    if maxmaterias_posibles < maxmaterias:
        maxmaterias = int(maxmaterias_posibles // 1)
    if maxcreditos_posibles < maxcreditos:
        maxcreditos = int(maxcreditos_posibles)
    materias = [copy.deepcopy(m) for m in materias]
    
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
                    # Normalizar días del intervalo
                    dias_libres = [d.strip().lower() for d in intervalo['dias']]
                    if dia_clase in dias_libres:
                        inicio_libre = hora_a_minutos(intervalo['inicio'])
                        fin_libre = hora_a_minutos(intervalo['fin'])
                        # Traslape total o parcial: inicio_clase < fin_libre y fin_clase > inicio_libre
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
            g for g in m.grupos if (
                (not usar_cupos or g.cupos > 0) and
                (not grupo_fuera_de_intervalo(g)) and
                (usar_virtuales or not any(c.lugar == "Virtual" for c in g.clases))
            )
        ]
        if m.obligatoria and not grupos_validos:
            materias_obligatorias_faltantes.append(m.nombre)
        if grupos_validos:
            m.grupos = grupos_validos
            materias_filtradas.append(m)

    # Validación: si falta alguna materia obligatoria, no se puede continuar
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
    materias_asignadas = set()

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
                materias_asignadas.add(materia.nombre)
                hubo_cambios = True
            else:
                st.error(f"No se pudo asignar el grupo único de la materia obligatoria: {materia.nombre}")
                return None
        for materia in materias_varios_grupos:
            grupos_compatibles = [g for g in materia.grupos if horario_base.verificar_grupo(g)]
            if len(grupos_compatibles) != len(materia.grupos):
                hubo_cambios = True
            materia.grupos = grupos_compatibles
        # Eliminar materias sin grupos válidos
        print(hubo_cambios)
        materias_filtradas = [m for m in materias_filtradas if m.grupos]

    # Finalmente, filtrar optativas
    for materia in materias_optativas:
        grupos_compatibles = [g for g in materia.grupos if horario_base.verificar_grupo(g)]
        materia.grupos = grupos_compatibles

    materias_filtradas = [m for m in materias_filtradas if m.grupos]
    materias_obligatorias = [m for m in materias_filtradas if m.obligatoria]
    materias_optativas = [m for m in materias_filtradas if not m.obligatoria]

    if len(materias_obligatorias) > maxmaterias:
        st.warning(
            "Hay más materias obligatorias que la cantidad máxima permitida."
        )
        return None

    grupos_incompatibles = set()
    combinaciones_obligatorias_viables = []

    # Buscar combinaciones viables solo con materias obligatorias
    posibles_combinaciones_obligatorias = product(*[m.grupos for m in materias_obligatorias])
    for combinacion_obligatorias in posibles_combinaciones_obligatorias:
        if incompatible(grupos_incompatibles, combinacion_obligatorias):
            continue
        horario = Horario()
        es_viable = True
        for grupo in combinacion_obligatorias:
            if not verificar_con_cache(horario, grupo):
                # Creamos un nuevo horario con solo el grupo problemático
                horario_test = Horario()
                horario_test.agregar_grupo(grupo)
                # Verificamos contra los otros grupos
                for otro_grupo in combinacion_obligatorias:
                    if otro_grupo != grupo and not verificar_con_cache(horario_test, otro_grupo):
                        grupos_incompatibles.add(frozenset((grupo, otro_grupo)))
                es_viable = False
                break
            horario.agregar_grupo(grupo)
            dias_ocupados = sum(1 for dia in horario.dias if any(horario.dias[dia].values()))
            if dias_ocupados > maxdias:
                es_viable = False
                break
        if es_viable:
            combinaciones_obligatorias_viables.append(combinacion_obligatorias)

    if not combinaciones_obligatorias_viables:
        st.warning(
            'No hay forma de organizar un horario con todas las materias obligatorias.'
        )
        return None

    creditos_obligatorios = sum(m.creditos for m in materias_obligatorias)
    mejor_horario = None
    mejor_encontrado = False
    max_materias = 0
    max_creditos = 0
    menor_dias_ocupados = float('inf')
    menor_huecos = float('inf')
    materias_seleccionadas_final = []
    grupos_final_incompatibles = set()

    for num_materias_optativas in range(maxmaterias - len(materias_obligatorias), -1, -1):
        combinaciones_optativas_viables = []
        if mejor_encontrado:
            break
        for combinacion_optativas in combinations(materias_optativas, num_materias_optativas):
            creditos_asignados = sum(materia.creditos for materia in combinacion_optativas)
            if creditos_asignados > (maxcreditos - creditos_obligatorios):
                continue
            for combinacion_grupos in product(*[m.grupos for m in combinacion_optativas]):
                if incompatible(grupos_incompatibles, combinacion_grupos):
                    continue
                horario = Horario()
                es_viable = True
                for grupo in combinacion_grupos:
                    if not verificar_con_cache(horario, grupo):
                        # Creamos un nuevo horario with solo el grupo problemático
                        horario_test = Horario()
                        horario_test.agregar_grupo(grupo)
                        # Verificamos contra los otros grupos
                        for otro_grupo in combinacion_grupos:
                            if otro_grupo != grupo and not verificar_con_cache(horario_test, otro_grupo):
                                grupos_incompatibles.add(frozenset((grupo, otro_grupo)))
                        es_viable = False
                        break
                    horario.agregar_grupo(grupo)
                    dias_ocupados = sum(1 for dia in horario.dias if any(horario.dias[dia].values()))
                    if dias_ocupados > maxdias:
                        es_viable = False
                        break
                if es_viable:
                    combinaciones_optativas_viables.append(combinacion_grupos)
        # Evaluar combinaciones de obligatorias y optativas viables
        for combinacion_total in product(combinaciones_obligatorias_viables, combinaciones_optativas_viables):
            combinacion_final = list(combinacion_total[0]) + list(combinacion_total[1])
            if incompatible(grupos_final_incompatibles, combinacion_final):
                continue
            creditos_asignados = sum(grupo.creditos for grupo in combinacion_final)
            if creditos_asignados > maxcreditos or creditos_asignados < mincreditos:
                continue
            horario = Horario()
            es_viable = True
            for grupo in combinacion_final:
                if not verificar_con_cache(horario, grupo):
                    # Creamos un nuevo horario con solo el grupo problemático
                    horario_test = Horario()
                    horario_test.agregar_grupo(grupo)
                horario.agregar_grupo(grupo)
            dias_ocupados = sum(1 for dia in horario.dias if any(horario.dias[dia].values()))
            if es_viable:
                huecos = horario.contar_huecos()
                if len(combinacion_final) < max_materias:
                    continue
                if len(combinacion_final) == max_materias:
                    if dias_ocupados > menor_dias_ocupados:
                        continue
                    if dias_ocupados == menor_dias_ocupados:
                        if creditos_asignados < max_creditos or (creditos_asignados == max_creditos and huecos > menor_huecos):
                            continue
                mejor_horario = horario
                mejor_encontrado = True
                max_materias = len(combinacion_final)
                max_creditos = creditos_asignados
                menor_dias_ocupados = dias_ocupados
                menor_huecos = huecos
                materias_seleccionadas_final = [
                    (grupo.horarios[0].nombre, grupo.grupo) for grupo in combinacion_final
                ]
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