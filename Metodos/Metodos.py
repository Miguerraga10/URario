import re, json
from Clases.Clase import Clase
from Clases.Grupo import Grupo
from Clases.Horario import Horario
from Clases.Materia import Materia
from datetime import datetime
import locale

# Dividir horarios UdeA
def dividir_clase_udea(horario, lugar):
    dias = {"L": "LUNES", "M": "MARTES", "W": "MIÉRCOLES", "J": "JUEVES", "V": "VIERNES", "S": "SÁBADO", "D": "DOMINGO"}
    resultado = []

    # Expresión regular para capturar los días y el rango de horas
    dias_horas = re.findall(r'([LMJWVS]+)(\d+)-(\d+)', horario)

    for grupo_dias, inicio, fin in dias_horas:
        # Formatear las horas correctamente (agregar ceros si es necesario)
        inicio = f"{int(inicio):02d}:00"
        fin = f"{int(fin):02d}:00"

        for letra_dia in grupo_dias:
            dia = dias[letra_dia]
            resultado.append((dia, inicio, fin, lugar))

    return resultado


def extraer_informacion(texto, obligatoria, universidad_seleccionada):
    lineas = texto.strip().split("\n")
    if not lineas:
        return None

    if universidad_seleccionada == "UdeA":
        # --- Extracción UdeA con formato unificado ---
        # Patrón para extraer información
        patron_nombre_materia = re.compile(r'Materia: \[\d+\] (.+)')
        patron_grupo = re.compile(r'GRUPO: (\d+)')
        patron_horario = re.compile(r'HORARIO: (.+)')
        patron_cupos = re.compile(r'CUPO MÁXIMO: \d+\. CUPO DISPONIBLE: (\d+)')

        # Extraer nombre de la materia
        match_materia = patron_nombre_materia.search(texto)
        if not match_materia:
            return None
        nombre_materia = match_materia.group(1).strip() 

        grupos = []
        grupo_actual = None
        clases_actuales = []
        cupos_disponibles = 0
        for linea in lineas:
            match_grupo = patron_grupo.search(linea)
            if match_grupo:
                if grupo_actual is not None and clases_actuales:
                    grupos.append({
                        'grupo': f"Grupo {grupo_actual}",
                        'cupos': cupos_disponibles,
                        'profesor': '',
                        'duracion': '',
                        'jornada': '',
                        'horarios': [
                            {
                                'inicio': c.hora_inicio,
                                'fin': c.hora_fin,
                                'dia': c.dia,
                                'lugar': c.lugar,
                                'materia': nombre_materia
                            } for c in clases_actuales
                        ],
                        'creditos': 0
                    })
                grupo_actual = int(match_grupo.group(1))
                clases_actuales = []
                cupos_disponibles = 0
                continue
            match_horario = patron_horario.search(linea)
            if match_horario:
                horarios = match_horario.group(1).split(";")
                for horario in horarios:
                    clases_divididas = dividir_clase_udea(horario.strip(), "UdeA")
                    for dia, inicio, fin, lugar in clases_divididas:
                        clases_actuales.append(Clase(nombre_materia, f"Grupo {grupo_actual}", dia, inicio, fin, lugar))
                continue
            match_cupos = patron_cupos.search(linea)
            if match_cupos:
                cupos_disponibles = int(match_cupos.group(1))
        if grupo_actual is not None and clases_actuales:
            grupos.append({
                'grupo': f"Grupo {grupo_actual}",
                'cupos': cupos_disponibles,
                'profesor': '',
                'duracion': '',
                'jornada': '',
                'horarios': [
                    {
                        'inicio': c.hora_inicio,
                        'fin': c.hora_fin,
                        'dia': c.dia,
                        'lugar': c.lugar,
                        'materia': nombre_materia
                    } for c in clases_actuales
                ],
                'creditos': 0
            })
        # Fecha de extracción actual
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            pass
        fechaExtraccion = datetime.now().strftime('%d/%m/%Y - %I:%M %p').replace('AM', 'a. m.').replace('PM', 'p. m.')
        materia_dict = {
            "nombre": nombre_materia,
            "codigo": '',
            "tipologia": '',
            "creditos": 0,
            "facultad": '',
            "carrera": '',
            "fechaExtraccion": fechaExtraccion,
            "cuposDisponibles": 0,
            "grupos": grupos,
            "obligatoria": obligatoria
        }
        with open("materias.json", "w", encoding="utf-8") as f:
            json.dump([materia_dict], f, ensure_ascii=False, indent=4)
        return Materia(
            nombre=nombre_materia,
            codigo='',
            tipologia='',
            creditos=0,
            facultad='',
            carrera='',
            fechaExtraccion=fechaExtraccion,
            cuposDisponibles=0,
            grupos=[
                Grupo(
                    grupo=g['grupo'],
                    horarios=[
                        Clase(
                            nombre=nombre_materia,
                            dia=h.get('dia', h.get('Dia', '')),
                            hora_inicio=h.get('inicio', h.get('hora_inicio', '')),
                            hora_fin=h.get('fin', h.get('hora_fin', '')),
                            lugar=h.get('lugar', '')
                        ) for h in g['horarios']
                    ],
                    creditos=0,
                    cupos=g['cupos'],
                    profesor='',
                    duracion='',
                    jornada=''
                ) for g in grupos
            ],
            obligatoria=obligatoria
        )
    elif universidad_seleccionada == "UNAL":
        # --- Extracción robusta de campos principales ---
        nombre_materia = re.sub(r'\s?\(.*\)\s?', '', lineas[0].strip())
        codigo = re.search(r'\((\d+[\w-]*)\)', lineas[0])
        codigo = codigo.group(1) if codigo else ''
        tipologia = ''
        creditos = 0
        facultad = ''
        carrera = ''
        fechaExtraccion = ''
        cuposDisponibles = 0
        grupos = []
        grupo_actual = None
        clases_actuales = []
        cupos_actual = 0
        profesor_actual = ''
        duracion_actual = ''
        jornada_actual = ''
        horarios_actuales = []
        # Extracción de campos
        for i, l in enumerate(lineas):
            l_strip = l.strip()
            if l_strip.lower().startswith('tipología:'):
                tipologia = l_strip.split(':',1)[1].strip()
            elif l_strip.lower().startswith('créditos:'):
                creditos = int(re.search(r'(\d+)', l_strip).group(1))
                # Buscar carrera inmediatamente después de créditos
                if i+1 < len(lineas):
                    posible_carrera = lineas[i+1].strip()
                    # Si la línea no es vacía ni empieza con 'Facultad', 'CLASE', '(', 'Tipología', 'Créditos', 'Fecha', 'Profesor', 'Duración', 'Jornada', 'Cupos', 'Prerrequisitos'
                    if posible_carrera and not any([
                        posible_carrera.lower().startswith(x) for x in [
                            'facultad', 'clase', '(', 'tipología', 'créditos', 'fecha', 'profesor', 'duración', 'jornada', 'cupos', 'prerrequisitos']
                    ]):
                        carrera = posible_carrera
            # Extraer facultad de la cabecera si no se ha extraído aún
            if not facultad:
                # Buscar facultad en las primeras 5 líneas
                for j in range(min(5, len(lineas))):
                    cab = lineas[j].strip()
                    if cab.lower().startswith('facultad:'):
                        facultad = cab.split(':',1)[1].strip()
                    elif 'facultad' in cab.lower() and not cab.lower().startswith('facultad:'):
                        facultad = cab.strip()
            elif l_strip.lower().startswith('facultad:'):
                facultad = l_strip.split(':',1)[1].strip()
            elif 'facultad' in l_strip.lower() and not l_strip.lower().startswith('facultad:'):
                facultad = l_strip.strip()
            elif l_strip.lower().startswith('ingeniería') or l_strip.lower().startswith('carrera:'):
                carrera = l_strip.replace('Carrera:', '').strip()
            elif l_strip.lower().startswith('fecha:'):
                # Ignorar la fecha del texto, se usará la actual
                pass
            elif 'cupos disponibles' in l_strip.lower():
                cuposDisponibles = int(re.search(r'(\d+)', l_strip).group(1))
                cupos_actual = cuposDisponibles
            elif re.match(r'\(\d+\)\s*(GRUPO|Grupo)', l_strip, re.IGNORECASE):
                if grupo_actual is not None:
                    grupos.append({
                        'grupo': grupo_actual,
                        'cupos': cupos_actual,
                        'profesor': profesor_actual,
                        'duracion': duracion_actual,
                        'jornada': jornada_actual,
                        'horarios': [
                            {
                                'inicio': h['inicio'],
                                'fin': h['fin'],
                                'dia': h['dia'],
                                'lugar': h['lugar'],
                                'materia': nombre_materia
                            } for h in horarios_actuales
                        ],
                        'creditos': creditos
                    })
                match_num = re.match(r'\((\d+)\)', l_strip)
                if match_num:
                    # Permitir (1) Grupo 1 o (1) Grupo
                    grupo_texto = l_strip.split('Grupo',1)[-1].strip()
                    if grupo_texto and grupo_texto[0].isdigit():
                        grupo_actual = f"Grupo {grupo_texto}"
                    else:
                        grupo_actual = f"Grupo {match_num.group(1)}"
                else:
                    grupo_actual = None
                clases_actuales = []
                horarios_actuales = []
                profesor_actual = ''
                duracion_actual = ''
                jornada_actual = ''
                cupos_actual = 0
            elif l_strip.lower().startswith('profesor:'):
                profesor_actual = l_strip.split(':',1)[1].strip().rstrip('.')
            elif l_strip.lower().startswith('duración:'):
                duracion_actual = l_strip.split(':',1)[1].strip()
            elif l_strip.lower().startswith('jornada:'):
                jornada_actual = l_strip.split(':',1)[1].strip()
            elif re.match(r'^(lunes|martes|miércoles|jueves|viernes|sábado|domingo)', l_strip, re.IGNORECASE):
                m = re.match(r'^(\w+) de (\d{2}:\d{2}) a (\d{2}:\d{2})', l_strip, re.IGNORECASE)
                if m:
                    dia = m.group(1).upper()
                    inicio = m.group(2)
                    fin = m.group(3)
                    lugar = ''
                    # Buscar líneas siguientes que sean de aula/sala, aunque sean largas
                    j = i+1
                    while j < len(lineas):
                        sig = lineas[j].strip()
                        if any(x in sig.lower() for x in ['bloque', 'aula', 'sala', 'salon', 'salón']):
                            lugar = sig.rstrip('.')
                            j += 1
                        else:
                            break
                    horarios_actuales.append({
                        'inicio': inicio,
                        'fin': fin,
                        'dia': dia,
                        'lugar': lugar
                    })
            # Permitir que "Cupos disponibles" y "Duración" aparezcan en cualquier orden
            elif l_strip.lower().startswith('duración:'):
                duracion_actual = l_strip.split(':',1)[1].strip()
            elif l_strip.lower().startswith('cupos disponibles:'):
                cuposDisponibles = int(re.search(r'(\d+)', l_strip).group(1))
                cupos_actual = cuposDisponibles
        # Último grupo
        if grupo_actual is not None:
            grupos.append({
                'grupo': grupo_actual,
                'cupos': cupos_actual,
                'profesor': profesor_actual,
                'duracion': duracion_actual,
                'jornada': jornada_actual,
                'horarios': [
                    {
                        'inicio': h['inicio'],
                        'fin': h['fin'],
                        'dia': h['dia'],
                        'lugar': h['lugar'],
                        'materia': nombre_materia
                    } for h in horarios_actuales
                ],
                'creditos': creditos
            })
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            pass
        fechaExtraccion = datetime.now().strftime('%d/%m/%Y - %I:%M %p').replace('AM', 'a. m.').replace('PM', 'p. m.')
        # Construir el diccionario de la materia con el orden correcto
        materia_dict = {
            "nombre": nombre_materia,
            "codigo": codigo,
            "tipologia": tipologia,
            "creditos": creditos,
            "facultad": facultad,
            "carrera": carrera,
            "fechaExtraccion": fechaExtraccion,
            "cuposDisponibles": cuposDisponibles,
            "grupos": grupos,
            "obligatoria": obligatoria
        }
        # Guardar en materias.json
        with open("materias.json", "w", encoding="utf-8") as f:
            json.dump([materia_dict], f, ensure_ascii=False, indent=4)
        # También devolver el objeto Materia para uso interno
        return Materia(
            nombre=nombre_materia,
            codigo=codigo,
            tipologia=tipologia,
            creditos=creditos,
            facultad=facultad,
            carrera=carrera,
            fechaExtraccion=fechaExtraccion,
            cuposDisponibles=cuposDisponibles,
            grupos=[
                Grupo(
                    grupo=g['grupo'],
                    horarios=[
                        Clase(
                            nombre=nombre_materia,
                            dia=h['dia'],
                            hora_inicio=h['inicio'],
                            hora_fin=h['fin'],
                            lugar=h['lugar']
                        ) for h in g['horarios']
                    ],
                    creditos=g['creditos'],
                    cupos=g['cupos'],
                    profesor=g['profesor'],
                    duracion=g['duracion'],
                    jornada=g['jornada']
                ) for g in grupos
            ],
            obligatoria=obligatoria
        )
    else:
        raise ValueError("Universidad no reconocida. Usa 'UdeA'.")


# Guardar materias en el archivo JSON con el formato unificado

def guardar_materias(materias, archivo="materias.json"):
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump([
            {
                "nombre": m.nombre,
                "codigo": m.codigo,
                "tipologia": m.tipologia,
                "creditos": m.creditos,
                "facultad": m.facultad,
                "carrera": m.carrera,
                "fechaExtraccion": m.fechaExtraccion,
                "cuposDisponibles": m.cuposDisponibles,
                "grupos": [
                    {
                        "grupo": g.grupo,
                        "cupos": g.cupos,
                        "profesor": g.profesor,
                        "duracion": g.duracion,
                        "jornada": g.jornada,
                        "horarios": [
                            {
                                "inicio": h.hora_inicio,
                                "fin": h.hora_fin,
                                "dia": h.dia,
                                "lugar": h.lugar,
                                "materia": m.nombre
                            } for h in g.horarios
                        ],
                        "creditos": g.creditos
                    } for g in m.grupos
                ],
                "obligatoria": m.obligatoria
            } for m in materias
        ], f, ensure_ascii=False, indent=4)

# Cargar materias desde el archivo JSON con el formato unificado

def cargar_materias(archivo="materias.json"):
    with open(archivo, "r", encoding="utf-8") as f:
        data = json.load(f)
        materias = []
        for m in data:
            grupos = []
            for g in m["grupos"]:
                horarios = [
                    Clase(
                        materia=m["nombre"],
                        dia=h["dia"],
                        hora_inicio=h.get("hora_inicio", h.get("inicio")),
                        hora_fin=h.get("hora_fin", h.get("fin")),
                        lugar=h["lugar"]
                    ) for h in g["horarios"]
                ]
                grupo = Grupo(
                    grupo=g["grupo"],
                    horarios=horarios,
                    creditos=m["creditos"],
                    cupos=g["cupos"],
                    profesor=g["profesor"],
                    duracion=g["duracion"],
                    jornada=g["jornada"]
                )
                grupos.append(grupo)
            materia = Materia(
                nombre=m["nombre"],
                codigo=m["codigo"],
                tipologia=m["tipologia"],
                creditos=m["creditos"],
                facultad=m["facultad"],
                carrera=m["carrera"],
                fechaExtraccion=m["fechaExtraccion"],
                cuposDisponibles=m["cuposDisponibles"],
                grupos=grupos,
                obligatoria=m.get("obligatoria", False)
            )
            materias.append(materia)
        return materias
