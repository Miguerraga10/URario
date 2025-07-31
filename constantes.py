# Archivo de constantes y configuraciones compartidas
import json
import os

# Cargar carreras y facultades de UNAL solo una vez
DATA_PATH = os.path.join(os.path.dirname(__file__), 'sia-extractor-main', 'data', 'carreras.json')
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"No se encontró el archivo de carreras en {DATA_PATH}. Por favor, verifica la ruta y que el archivo exista.")
with open(DATA_PATH, encoding='utf-8') as f:
    carreras_data = json.load(f)

facultades_unal = sorted(set(item['facultad'] for item in carreras_data))
carreras_por_facultad = {}
for item in carreras_data:
    fac = item['facultad']
    if fac not in carreras_por_facultad:
        carreras_por_facultad[fac] = []
    carreras_por_facultad[fac].append(item['carrera'])

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

# Guardar carreras y facultades en archivos JSON
with open(r'd:\Miguel\Universidad\Gen_Horario\Datos\facultades_unal.json', 'w', encoding='utf-8') as f:
    json.dump(facultades_unal, f, ensure_ascii=False, indent=2)

with open(r'd:\Miguel\Universidad\Gen_Horario\Datos\carreras_por_facultad.json', 'w', encoding='utf-8') as f:
    json.dump(carreras_por_facultad, f, ensure_ascii=False, indent=2)

with open(r'd:\Miguel\Universidad\Gen_Horario\Datos\niveles_unal.json', 'w', encoding='utf-8') as f:
    json.dump(niveles_unal, f, ensure_ascii=False, indent=2)

with open(r'd:\Miguel\Universidad\Gen_Horario\Datos\sedes_unal.json', 'w', encoding='utf-8') as f:
    json.dump(sedes_unal, f, ensure_ascii=False, indent=2)
