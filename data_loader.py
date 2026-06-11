# -*- coding: utf-8 -*-
"""
data_loader.py — Carga y armoniza las bases anuales de Defunciones Generales
del INEC (2019, 2020, 2021 y 2024) directamente desde internet, manejando las
diferencias de codificación y formato entre años en una sola tabla limpia.
"""

import io
import zipfile
import requests
import pandas as pd

# Mapeo de URLs de descarga directa desde el servidor oficial del INEC
URLS_INEC = {
    2019: "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/Defunciones_Generales_2019/2.%20Datos_abiertos_EDG_2019.zip",
    2020: "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/Defunciones_Generales_2020/BBD_EDG_2020_CSV_v1.zip",
    2021: "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/Defunciones_Generales_2021/2.%20Datos_abiertos_EDG_2021.zip",
    2024: "https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/Defunciones_Generales/2024/2.%20Datos_abiertos_EDG_2024.zip"
}

MES_NOMBRE = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5,
              "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9,
              "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
NOMBRE_MES = {v: k for k, v in MES_NOMBRE.items()}

# --- DICCIONARIOS DE DECODIFICACIÓN EXCLUSIVOS PARA LA BASE 2019 ---
SEXO_2019 = {"1": "Hombre", "2": "Mujer"}
CODEDAD_2019 = {"1": "Horas", "2": "Días", "3": "Meses", "4": "Años", "9": "Sin información"}
PROV_2019 = {
    "01": "Azuay", "02": "Bolívar", "03": "Cañar", "04": "Carchi", "05": "Cotopaxi",
    "06": "Chimborazo", "07": "El Oro", "08": "Esmeraldas", "09": "Guayas",
    "10": "Imbabura", "11": "Loja", "12": "Los Ríos", "13": "Manabí",
    "14": "Morona Santiago", "15": "Napo", "16": "Pastaza", "17": "Pichincha",
    "18": "Tungurahua", "19": "Zamora Chinchipe", "20": "Galápagos",
    "21": "Sucumbíos", "22": "Orellana", "23": "Santo Domingo de los Tsáchilas",
    "24": "Santa Elena"
}

# --- MAPEOS PARA ARMONIZAR TEXTO EN 2020, 2021 Y 2024 ---
# Evita la duplicación por diferencias de tildes o mayúsculas entre publicaciones anuales
NORMALIZA_PROV = {
    "Galapagos": "Galápagos",
    "Santo Domingo De Los Tsachilas": "Santo Domingo de los Tsáchilas",
    "Santo Domingo de los Tsachilas": "Santo Domingo de los Tsáchilas",
    "SANTO DOMINGO DE LOS TSÁCHILAS": "Santo Domingo de los Tsáchilas",
    "SANTA ELENA": "Santa Elena",
    "GUAYAS": "Guayas",
    "PICHINCHA": "Pichincha",
    "MANABÍ": "Manabí",
    "AZUAY": "Azuay"
}

ORDEN_GRUPO_EDAD = ["<1", "1-4", "5-14", "15-24", "25-34", "35-44",
                    "45-54", "55-64", "65-74", "75-84", "85+"]


def _mes_a_num(serie: pd.Series) -> pd.Series:
    """Convierte el mes de fallecimiento a número entero, soportando texto o dígitos."""
    s = serie.astype(str).str.strip()
    num = pd.to_numeric(s, errors="coerce")
    return num.fillna(s.map(MES_NOMBRE))


def cargar_anio_online(url: str, anio: int) -> pd.DataFrame:
    """
    Descarga el archivo comprimido desde el servidor del INEC, extrae el CSV 
    en memoria (sin escribir en disco) y armoniza las variables del año correspondiente.
    """
    try:
        respuesta = requests.get(url, timeout=45)
        respuesta.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(respuesta.content)) as z:
            # Localiza de forma dinámica el archivo CSV dentro del paquete ZIP
            archivo_csv = [f for f in z.namelist() if f.lower().endswith('.csv')][0]
            
            with z.open(archivo_csv) as f:
                df = pd.read_csv(f, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
                
    except Exception as e:
        print(f"⚠️ Alerta: No se pudo procesar el año {anio} desde internet. Motivo: {e}")
        return pd.DataFrame()

    # Limpieza de espacios accidentales en los nombres de las columnas
    df.columns = [c.strip() for c in df.columns]

    # Filtro de consistencia: Descartar registros inscritos de forma tardía
    df = df[df["anio_fall"].astype(str).str.strip() == str(anio)].copy()

    if df.empty:
        return pd.DataFrame()

    out = pd.DataFrame(index=df.index)
    out["anio"] = anio
    out["mes_num"] = _mes_a_num(df["mes_fall"])

    # --- INICIO DEL MAPEO ESPECÍFICO POR AÑO ---
    if anio == 2019:
        # 2019 utiliza catálogos numéricos rígidos
        out["sexo"] = df["sexo"].map(SEXO_2019)
        cod_edad = df["cod_edad"].map(CODEDAD_2019)
        prov = df["prov_fall"].map(PROV_2019)
    else:
        # 2020, 2021 y 2024 registran cadenas de texto literales. Normalizamos texto.
        out["sexo"] = df["sexo"].str.strip().str.capitalize()
        cod_edad = df["cod_edad"].str.strip().str.capitalize()
        # Conservar el formato título para provincias (ej. "Guayas", "Los Ríos")
        prov = df["prov_fall"].str.strip().str.title()

    # Resolver inconsistencias ortográficas de las provincias entre años
    out["provincia"] = prov.replace(NORMALIZA_PROV)

    # --- INGENIERÍA DE DATOS: EDAD UNIFICADA EN AÑOS ---
    edad_num = pd.to_numeric(df["edad"], errors="coerce")
    factor = cod_edad.map({"Años": 1, "Anios": 1, "Meses": 1/12, "Días": 1/365, "Dias": 1/365, "Horas": 1/8760})
    out["edad_anios"] = edad_num * factor

    # --- INGENIERÍA DE DATOS: IDENTIFICADOR DE MUERTE EXTERNA/VIOLENTA ---
    # Si contiene una etiqueta válida de causa externa (no vacía o sin información), es True
    mor_viol_limpio = df["mor_viol"].astype(str).str.strip()
    out["es_violenta"] = ~mor_viol_limpio.isin(["", "nan", "Sin información", "No asistida", "9"])

    # Campo secundario de entorno geográfico (si existe en la estructura anual)
    out["area_fall"] = df["area_fall"].str.strip().str.capitalize() if "area_fall" in df.columns else ""
    
    # Eliminación de filas sin índice de mes válido
    out = out.dropna(subset=["mes_num"])
    out["mes_num"] = out["mes_num"].astype(int)
    
    return out


def cargar_todo_online() -> pd.DataFrame:
    """
    Recorre los endpoints del INEC, descarga la data histórica de 2019 a 2024,
    la unifica en un solo dataframe estructurado y calcula campos globales.
    """
    partes = []
    faltantes = []
    
    for anio, url in URLS_INEC.items():
        print(f"Conectando al servidor del INEC para obtener el año {anio}...")
        df_anio = cargar_anio_online(url, anio)
        if not df_anio.empty:
            partes.append(df_anio)
            print(f"✅ Año {anio} procesado exitosamente ({len(df_anio):,} registros).")
        else:
            faltantes.append((anio, url))
            
    if not partes:
        raise FileNotFoundError("Error crítico: No se pudo descargar ninguna base de datos desde internet.")
        
    df = pd.concat(partes, ignore_index=True)

    # Variables de control global calculadas post-unión
    df["mes_nombre"] = df["mes_num"].map(NOMBRE_MES)
    df["grupo_edad"] = pd.cut(
        df["edad_anios"],
        bins=[-0.01, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85, 200],
        labels=ORDEN_GRUPO_EDAD
    )
    df["prov_geo"] = df["provincia"].replace({"Santo Domingo de los Tsáchilas": "Santo Domingo"})
    df.attrs["faltantes"] = faltantes
    
    return df


if __name__ == "__main__":
    # Test local de integración
    try:
        data_consolidada = cargar_todo_online()
        print("\n" + "="*50)
        print("  REPORTE DE INTEGRACIÓN HISTÓRICA MULTI-AÑO  ")
        print("="*50)
        print(f"Total registros en memoria RAM: {len(data_consolidada):,}")
        
        print("\nDefunciones reales por año (excluyendo registros tardíos):")
        print(data_consolidada.groupby("anio").size().to_string())
        
        print("\nVerificación de consistencia de variables (Sexo):")
        print(data_consolidada["sexo"].value_counts().to_string())
        
        print("\nProporción de eventos por causa externa / violenta:")
        conteo_violenta = data_consolidada["es_violenta"].value_counts(normalize=True) * 100
        print(conteo_violenta.to_string(format_func=lambda x: f"{x:.2f}%"))
        
        if data_consolidada.attrs["faltantes"]:
            print("\n⚠️ Servidores no disponibles en el intento actual para:", data_consolidada.attrs["faltantes"])
            
    except Exception as e:
        print(f"❌ Error durante la prueba de ejecución: {e}")