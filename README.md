# Panel de Defunciones Generales del Ecuador · 2019–2024
### Estudio multianual con estimación de demanda para abastecimiento interhospitalario

Aplicación interactiva (Streamlit + Plotly) que armoniza varias bases anuales del INEC,
analiza la tendencia de la mortalidad y **estima en qué mes conviene reforzar el inventario**
hospitalario ante el incremento esperado de defunciones.

## Archivos necesarios en la carpeta

```
app.py                 ← interfaz del panel (3 pestañas)
data_loader.py         ← carga y ARMONIZA las bases anuales (formatos distintos por año)
ec_prov.geojson        ← límites de las 24 provincias (mapa); si falta, se intenta descargar
requirements.txt

# Bases de datos del INEC (una por año):
BDD_EDG_2019.csv
EDG_2020_CSV_v1.csv
EDG_2021_CSV.csv
EDG_2024_CSV.csv
```

Para añadir más años (p. ej. 2022, 2023), descarga su CSV del INEC, colócalo en la carpeta
y registra `año: nombre_archivo.csv` en el diccionario `ARCHIVOS` de `data_loader.py`.
Fuente: https://www.ecuadorencifras.gob.ec/defunciones-generales-y-fetales-bases-de-datos/

## Cómo ejecutarlo en VSCode

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Qué hace cada pestaña

1. **📈 Tendencia y pronóstico** — totales anuales (marca los años COVID como atípicos),
   serie mensual continua, y la **estimación de demanda**: proyecta el total del próximo
   año y lo reparte con un índice estacional para señalar el **mes pico** y el **mes en que
   conviene abastecerse** (el previo al pico), más una **reserva de contingencia** basada en
   el peor mes histórico (abril 2020).
2. **🗺️ Territorio** — mapa coroplético + ranking por provincia, con selector de métrica
   (defunciones, % violentas, edad media).
3. **👥 Perfil demográfico** — pirámide por edad y sexo, y muertes violentas por año.

## Notas técnicas (armonización)

Las bases del INEC **no son homogéneas entre años**:
- **2019** viene codificada con números (sexo 1/2, provincia 01–24, mes 1–12, unidad de edad
  1–9); `data_loader.py` la decodifica a etiquetas usando la codificación DPA del INEC.
- **2020/2021/2024** usan etiquetas de texto, pero difieren en el orden de columnas y en
  detalles de escritura (p. ej. «Galapagos» vs «Galápagos»), que también se normalizan.
- Cada archivo se filtra a su propio año (`anio_fall`) para no duplicar inscripciones tardías.

**Importante sobre el pronóstico:** 2020 y 2021 fueron años de pandemia con picos atípicos
(abril 2020 ≈ 21 mil defunciones). Por defecto se **excluyen del patrón estacional** para no
predecir un falso pico de abril; puede incluirlos con la casilla correspondiente para ver el
contraste. La estimación es una guía de planificación con incertidumbre, no una predicción exacta.
