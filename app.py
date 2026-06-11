# -*- coding: utf-8 -*-
"""
Panel de Análisis y Planificación — Defunciones Generales del Ecuador (INEC)
Estudio multianual 2019–2024 con estimación de demanda para abastecimiento
interhospitalario..


"""

import os
import json
import urllib.request

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import data_loader as dl

# --------------------------------------------------------------------------- #
# CONFIGURACIÓN
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Defunciones Ecuador 2019–2024",
                   page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

BASE_DIR = os.path.dirname(__file__)
GEOJSON_PATH = os.path.join(BASE_DIR, "ec_prov.geojson")
GEOJSON_URL = ("https://raw.githubusercontent.com/pabl-o-ce/"
               "Ecuador-geoJSON/master/geojson/provinces.geojson")

COLOR_HOMBRE, COLOR_MUJER = "#2E6E9E", "#C25B7C"
COLOR_SEXO = {"Hombre": COLOR_HOMBRE, "Mujer": COLOR_MUJER}
COLOR_ACENTO = "#B5482E"
COLOR_NEUTRO = "#6E7B8B"
COVID_YEARS = [2020, 2021]
ORDEN_GRUPO_EDAD = dl.ORDEN_GRUPO_EDAD


# --------------------------------------------------------------------------- #
# CARGA DE DATOS (cacheada)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Cargando y armonizando las bases 2019–2024…")
def cargar():
    df = dl.cargar_todo_online() 
    return df, df.attrs.get("faltantes", [])

@st.cache_data(show_spinner=False)
def cargar_geojson():
    """Carga el GeoJSON local; si falta, intenta descargarlo una vez."""
    try:
        if os.path.exists(GEOJSON_PATH):
            with open(GEOJSON_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        with urllib.request.urlopen(GEOJSON_URL, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        try:  # lo guardamos para próximas ejecuciones
            with open(GEOJSON_PATH, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except OSError:
            pass
        return data
    except Exception:
        return None


df, FALTANTES = cargar()
GEOJSON = cargar_geojson()

ANIOS = sorted(df["anio"].unique())
PROVINCIAS = sorted(df["provincia"].dropna().unique())


# --------------------------------------------------------------------------- #
# ENCABEZADO
# --------------------------------------------------------------------------- #
st.title("📊 Defunciones Generales del Ecuador · 2019–2024")
st.markdown(
    "Estudio multianual del Registro Estadístico de Defunciones Generales (INEC) "
    "orientado a **anticipar la demanda hospitalaria** y planificar el "
    "abastecimiento interhospitalario. Datos disponibles: "
    f"**{', '.join(str(a) for a in ANIOS)}**.")
if FALTANTES:
    st.info("Años sin archivo cargado (se omiten): " +
            ", ".join(f"{a}" for a, _ in FALTANTES) +
            ". Coloca su CSV en la carpeta para incluirlos.")


# --------------------------------------------------------------------------- #
# FILTROS GLOBALES
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header(" Filtros")
    sel_anios = st.multiselect("Años", ANIOS, default=ANIOS)
    sel_sexo = st.multiselect("Sexo", ["Hombre", "Mujer"], default=["Hombre", "Mujer"])
    sel_prov = st.multiselect("Provincia", PROVINCIAS, default=[],
                              help="Vacío = todas las provincias")
    st.divider()
    st.caption("Fuente: INEC – Ecuador en Cifras. Licencia CC-BY-4.0.")

if not sel_anios:
    st.warning("Seleccione al menos un año.")
    st.stop()

mask = df["anio"].isin(sel_anios) & df["sexo"].isin(sel_sexo)
if sel_prov:
    mask &= df["provincia"].isin(sel_prov)
dff = df[mask]
if dff.empty:
    st.warning("No hay registros con los filtros seleccionados.")
    st.stop()


# --------------------------------------------------------------------------- #
# KPIs
# --------------------------------------------------------------------------- #
c1, c2, c3, c4 = st.columns(4)
c1.metric("Defunciones (filtradas)", f"{len(dff):,}".replace(",", "."))
c2.metric("Años incluidos", f"{len(sel_anios)}")
c3.metric("Edad media", f"{dff['edad_anios'].mean():,.1f} años")
c4.metric("% violentas/externas", f"{100*dff['es_violenta'].mean():,.1f} %")
st.divider()


tab_pron, tab_geo, tab_demo = st.tabs(
    [" Tendencia y pronóstico", " Territorio", " Perfil demográfico"])


# =========================================================================== #
# TAB 1 — TENDENCIA Y PRONÓSTICO
# =========================================================================== #
with tab_pron:
    # ---- A) Totales anuales ----
    st.subheader("Evolución anual de las defunciones")
    anual = dff.groupby("anio").size().reset_index(name="defunciones")
    anual["tipo"] = np.where(anual["anio"].isin(COVID_YEARS),
                             "Año atípico (COVID-19)", "Año normal")
    figA = px.bar(anual, x="anio", y="defunciones", color="tipo", text="defunciones",
                  color_discrete_map={"Año normal": COLOR_NEUTRO,
                                      "Año atípico (COVID-19)": COLOR_ACENTO},
                  labels={"anio": "Año", "defunciones": "N.º de defunciones", "tipo": ""})
    figA.update_traces(texttemplate="%{text:,}", textposition="outside")
    figA.update_layout(height=360, margin=dict(t=10, b=10),
                       xaxis=dict(tickmode="linear"), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(figA, use_container_width=True)
    st.caption("La pandemia disparó la mortalidad en 2020–2021 (hasta ~115 mil en 2020). "
               "Esos años se marcan como atípicos porque no representan la demanda de "
               "rutina; el patrón de planificación debe basarse en años normales.")

    # ---- B) Serie mensual continua ----
    st.subheader("Serie mensual (todos los años)")
    serie = (dff.groupby(["anio", "mes_num"]).size().reset_index(name="defunciones"))
    serie["periodo"] = (serie["anio"].astype(str) + "-" +
                        serie["mes_num"].astype(str).str.zfill(2))
    serie = serie.sort_values(["anio", "mes_num"])
    figB = px.line(serie, x="periodo", y="defunciones", markers=True,
                   color_discrete_sequence=[COLOR_HOMBRE],
                   labels={"periodo": "Año-Mes", "defunciones": "Defunciones/mes"})
    figB.update_layout(height=340, margin=dict(t=10, b=10),
                       xaxis=dict(showgrid=False))
    st.plotly_chart(figB, use_container_width=True)
    st.caption("El enorme repunte de abril de 2020 (la crisis de Guayaquil) es un choque "
               "epidémico, no un patrón estacional recurrente.")

    st.divider()

    # ---- C) Pronóstico / planificación ----
    st.subheader(" Estimación de demanda y mes de abastecimiento")

    cc1, cc2, cc3 = st.columns([1.1, 1, 1])
    with cc1:
        excluir_covid = st.checkbox(
            "Excluir años atípicos (COVID 2020–2021) del patrón estacional",
            value=True)
    anios_norm = [a for a in sel_anios if a not in COVID_YEARS] if excluir_covid else sel_anios
    if len(anios_norm) == 0:
        st.warning("No quedan años para el patrón estacional. Desmarque la casilla o "
                   "incluya años normales.")
        st.stop()
    with cc2:
        target = st.slider("Año a estimar", max(sel_anios) + 1, max(sel_anios) + 6,
                           max(sel_anios) + 1)

    # patrón estacional (share mensual promedio sobre los años base)
    piv = dff[dff["anio"].isin(anios_norm)].pivot_table(
        index="anio", columns="mes_num", aggfunc="size", fill_value=0)
    for m in range(1, 13):
        if m not in piv.columns:
            piv[m] = 0
    piv = piv[sorted(piv.columns)]
    shares = piv.div(piv.sum(axis=1), axis=0)
    share = shares.mean(axis=0)
    share = share / share.sum()
    totals = piv.sum(axis=1)
    y0, y1 = min(anios_norm), max(anios_norm)
    cagr = ((totals[y1] / totals[y0]) ** (1 / (y1 - y0)) - 1) if y1 > y0 else 0.0

    with cc3:
        growth = st.slider("Crecimiento anual estimado (%)", -5.0, 10.0,
                           float(round(cagr * 100, 1)), 0.1,
                           help="Predeterminado: tasa compuesta entre el primer y "
                                "último año normal seleccionado.") / 100

    base_total = totals[y1]
    proj_total = base_total * ((1 + growth) ** (target - y1))
    monthly = (share * proj_total)

    # banda histórica (min-max mensual de años normales) escalada al total proyectado
    esc = proj_total / totals.mean()
    banda_min = piv.min(axis=0) * esc
    banda_max = piv.max(axis=0) * esc

    meses_x = [dl.NOMBRE_MES[m] for m in range(1, 13)]
    pico_mes = int(monthly.idxmax())
    abastecer = 12 if pico_mes == 1 else pico_mes - 1

    figC = go.Figure()
    figC.add_trace(go.Scatter(x=meses_x, y=[banda_max.get(m, 0) for m in range(1, 13)],
                              line=dict(width=0), showlegend=False, hoverinfo="skip"))
    figC.add_trace(go.Scatter(x=meses_x, y=[banda_min.get(m, 0) for m in range(1, 13)],
                              fill="tonexty", fillcolor="rgba(46,110,158,0.12)",
                              line=dict(width=0), name="Rango histórico (años normales)"))
    figC.add_trace(go.Scatter(x=meses_x, y=[monthly.get(m, 0) for m in range(1, 13)],
                              mode="lines+markers", line=dict(color=COLOR_HOMBRE, width=3),
                              name=f"Estimación {target}"))
    figC.add_trace(go.Scatter(x=[dl.NOMBRE_MES[pico_mes]], y=[monthly[pico_mes]],
                              mode="markers", marker=dict(color=COLOR_ACENTO, size=14,
                              symbol="star"), name="Mes pico"))
    figC.update_layout(height=400, margin=dict(t=10, b=10),
                       yaxis_title="Defunciones estimadas/mes",
                       legend=dict(orientation="h", y=1.12))
    st.plotly_chart(figC, use_container_width=True)

    # ---- Tarjetas de recomendación ----
    pico_hist = int(piv.values.max()) if piv.size else 0
    mes_normal = base_total / 12
    surge = (df.pivot_table(index="anio", columns="mes_num", aggfunc="size",
                            fill_value=0).max().max())
    ratio = surge / mes_normal if mes_normal else 0

    r1, r2, r3 = st.columns(3)
    r1.metric(f"Total estimado {target}", f"{proj_total:,.0f}".replace(",", "."),
              f"{growth*100:+.1f}% anual")
    r2.metric("Mes de mayor demanda", dl.NOMBRE_MES[pico_mes],
              f"~{monthly[pico_mes]:,.0f} defunciones".replace(",", "."))
    r3.metric("➡️ Reforzar inventario en", dl.NOMBRE_MES[abastecer],
              "el mes previo al pico")

    st.success(
        f"**Recomendación de abastecimiento.** Con base en {', '.join(map(str, anios_norm))}, "
        f"la demanda de {target} se estima en **{proj_total:,.0f}** defunciones, con su punto "
        f"más alto en **{dl.NOMBRE_MES[pico_mes]}**. Conviene **reforzar el inventario "
        f"durante {dl.NOMBRE_MES[abastecer]}**, el mes previo, para llegar abastecido al pico."
        .replace(",", "."))
    st.warning(
        f"**Reserva de contingencia.** El mayor mes registrado fue **abril de 2020 "
        f"({surge:,.0f} defunciones)**, ~**{ratio:.1f}×** un mes normal. Un plan robusto debe "
        f"poder absorber un choque epidémico de esa magnitud, no solo la demanda de rutina."
        .replace(",", "."))
    st.caption("Método: índice estacional = participación mensual promedio de los años "
               "seleccionados; el total anual se proyecta con la tasa de crecimiento "
               "indicada y se reparte por ese índice. La franja muestra el rango histórico. "
               "Es una guía de planificación con incertidumbre, no una predicción exacta.")


# =========================================================================== #
# TAB 2 — TERRITORIO (mapa + ranking)
# =========================================================================== #
with tab_geo:
    st.subheader("Distribución por provincia")
    st.caption(f"Años incluidos: {', '.join(str(a) for a in sel_anios)} "
               "(use el filtro de años de la izquierda para acotar).")

    METRICAS = {
        "Número de defunciones": ("defunciones", "YlOrRd", ":,"),
        "% muertes violentas/externas": ("pct_violenta", "OrRd", ":.1f"),
        "Edad media al fallecer": ("edad_media", "Tealgrn", ":.1f"),
    }
    sel_m = st.radio("Métrica", list(METRICAS.keys()), horizontal=True)
    col_m, escala, _ = METRICAS[sel_m]

    geo_df = (dff.groupby("prov_geo")
              .agg(defunciones=("prov_geo", "size"),
                   pct_violenta=("es_violenta", "mean"),
                   edad_media=("edad_anios", "mean")).reset_index())
    geo_df["pct_violenta"] *= 100

    t_mapa, t_rank = st.tabs([" Mapa", " Ranking"])
    with t_mapa:
        if GEOJSON is None:
            st.warning("No se pudo cargar 'ec_prov.geojson' (ni descargarlo). "
                       "Colócalo junto a app.py para ver el mapa; mientras tanto, usa el Ranking.")
        else:
            try:
                figM = px.choropleth(
                    geo_df, geojson=GEOJSON, locations="prov_geo",
                    featureidkey="properties.province", color=col_m,
                    color_continuous_scale=escala, hover_name="prov_geo",
                    hover_data={"prov_geo": False, "defunciones": ":,",
                                "pct_violenta": ":.1f", "edad_media": ":.1f"},
                    labels={"defunciones": "Defunciones", "pct_violenta": "% violentas",
                            "edad_media": "Edad media"})
                figM.update_geos(fitbounds="locations", visible=False)
                figM.update_layout(height=560, margin=dict(t=10, b=10, l=0, r=0),
                                   coloraxis_colorbar_title_text="")
                st.plotly_chart(figM, use_container_width=True)
                st.caption("Mapa coroplético: el color codifica la métrica elegida y la "
                           "posición responde el «¿dónde?». Pase el cursor para ver el detalle.")
            except Exception as e:
                st.error(f"No se pudo dibujar el mapa ({e}). Se muestra el ranking.")
    with t_rank:
        top_n = st.slider("Mostrar N provincias", 5, 24, 12, key="rank_n")
        rank = geo_df.sort_values(col_m, ascending=True).tail(top_n)
        figR = px.bar(rank, x=col_m, y="prov_geo", orientation="h", color=col_m,
                      color_continuous_scale=escala,
                      labels={col_m: sel_m, "prov_geo": "Provincia"})
        figR.update_layout(height=max(360, 26*top_n), coloraxis_showscale=False,
                           margin=dict(t=10, b=10))
        st.plotly_chart(figR, use_container_width=True)
        st.caption("Barras ordenadas: permiten comparar el valor exacto entre provincias.")


# =========================================================================== #
# TAB 3 — PERFIL DEMOGRÁFICO
# =========================================================================== #
with tab_demo:
    st.subheader("Estructura por edad y sexo")
    pir = (dff.dropna(subset=["grupo_edad"])
           .groupby(["grupo_edad", "sexo"]).size().reset_index(name="n"))
    ph = pir[pir.sexo == "Hombre"].set_index("grupo_edad")["n"].reindex(ORDEN_GRUPO_EDAD).fillna(0)
    pm = pir[pir.sexo == "Mujer"].set_index("grupo_edad")["n"].reindex(ORDEN_GRUPO_EDAD).fillna(0)
    figP = go.Figure()
    figP.add_bar(y=ORDEN_GRUPO_EDAD, x=-ph.values, name="Hombre", orientation="h",
                 marker_color=COLOR_HOMBRE, customdata=ph.values,
                 hovertemplate="Hombre %{y}: %{customdata:,}<extra></extra>")
    figP.add_bar(y=ORDEN_GRUPO_EDAD, x=pm.values, name="Mujer", orientation="h",
                 marker_color=COLOR_MUJER,
                 hovertemplate="Mujer %{y}: %{x:,}<extra></extra>")
    mx = max(ph.max(), pm.max()) if len(ph) else 1
    figP.update_layout(barmode="relative", height=440, bargap=0.12,
                       xaxis=dict(title="Hombres ◄ | ► Mujeres",
                                  tickvals=np.linspace(-mx, mx, 7),
                                  ticktext=[f"{abs(int(v)):,}" for v in np.linspace(-mx, mx, 7)]),
                       yaxis=dict(title="Grupo de edad"),
                       legend=dict(orientation="h", y=1.05), margin=dict(t=10, b=10))
    st.plotly_chart(figP, use_container_width=True)

    st.subheader("Muertes violentas / externas por año")
    viol = (dff[dff["es_violenta"]].groupby("anio").size().reset_index(name="violentas")
            .merge(dff.groupby("anio").size().reset_index(name="total"), on="anio"))
    viol["pct"] = 100 * viol["violentas"] / viol["total"]
    figV = px.bar(viol, x="anio", y="violentas", text="violentas",
                  color_discrete_sequence=[COLOR_ACENTO],
                  labels={"anio": "Año", "violentas": "Muertes violentas/externas"})
    figV.update_traces(texttemplate="%{text:,}", textposition="outside")
    figV.update_layout(height=340, margin=dict(t=10, b=10), xaxis=dict(tickmode="linear"))
    st.plotly_chart(figV, use_container_width=True)
    st.caption("Las muertes externas demandan recursos forenses y de patología; su volumen "
               "por año ayuda a dimensionar esa capacidad específica.")
