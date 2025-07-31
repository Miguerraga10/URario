import streamlit as st
import json
import os
import textwrap
from M10horariosplus import generar_horarios, obtener_facultades_por_sede, obtener_carreras_por_facultad_nivel_sede
from Clases.Materia import Materia
from Clases.Grupo import Grupo
from Clases.Clase import Clase
def colores_futuristas():
    return [
        "#00fff7", "#ff00ea", "#39ff14", "#faff00", "#ff005b",
        "#00b3ff", "#ff9100", "#a020f0", "#00ff85", "#ff61a6"
    ]

def color_futuro(materia, colores_materias, paleta, usar_colores=True):
    if not usar_colores or not materia:
        return "#222831"
    if materia not in colores_materias:
        colores_materias[materia] = paleta[len(colores_materias) % len(paleta)]
    return colores_materias[materia]

# Carpeta donde se guardan los historiales de cada usuario
directorio_usuarios = "usuarios"
os.makedirs(directorio_usuarios, exist_ok=True)

st.set_page_config(page_title="Generador de Horarios UNAL", layout="wide")
st.title("Generador de Horarios UNAL")

from constantes import sedes_unal, carreras_por_facultad

st.subheader("Selecciona la sede y carrera")
sede_seleccionada = st.selectbox("Sede", [s for s in sedes_unal if "MEDELLÍN" in s])
facultades = sorted(carreras_por_facultad.keys())
facultad_seleccionada = st.selectbox("Facultad", facultades)
carreras = carreras_por_facultad.get(facultad_seleccionada, [])
carrera_seleccionada = st.selectbox("Carrera", carreras)

st.subheader("Carga tu historial académico manualmente")
historial_texto = st.text_area("Pega aquí tu historial académico (formato JSON o texto estructurado)", value="", height=150)
if st.button("Procesar historial académico"):
    try:
        historial_data = json.loads(historial_texto)
        st.success("Historial académico procesado correctamente.")
    except Exception as e:
        st.error(f"Error al procesar el historial: {e}")
        historial_data = None
else:
    historial_data = None

st.subheader("Carga tus materias posibles manualmente")
materias_texto = st.text_area("Pega aquí tus materias posibles (formato JSON o texto estructurado)", value="", height=150)
if st.button("Procesar materias posibles"):
    try:
        materias_data = json.loads(materias_texto)
        st.success("Materias procesadas correctamente.")
    except Exception as e:
        st.error(f"Error al procesar las materias: {e}")
        materias_data = None
else:
    materias_data = None

    # Parámetros para generar horarios
    st.subheader("Parámetros de generación de horario")
    mincreditos = st.number_input("Créditos mínimos", min_value=0, value=8)
    maxcreditos = st.number_input("Créditos máximos", min_value=0, value=24)
    minmaterias = st.number_input("Materias mínimas", min_value=1, value=1)
    maxmaterias = st.number_input("Materias máximas", min_value=1, value=7)
    hora_inicio = st.text_input("Hora inicio", value="08:00")
    hora_fin = st.text_input("Hora fin", value="20:00")
    usar_cupos = st.checkbox("Solo grupos con cupos disponibles", value=False)
    maxdias = st.number_input("Máximo de días ocupados", min_value=1, value=7)
    usar_virtuales = st.checkbox("Permitir materias virtuales", value=True)
    horas_libres = st.text_area("Intervalos de horas libres (JSON)", value="[]")
    try:
        horas_libres = json.loads(horas_libres)
    except:
        horas_libres = None
        st.warning("Formato de horas libres inválido. Usa una lista de dicts.")

    def dict_to_obj_materias(materias_data):
        materias_objs = []
        for m in materias_data:
            grupos_objs = []
            for g in m.get('grupos', []):
                clases_objs = [Clase(**c) for c in g.get('clases', [])]
                grupo_obj = Grupo(
                    grupo=g.get('grupo'),
                    cupos=g.get('cupos', 0),
                    horarios=clases_objs,
                    clases=clases_objs,
                    creditos=g.get('creditos', m.get('creditos', 0))
                )
                grupos_objs.append(grupo_obj)
            materia_obj = Materia(
                nombre=m.get('nombre'),
                creditos=m.get('creditos', 0),
                grupos=grupos_objs,
                obligatoria=m.get('obligatoria', False)
            )
            materias_objs.append(materia_obj)
        return materias_objs

    if st.button("Generar horario óptimo"):
        if materias_data:
            materias_objs = dict_to_obj_materias(materias_data)
            horario = generar_horarios(
                materias_objs,
                mincreditos=mincreditos,
                maxcreditos=maxcreditos,
                minmaterias=minmaterias,
                maxmaterias=maxmaterias,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                usar_cupos=usar_cupos,
                maxdias=maxdias,
                usar_virtuales=usar_virtuales,
                horas_libres=horas_libres
            )
            if horario:
                st.success("Horario generado correctamente.")
                # Visualización dinámica de horario
                colores_materias = {}
                paleta = colores_futuristas()
                dias_con_clases = [dia for dia in horario.dias if any(horario.dias[dia].values())]
                todas_las_horas = horario.horas() if hasattr(horario, 'horas') else []
                horas_con_clases = [hora for hora in todas_las_horas if any(horario.dias[dia].get(hora) for dia in dias_con_clases)]
                if horas_con_clases:
                    horas_rango = todas_las_horas[todas_las_horas.index(horas_con_clases[0]):todas_las_horas.index(horas_con_clases[-1]) + 1]
                else:
                    horas_rango = []
                # Construir tabla estilo horario
                st.markdown("## Horario generado")
                if dias_con_clases and horas_rango:
                    import pandas as pd
                    horario_df = pd.DataFrame(index=horas_rango, columns=dias_con_clases)
                    for dia in dias_con_clases:
                        for hora in horas_rango:
                            clase = horario.dias[dia].get(hora)
                            if clase:
                                horario_df.at[hora, dia] = clase.nombre
                            else:
                                horario_df.at[hora, dia] = ""
                    def color_cells(val):
                        return f'background-color: {color_futuro(val, colores_materias, paleta)}; color: #fff;' if val else ''
                    st.dataframe(horario_df.style.applymap(color_cells))
                else:
                    st.info("No hay clases asignadas en el horario.")
                # Selector de grupos dinámico
                st.markdown("### Selección de grupos por materia")
                columnas = st.columns(4)
                materias_seleccionadas_dict = {}
                for idx, materia in enumerate(materias_objs):
                    grupos_fuente = getattr(materia, 'grupos_originales', materia.grupos)
                    grupos_disponibles = [str(grupo.grupo) for grupo in grupos_fuente]
                    valor_defecto = grupos_disponibles[0] if grupos_disponibles else ""
                    with columnas[idx % 4]:
                        seleccion = st.selectbox(f"{materia.nombre}", grupos_disponibles, index=0 if valor_defecto else -1, key=f"grupo_{materia.nombre}")
                        materias_seleccionadas_dict[materia.nombre] = seleccion
                # Mostrar resumen de selección
                st.markdown("#### Resumen de selección de grupos")
                resumen = pd.DataFrame(list(materias_seleccionadas_dict.items()), columns=["Materia", "Grupo seleccionado"])
                st.dataframe(resumen)
            else:
                st.error("No se pudo generar un horario óptimo.")
        else:
            st.error("Debes cargar tus materias posibles primero.")
