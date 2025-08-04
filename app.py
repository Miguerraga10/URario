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



# Menú de carrera inicia vacío y se llena al seleccionar
st.subheader("Selecciona la carrera de la Facultad de Minas")
FACULTAD_MINAS = "FACULTAD DE MINAS"
CARRERAS_MINAS = [
    {"nombre": "Ingeniería Administrativa", "codigo": "3515"},
    {"nombre": "Ingeniería de Sistemas e Informática", "codigo": "3534"}
]
carrera_opciones = ["Selecciona una carrera..."] + [f"{c['nombre']} ({c['codigo']})" for c in CARRERAS_MINAS]
carrera_seleccionada = st.selectbox("Carrera", carrera_opciones)

materias_carrera = []
if carrera_seleccionada != "Selecciona una carrera...":
    # Extraer materias posibles según historial y prerrequisitos
    st.markdown("#### Procesa tu historial académico para ver materias disponibles")
    historial_texto = st.text_area("Pega aquí tu historial académico (texto plano del SIA)", value="", height=150)
    if st.button("Procesar historial y ver materias disponibles"):
        from Revisa_Materias import extraer_materias_aprobadas, materias_posibles_desde_historial
        materias_aprobadas = extraer_materias_aprobadas(historial_texto)
        if materias_aprobadas:
            st.success(f"Materias aprobadas extraídas: {len(materias_aprobadas)}")
            st.write(materias_aprobadas)
            # Extraer materias posibles para la carrera seleccionada
            codigo_carrera = carrera_seleccionada.split("(")[-1].replace(")","").strip()
            materias_carrera = materias_posibles_desde_historial(materias_aprobadas, codigo_carrera)
            if materias_carrera:
                st.success(f"Materias posibles para la carrera: {len(materias_carrera)}")
                for m in materias_carrera:
                    st.write(f"- {m['nombre']} ({m['codigo']})")
            else:
                st.warning("No se encontraron materias posibles para la carrera seleccionada.")
        else:
            st.warning("No se encontraron materias aprobadas en el historial.")




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
        st.markdown(f"**Nombre:** {materia_obj.nombre}")
        st.markdown(f"**Código:** {getattr(materia_obj, 'codigo', '')}")
        st.markdown(f"**Créditos:** {getattr(materia_obj, 'creditos', '')}")
        st.markdown(f"**Grupos:** {len(materia_obj.grupos)}")
        for grupo in materia_obj.grupos:
            st.markdown(f"- Grupo: {getattr(grupo, 'grupo', '')}, Cupos: {getattr(grupo, 'cupos', '')}")
            for clase in grupo.horarios:
                st.markdown(f"    - {clase.dia} {clase.hora_inicio}-{clase.hora_fin} {clase.lugar}")
        # Añadir materia procesada a la lista
        if 'materias_manuales' not in st.session_state:
            st.session_state['materias_manuales'] = []
        st.session_state['materias_manuales'].append(materia_obj)
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
st.markdown("Intervalos de horas libres (ejemplo: Lunes 10:00-12:00; Martes 14:00-16:00)")
intervalos_libres_texto = st.text_area("Intervalos libres", value="")
def parsear_intervalos_libres(texto):
    intervalos = []
    for linea in texto.split(';'):
        linea = linea.strip()
        if not linea:
            continue
        # Ejemplo: Lunes 10:00-12:00
        import re
        m = re.match(r'(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+(\d{2}:\d{2})-(\d{2}:\d{2})', linea, re.IGNORECASE)
        if m:
            dia = m.group(1).lower()
            inicio = m.group(2)
            fin = m.group(3)
            intervalos.append({'dias': [dia], 'inicio': inicio, 'fin': fin})
    return intervalos if intervalos else None
horas_libres = parsear_intervalos_libres(intervalos_libres_texto)

# Mostrar materias añadidas y posibles
st.markdown("### Materias añadidas")
materias_total = st.session_state.get('materias_manuales', [])
if materias_carrera:
    from Metodos.Metodos import extraer_informacion
    for m in materias_carrera:
        materia_obj = extraer_informacion(m['texto'], obligatoria=m.get('obligatoria', False), universidad_seleccionada="UNAL")
        if materia_obj:
            materias_total.append(materia_obj)
if materias_total:
    for m in materias_total:
        st.write(f"- {m.nombre}")
else:
    st.info("No has añadido materias aún.")

if st.button("Generar horario óptimo"):
    if materias_total:
        horario = generar_horarios(
            materias_total,
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
            for idx, materia in enumerate(materias_total):
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
