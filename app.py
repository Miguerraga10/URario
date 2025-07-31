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

# Autenticación simple por nombre de usuario
usuario = st.text_input("Usuario", value="")
if usuario:
    ruta_historial = os.path.join(directorio_usuarios, f"{usuario}_historial.json")
    ruta_materias = os.path.join(directorio_usuarios, f"{usuario}_materias.json")

    st.subheader("Carga tu historial académico")
    historial_file = st.file_uploader("Sube tu historial académico (JSON)", type=["json"])
    if historial_file:
        historial_data = json.load(historial_file)
        with open(ruta_historial, "w", encoding="utf-8") as f:
            json.dump(historial_data, f, ensure_ascii=False, indent=2)
        st.success("Historial guardado correctamente.")
    elif os.path.exists(ruta_historial):
        with open(ruta_historial, "r", encoding="utf-8") as f:
            historial_data = json.load(f)
        st.info("Historial académico cargado.")
    else:
        historial_data = None

    st.subheader("Carga tus materias posibles")
    materias_file = st.file_uploader("Sube tus materias posibles (JSON)", type=["json"])
    if materias_file:
        materias_data = json.load(materias_file)
        with open(ruta_materias, "w", encoding="utf-8") as f:
            json.dump(materias_data, f, ensure_ascii=False, indent=2)
        st.success("Materias guardadas correctamente.")
    elif os.path.exists(ruta_materias):
        with open(ruta_materias, "r", encoding="utf-8") as f:
            materias_data = json.load(f)
        st.info("Materias posibles cargadas.")
    else:
        materias_data = None
        st.warning("Debes subir el archivo de materias posibles. No se puede extraer automáticamente.")

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
else:
    st.info("Ingresa tu usuario para comenzar.")
