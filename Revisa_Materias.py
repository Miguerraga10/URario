import re
import json
import subprocess
import os
import unicodedata


def extraer_materias_aprobadas(texto):
    """Extrae las materias aprobadas de un texto de historial académico.
    Busca líneas que coincidan con el patrón de materia y verifica si la
    siguiente línea indica que está aprobada.

    Args:
        texto (str): Texto del historial académico.

    Returns:
        list: Lista de strings con el formato "codigo - nombre" de materias 
        aprobadas.

    """
    materias = []
    lineas = texto.split('\n')
    for i, linea in enumerate(lineas):
        # Permite cualquier texto después del periodo (no solo números)
        match = re.match(r'(.+?)\s+\((\d+-?M?)\)\s+\d+\s+.+?\s+\d{4}-\dS .+', linea)
        if match:
            if i + 1 < len(lineas) and lineas[i + 1].strip().upper().startswith('APROBADA'):
                nombre = match.group(1).strip()
                codigo = match.group(2).strip()
                materias.append(f"{codigo} - {nombre}")
    return materias


def cumple_prerrequisitos(asignatura, materias_aprobadas):
    """Verifica si una asignatura cumple con los prerrequisitos dados un
    diccionario de materias aprobadas.

    Args:
        asignatura (dict): Diccionario con información de la asignatura,
        incluyendo prerrequisitos.
        materias_aprobadas (dict): Diccionario con los códigos de materias
        aprobadas.

    Returns:

        bool: True si cumple todos los prerrequisitos, False en caso contrario.
    """
    for prereq in asignatura.get('prerequisitos', []):
        cumple = 0
        for asig in prereq.get('asignaturas', []):
            codigo = asig.get('codigo', '').lower()
            # Si es inglés, virtual o cualquier nivel de inglés, se da por cumplido si hay algún inglés aprobado
            if (
                'inglés' in asig.get('nombre', '').lower() or
                'ingles' in asig.get('nombre', '').lower() or
                'virtual' in asig.get('nombre', '').lower()
            ):
                if any('ing' in c.lower() for c in materias_aprobadas.keys()):
                    cumple += 1
                    continue
            if materias_aprobadas.get(codigo):
                cumple += 1
        if prereq.get('isTodas', False):
            if cumple < prereq.get('cantidad', 0):
                return False
        else:
            if cumple == 0:
                return False
    return True


def actualizar_materias_json(nuevas_materias, archivo="materias.json"):
    """Actualiza el archivo materias.json agregando o reemplazando materias
    por código o nombre.

    Args:
        nuevas_materias (list): Lista de diccionarios de materias nuevas
        o actualizadas.
        archivo (str): Ruta al archivo JSON a actualizar.

    """
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            existentes = json.load(f)
    except Exception:
        existentes = []
    # Crear un dict por código para reemplazo rápido
    existentes_dict = {m.get('codigo', m.get('nombre', '')): m for m in existentes}
    for nueva in nuevas_materias:
        clave = nueva.get('codigo', nueva.get('nombre', ''))
        existentes_dict[clave] = nueva
    # Guardar actualizado
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(list(existentes_dict.values()), f, ensure_ascii=False, indent=4)


def materias_posibles_desde_historial(texto):
    """Extrae materias aprobadas del texto y las retorna.

    Args:
        texto (str): Texto del historial académico.
    
    Returns:
        tuple: (materias_aprobadas, None, None)

    """
    materias_aprobadas = extraer_materias_aprobadas(texto)
    return materias_aprobadas, None, None


def normalizar_nombre(nombre):
    """Normaliza un nombre quitando acentos y convirtiendo a ASCII simple.

    Args:
        nombre (str): Nombre a normalizar.

    Returns:
        str: Nombre normalizado.

    """
    nombre = unicodedata.normalize('NFKD', nombre)
    nombre = nombre.encode('ASCII', 'ignore').decode('ASCII')
    return nombre


def buscar_json_carrera(nombre_carrera, sede):
    """Busca el archivo JSON correspondiente a una carrera y sede en el
    sistema de archivos.

    Args:
        nombre_carrera (str): Nombre de la carrera.
        sede (str): Nombre de la sede.

    Returns:
        str or None: Ruta al archivo JSON de la carrera, o None si no
        se encuentra.

    """
    # Cargar carreras.json para obtener el código
    with open(r'd:\Miguel\Universidad\Gen_Horario\sia-extractor-main\data\carreras.json', encoding='utf-8') as f:
        carreras_data = json.load(f)
    # Buscar el código de la carrera por nombre y sede
    codigo = None
    for item in carreras_data:
        if item['carrera'].strip().lower() == nombre_carrera.strip().lower() and item['sede'].strip().lower() == sede.strip().lower():
            codigo = item['codigo']
            break
    if not codigo:
        return None
    # Normalizar nombre
    def normalizar_nombre(nombre):
        nombre = unicodedata.normalize('NFKD', nombre)
        nombre = nombre.encode('ASCII', 'ignore').decode('ASCII')
        return nombre.replace(' ', '_').replace(',', '').replace('.', '').replace('-', '_').upper()
    nombre_norm = normalizar_nombre(nombre_carrera)
    # Buscar en ambas rutas posibles
    nombre_archivo = f"{codigo}_{nombre_norm}.json"
    ruta1 = os.path.join("sia-extractor-main", nombre_archivo)
    ruta2 = os.path.join("sia-extractor-main", "data", nombre_archivo)
    if os.path.exists(ruta1):
        return ruta1
    if os.path.exists(ruta2):
        return ruta2
    return None


def cargar_materias_posibles_por_carrera(nombre_carrera, materias_aprobadas):
    """Busca el archivo JSON de la carrera seleccionada, calcula materias
    posibles y actualiza materias.json y materias_posibles.json.

    Args:
        nombre_carrera (str): Nombre de la carrera.
        materias_aprobadas (list): Lista de materias aprobadas (códigos).

    Returns:
        tuple: (lista de materias posibles, ruta al archivo de la carrera)
        
    """
    archivo_carrera = None

    def normalizar_nombre_archivo(nombre):
        nombre = unicodedata.normalize('NFKD', nombre)
        nombre = nombre.encode('ASCII', 'ignore').decode('ASCII')
        nombre = nombre.replace(' ', '_').replace(',', '').replace('.', '').replace('-', '_')
        return nombre.strip().upper()

    try:
        with open("sia-extractor-main/carreras.json", encoding="utf-8") as f:
            carreras = json.load(f)
        carrera_info = next((c for c in carreras if c.get("carrera", "").strip() == nombre_carrera.strip()), None)
        if carrera_info and 'carrera' in carrera_info:
            nombre_norm = normalizar_nombre_archivo(carrera_info["carrera"])
            nombre_archivo = f"{nombre_norm}.json"
            print(f"Buscando archivo: sia-extractor-main/{nombre_archivo}")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ruta1 = os.path.join(base_dir, "sia-extractor-main", nombre_archivo)
            ruta2 = os.path.join(base_dir, "sia-extractor-main", "data", nombre_archivo)
            if os.path.exists(ruta1):
                archivo_carrera = ruta1
            elif os.path.exists(ruta2):
                archivo_carrera = ruta2
            else:
                print(f"No se encontró el archivo de la carrera en: {ruta1} ni en: {ruta2}")
                # Ejecutar extracción automática
                try:
                    cwd_actual = os.getcwd()
                    sia_dir = os.path.join(base_dir, "sia-extractor-main")
                    os.chdir(sia_dir)
                    comando = f'go run main.go extract "{carrera_info["carrera"]}"'
                    print(f"Ejecutando: {comando} en {sia_dir}")
                    resultado = subprocess.run(comando, shell=True, capture_output=True, text=True, encoding="utf-8")
                    os.chdir(cwd_actual)
                    print(resultado.stdout)
                    if resultado.stderr:
                        print("[Go STDERR]", resultado.stderr)
                    if resultado.returncode == 0 and os.path.exists(ruta1):
                        archivo_carrera = ruta1
                    elif resultado.returncode == 0 and os.path.exists(ruta2):
                        archivo_carrera = ruta2
                    else:
                        print("No se pudo generar el archivo de la carrera automáticamente.\nRevise el mensaje de error arriba y verifique el nombre/código de la carrera.")
                        return None, None
                except Exception as e:
                    print(f"Error ejecutando extracción automática: {e}")
                    try:
                        os.chdir(cwd_actual)
                    except Exception:
                        pass
                    return None, None
        else:
            print(f"No se encontró la carrera '{nombre_carrera}' en carreras.json.")
            return None, None
    except Exception as e:
        print(f"Error leyendo carreras.json: {e}")
        return None, None

    if not archivo_carrera:
        return None, None
    with open(archivo_carrera, encoding="utf-8") as f:
        data = json.load(f)
    asignaturas = data.get('asignaturas', []) if isinstance(data, dict) else data if isinstance(data, list) else []
    codigos_aprobados = set([m.split(' - ')[0] for m in materias_aprobadas])
    posibles = []
    for asignatura in asignaturas:
        if asignatura.get('codigo') in codigos_aprobados:
            continue
        if cumple_prerrequisitos(asignatura, {c: True for c in codigos_aprobados}):
            posible = {k: v for k, v in asignatura.items() if k != 'prerequisitos'}
            tipologia = asignatura.get('tipologia', '').strip().lower()
            posible['obligatoria'] = 'obligatoria' in tipologia
            if 'grupos' in posible:
                for grupo in posible['grupos']:
                    grupo['creditos'] = posible.get('creditos', 0)
                    if 'horarios' in grupo:
                        for horario in grupo['horarios']:
                            horario['materia'] = posible.get('nombre', '')
            posibles.append(posible)
    # Guardar en materias_posibles.json
    with open("materias_posibles.json", "w", encoding="utf-8") as f:
        json.dump(posibles, f, ensure_ascii=False, indent=2)
    actualizar_materias_json(posibles)
    return posibles, archivo_carrera