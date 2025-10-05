# app.py
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

st.title("Dashboard de Precios de GNV en Colombia")

# --- Carga de datos ---
ruta_gas = "Precios_Gas_MinMinas.csv"
ruta_shapefile_zip = "Colombia_Municipios_Simplificado.zip"  # ZIP con los shapefiles

# Leer shapefile desde ZIP
df_shapefile = gpd.read_file(f"zip://{ruta_shapefile_zip}")

df_gas = pd.read_csv(ruta_gas, sep=',', encoding='latin-1')
df_gas['PRECIO_PROMEDIO_PUBLICADO'] = (
    df_gas['PRECIO_PROMEDIO_PUBLICADO']
    .str.replace(',', '')
    .astype('int64')
)

# --- Preparación del shapefile ---
df_shapefile['mpio_cdpmp'] = pd.to_numeric(df_shapefile['mpio_cdpmp'], errors='coerce').fillna(0).astype(int)
df_shapefile_reducido = df_shapefile[['mpio_cdpmp', 'geometry']]

# --- Unión de datos ---
df_geografico = df_gas.merge(
    df_shapefile_reducido,
    left_on='CODIGO_MUNICIPIO_DANE',
    right_on='mpio_cdpmp',
    how='left'
)
df_geografico = gpd.GeoDataFrame(df_geografico, geometry='geometry')

# --- Mapa estático ---
st.subheader("Mapa estático (2024)")

df_gas_2024 = df_gas[df_gas["ANIO_PRECIO"] == 2024]
df_gas_2024_prom = df_gas_2024.groupby("CODIGO_MUNICIPIO_DANE")["PRECIO_PROMEDIO_PUBLICADO"].mean().reset_index()

gdf_2024 = df_shapefile_reducido.merge(
    df_gas_2024_prom,
    left_on="mpio_cdpmp",
    right_on="CODIGO_MUNICIPIO_DANE",
    how="left"
)

fig, ax = plt.subplots(1, 1, figsize=(10, 8))
gdf_2024.plot(
    column="PRECIO_PROMEDIO_PUBLICADO",
    cmap="viridis",
    linewidth=0.3,
    edgecolor="gray",
    legend=True,
    ax=ax,
    missing_kwds={"color": "lightgrey", "label": "Sin datos"}
)
ax.set_title("Precio Promedio de GNV por Municipio - 2024")
ax.axis("off")
st.pyplot(fig)

# --- Mapa dinámico interactivo ---
st.subheader("Mapa dinámico por año")

# Limpiar y agrupar datos
df_temp = (
    df_geografico
    .dropna(subset=["CODIGO_MUNICIPIO_DANE", "ANIO_PRECIO", "PRECIO_PROMEDIO_PUBLICADO", "geometry"])
    .groupby(["CODIGO_MUNICIPIO_DANE", "ANIO_PRECIO"])
    .agg({
        "PRECIO_PROMEDIO_PUBLICADO": "mean",
        "geometry": "first"
    })
    .reset_index()
)

df_temp = gpd.GeoDataFrame(df_temp, geometry="geometry", crs=df_geografico.crs)
df_temp["geometry"] = df_temp["geometry"].simplify(tolerance=0.05, preserve_topology=True)

# Slider para seleccionar el año
year_selected = st.slider(
    "Selecciona el año",
    int(df_temp["ANIO_PRECIO"].min()),
    int(df_temp["ANIO_PRECIO"].max()),
    2024
)

gdf_year = df_temp[df_temp["ANIO_PRECIO"] == year_selected]

m = folium.Map(location=[4.5, -74.1], zoom_start=6, tiles="cartodb positron")

folium.Choropleth(
    geo_data=gdf_year,
    data=gdf_year,
    columns=["CODIGO_MUNICIPIO_DANE", "PRECIO_PROMEDIO_PUBLICADO"],
    key_on="feature.properties.CODIGO_MUNICIPIO_DANE",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name="Precio promedio de GNV"
).add_to(m)

st_folium(m, width=700, height=500)
st.markdown("Fuente: Ministerio de Minas y Energía - Colombia")
