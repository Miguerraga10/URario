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


# Menú solo Facultad de Minas y carreras específicas
st.subheader("Selecciona la carrera de la Facultad de Minas")
FACULTAD_MINAS = "FACULTAD DE MINAS"
CARRERAS_MINAS = [
    {"nombre": "Ingeniería Administrativa", "codigo": "3515"},
    {"nombre": "Ingeniería de Sistemas e Informática", "codigo": "3534"}
]
carrera_opciones = [f"{c['nombre']} ({c['codigo']})" for c in CARRERAS_MINAS]
carrera_seleccionada = st.selectbox("Carrera", carrera_opciones)



st.subheader("Carga tu historial académico manualmente")
historial_texto = st.text_area("Pega aquí tu historial académico (texto plano del SIA)", value="", height=150)
if st.button("Procesar historial académico"):
    from Revisa_Materias import extraer_materias_aprobadas
    materias_aprobadas = extraer_materias_aprobadas(historial_texto)
    if materias_aprobadas:
        st.success(f"Materias aprobadas extraídas: {len(materias_aprobadas)}")
        st.write(materias_aprobadas)
    else:
        st.warning("No se encontraron materias aprobadas en el historial.")



st.subheader("Añade una materia manualmente")
materia_texto = st.text_area("Pega aquí la información de la materia (texto plano del SIA)", value="", height=150)
universidad_materia = st.radio("Universidad de la materia", ["UNAL", "UdeA"])
if st.button("Procesar materia"):
    from Metodos.Metodos import extraer_informacion
    materia_obj = extraer_informacion(materia_texto, obligatoria=False, universidad_seleccionada=universidad_materia)
    if materia_obj:
        st.success(f"Materia procesada: {materia_obj.nombre}")
        st.write(materia_obj)
    else:
        st.error("No se pudo procesar la materia. Verifica el formato del texto.")


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

    # Permitir agregar varias materias manualmente
    if 'materias_manuales' not in st.session_state:
        st.session_state['materias_manuales'] = []

    if st.button("Agregar materia a la lista"):
        if 'materia_obj' in locals() and materia_obj:
            st.session_state['materias_manuales'].append(materia_obj)
            st.success(f"Materia '{materia_obj.nombre}' añadida a la lista.")
        else:
            st.warning("Primero procesa una materia válida.")

    st.markdown("### Materias añadidas")
    if st.session_state['materias_manuales']:
        for m in st.session_state['materias_manuales']:
            st.write(f"- {m.nombre}")
    else:
        st.info("No has añadido materias aún.")

    if st.button("Generar horario óptimo"):
        materias_objs = st.session_state['materias_manuales']
        if materias_objs:
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
            st.error("Debes añadir materias primero.")
