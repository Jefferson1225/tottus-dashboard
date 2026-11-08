"""Dashboard de inventario, demanda y soporte a la reposición."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.datos import ErrorDatos, cargar_csv, validar_relaciones
from src.indicadores import indicadores, preparar_resumen
from src.demanda import estimar_demanda
from src.panel_analisis import panel_reposicion, panel_evaluacion, panel_segmentacion


RAIZ = Path(__file__).resolve().parent
VERDE = '#16834b'
COLORES = {'Sin stock': '#ce5547', 'Bajo mínimo': '#d69b35',
           'En nivel mínimo': '#647fbb', 'Disponible': VERDE, 'Sin datos': '#8b9490'}
NOMBRES = {'producto_id': 'Código', 'nombre': 'Producto', 'categoria': 'Categoría',
           'unidades_vendidas': 'Unidades vendidas', 'stock_actual': 'Stock actual',
           'stock_minimo': 'Stock mínimo', 'estado': 'Estado',
           'faltante_minimo': 'Brecha al mínimo', 'fecha_corte': 'Fecha de corte'}


def grafico(tabla, especificacion):
    """Presenta gráficos con un estilo común y tooltips de los datos."""
    especificacion['config'] = {
        'view': {'stroke': None},
        'axis': {'gridColor': '#edf0ed', 'labelColor': '#64756b', 'titleColor': '#64756b'},
    }
    st.vega_lite_chart(tabla, especificacion, width='stretch', height=270)


def tabla_productos(tabla, clave):
    columnas = ['producto_id', 'nombre', 'categoria', 'stock_actual', 'stock_minimo',
                'unidades_vendidas', 'estado', 'faltante_minimo']
    visible = tabla[columnas].rename(columns=NOMBRES)

    def estilo_estado(valor):
        return f'color: {COLORES.get(str(valor), "#19342a")}; font-weight: 600'

    st.dataframe(
        visible.style.map(estilo_estado, subset=['Estado']),
        hide_index=True, width='stretch', key=clave,
        column_config={
            'Producto': st.column_config.TextColumn(width='medium'),
            'Stock actual': st.column_config.NumberColumn(format='%d'),
            'Stock mínimo': st.column_config.NumberColumn(format='%d'),
            'Unidades vendidas': st.column_config.NumberColumn(format='%d'),
            'Brecha al mínimo': st.column_config.NumberColumn(
                format='%d', help='Unidades que faltan para llegar al mínimo. No es una cantidad de compra recomendada.'),
        },
    )


def main():
    st.set_page_config(page_title='Tottus | Inventario y reposición', page_icon='🟢', layout='wide')
    st.markdown('''
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 2rem; max-width: 1540px;}
      h1, h2, h3 {letter-spacing: -.035em;}
      [data-testid="stSidebar"] {border-right: 1px solid #e3e9e1;}
      [data-testid="stMetric"] {background: white; border-radius: 14px; padding: 0;}
      [data-testid="stMetricValue"] {font-size: 2.2rem; font-weight: 650;}
      [data-testid="stMetricLabel"] {color: #63756a;}
      .hero {background: linear-gradient(110deg, #103d2c, #1d6141); color: white;
             padding: 26px 30px; border-radius: 18px; margin-bottom: 20px;}
      .hero .eyebrow {font-size: 11px; letter-spacing: .16em; color: #b6d5bd; font-weight: 700;}
      .hero h1 {font-size: 32px; color: white; margin: 8px 0; padding: 0; line-height: 1.25;}
      .hero p {color: #d8e6db; font-size: 14px; margin: 8px 0 0;}
      .brand {font-size: 30px; font-weight: 800; letter-spacing: -.06em; color: #16834b;}
      .brand-sub {font-size: 11px; letter-spacing: .12em; color: #7c8c80; margin-top: -8px; margin-bottom: 24px;}
      [data-testid="stTabs"] button {font-weight: 600;}
    </style>
    ''', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div class="brand">tottus<span style="color:#a6bd42">.</span></div>'
                    '<div class="brand-sub">SOPORTE DE DECISIONES</div>', unsafe_allow_html=True)
        st.caption('INVENTARIO · ANÁLISIS · REPOSICIÓN')
        fuente = st.radio('Fuente de información', ['Demo académica', 'Cargar mis CSV'], key='fuente')

    st.markdown('''<div class="hero"><div class="eyebrow">ABASTECIMIENTO / PANEL DE CONTROL</div>
        <h1>Inventario y reposición</h1>
        <p>Revisa tus ventas, identifica faltantes y prioriza los productos que necesitan atención.</p>
        </div>''', unsafe_allow_html=True)

    try:
        if fuente == 'Demo académica':
            tablas = {tipo: cargar_csv(RAIZ / 'data' / 'demo' / f'{tipo}.csv', tipo)
                      for tipo in ['productos', 'ventas', 'inventario']}
            st.caption('● DATOS SIMULADOS PARA FINES ACADÉMICOS · Sede de demostración · No representan operaciones reales de Tottus.')
        else:
            st.info('Carga los tres archivos del mismo ámbito de inventario. Formato: CSV UTF-8, separado por punto y coma (;).')
            columnas = st.columns(3)
            archivos = {}
            for columna, tipo in zip(columnas, ['productos', 'ventas', 'inventario']):
                with columna:
                    archivos[tipo] = st.file_uploader(f'{tipo}.csv', type='csv', key=f'archivo_{tipo}')
                    st.caption({'productos': 'producto_id; nombre; categoria',
                                'ventas': 'fecha; producto_id; unidades_vendidas',
                                'inventario': 'fecha_corte; producto_id; stock_actual; stock_minimo'}[tipo])
            if not all(archivo is not None for archivo in archivos.values()):
                st.info('El panel estará disponible cuando cargues los tres CSV. Puedes volver a la demo desde el menú lateral.')
                return
            tablas = {tipo: cargar_csv(archivo, tipo) for tipo, archivo in archivos.items()}
            st.caption('ARCHIVOS CARGADOS POR EL USUARIO · La fuente y el ámbito corresponden a los archivos seleccionados.')

        productos, ventas, inventario = (tablas[tipo] for tipo in ['productos', 'ventas', 'inventario'])
        validar_relaciones(productos, ventas, inventario)
    except ErrorDatos as error:
        st.error(str(error))
        st.caption('Corrige el archivo y vuelve a cargarlo. No se han descartado filas para calcular los resultados.')
        return

    with st.sidebar:
        st.divider()
        st.subheader('Explorar información')
        categorias = st.multiselect('Categorías', sorted(productos['categoria'].unique()),
                                    default=sorted(productos['categoria'].unique()), key='categorias')
        catalogo = productos[productos['categoria'].isin(categorias)]
        codigos = catalogo['producto_id'].tolist()
        if 'productos' in st.session_state:
            st.session_state['productos'] = [codigo for codigo in st.session_state['productos'] if codigo in codigos]
        etiquetas = catalogo.set_index('producto_id')['nombre'].to_dict()
        seleccion = st.multiselect('Productos', codigos, format_func=lambda codigo: etiquetas[codigo],
                                   placeholder='Todos los productos', key='productos')
        if seleccion:
            catalogo = catalogo[catalogo['producto_id'].isin(seleccion)]

        limites = (ventas['fecha'].min().date(), ventas['fecha'].max().date())
        periodo = st.date_input('Periodo de ventas', value=limites, min_value=limites[0], max_value=limites[1],
                                format='DD/MM/YYYY', key='periodo')
        cortes = sorted(inventario['fecha_corte'].dt.date.unique(), reverse=True)
        corte = st.selectbox('Corte de inventario', cortes, format_func=lambda fecha: fecha.strftime('%d/%m/%Y'), key='corte')
        st.caption('El periodo filtra las ventas. El stock corresponde únicamente al corte seleccionado.')
        ventana = st.selectbox('Ventana del modelo (días)', [14, 28, 42, 56], index=1, key='ventana_modelo')
        st.caption('Demanda, evaluación y segmentos usan el histórico hasta el corte de inventario, independientemente del periodo descriptivo.')
        st.divider()
        st.caption('PROTOTIPO ACADÉMICO\n\nPython · pandas · Streamlit · CSV')

    if len(periodo) != 2:
        st.info('Selecciona una fecha inicial y una fecha final para analizar las ventas.')
        return
    if catalogo.empty:
        st.info('No hay productos seleccionados. Elige al menos una categoría en el menú lateral.')
        return

    inicio, fin = periodo
    resumen = preparar_resumen(catalogo, ventas, inventario, corte, inicio, fin)
    valores = indicadores(resumen)
    st.caption(f'VENTAS: {inicio:%d/%m/%Y} — {fin:%d/%m/%Y}  /  INVENTARIO AL {corte:%d/%m/%Y}')
    columnas = st.columns(4)
    for columna, etiqueta, clave, ayuda in zip(
        columnas, ['Productos analizados', 'Unidades vendidas', 'Productos sin stock', 'Bajo stock mínimo'],
        ['productos', 'unidades', 'sin_stock', 'bajo_minimo'],
        ['Productos del catálogo con los filtros seleccionados.',
         'Suma de unidades registradas en el periodo. No es demanda estimada.',
         'Productos con stock igual a cero en el corte de inventario.',
         'Stock menor al mínimo. Puede incluir productos sin stock; no sumes ambos indicadores.'],
    ):
        columna.metric(etiqueta, f'{valores[clave]:,}'.replace(',', ' '), border=True, help=ayuda)

    if valores['sin_inventario']:
        st.warning(f'{valores["sin_inventario"]} producto(s) sin inventario en este corte. Se muestran como «Sin datos» y se excluyen de las alertas de stock.')
    sin_ventas = int(resumen['unidades_vendidas'].isna().sum())
    if sin_ventas:
        st.caption(f'{sin_ventas} producto(s) sin registros de ventas en el periodo; no se interpretan automáticamente como cero ventas.')

    general, detalle, reposicion, evaluacion, segmentos, alcance = st.tabs([
        'Vista general', 'Detalle de inventario', 'Reposición y escenarios',
        'Evaluación de demanda', 'Segmentación', 'Datos y alcance'])
    ventas_filtradas = ventas[ventas['producto_id'].isin(catalogo['producto_id']) &
                              ventas['fecha'].between(pd.Timestamp(inicio), pd.Timestamp(fin))]
    with general:
        izquierda, derecha = st.columns([1.65, 1])
        with izquierda, st.container(border=True):
            st.subheader('Evolución de ventas')
            st.caption('Unidades registradas por día · periodo seleccionado')
            diarias = ventas_filtradas.groupby('fecha', as_index=False)['unidades_vendidas'].sum()
            if diarias.empty:
                st.info('No hay registros de ventas para esta selección.')
            else:
                grafico(diarias, {
                    'mark': {'type': 'area', 'line': {'color': VERDE, 'strokeWidth': 2.5},
                             'color': {'gradient': 'linear', 'x1': 0, 'y1': 0, 'x2': 0, 'y2': 1,
                                       'stops': [{'offset': 0, 'color': '#8fcaa4'}, {'offset': 1, 'color': '#f6faf5'}]}},
                    'encoding': {
                        'x': {'field': 'fecha', 'type': 'temporal', 'title': None, 'axis': {'format': '%d/%m', 'grid': False}},
                        'y': {'field': 'unidades_vendidas', 'type': 'quantitative', 'title': 'Unidades'},
                        'tooltip': [{'field': 'fecha', 'type': 'temporal', 'title': 'Fecha', 'format': '%d/%m/%Y'},
                                    {'field': 'unidades_vendidas', 'type': 'quantitative', 'title': 'Unidades'}],
                    },
                })
        with derecha, st.container(border=True):
            st.subheader('Ventas por categoría')
            st.caption('Participación en unidades · mismo periodo')
            categoria = ventas_filtradas.merge(productos[['producto_id', 'categoria']], on='producto_id', validate='many_to_one')
            categoria = categoria.groupby('categoria', as_index=False)['unidades_vendidas'].sum()
            if not categoria.empty:
                grafico(categoria, {
                    'mark': {'type': 'bar', 'color': VERDE, 'cornerRadiusEnd': 5, 'size': 30},
                    'encoding': {
                        'y': {'field': 'categoria', 'type': 'nominal', 'sort': '-x', 'title': None, 'axis': {'labelLimit': 145}},
                        'x': {'field': 'unidades_vendidas', 'type': 'quantitative', 'title': 'Unidades'},
                        'tooltip': [{'field': 'categoria', 'title': 'Categoría'}, {'field': 'unidades_vendidas', 'title': 'Unidades'}],
                    },
                })
            else:
                st.info('No hay ventas registradas para esta selección.')

        with st.container(border=True):
            st.subheader('Productos que requieren atención')
            st.caption('Stock cero o por debajo del mínimo definido. La brecha indica el faltante frente al mínimo; no es una recomendación de compra.')
            alertas = resumen[resumen['estado'].isin(['Sin stock', 'Bajo mínimo'])]
            if alertas.empty:
                st.info('No se identificaron productos con stock cero o bajo mínimo entre los inventarios conocidos.')
            else:
                tabla_productos(alertas, 'tabla_alertas')

    with detalle:
        st.subheader('Inventario por producto')
        st.caption('Sin stock: 0 unidades · Bajo mínimo: stock < mínimo · En nivel mínimo: stock = mínimo · Disponible: stock > mínimo · Sin datos: falta inventario.')
        tabla_productos(resumen, 'tabla_inventario')
        st.download_button('Descargar detalle CSV',
                           resumen.rename(columns=NOMBRES).to_csv(index=False, sep=';').encode('utf-8-sig'),
                           file_name=f'inventario_{corte:%Y%m%d}.csv', mime='text/csv')
        st.caption('Los conteos de «sin stock» y «bajo mínimo» pueden coincidir. Los valores vacíos son desconocidos, no ceros.')
        with st.container(border=True):
            st.subheader('Stock actual frente al mínimo')
            conocidos = resumen.dropna(subset=['stock_actual']).head(10)
            if conocidos.empty:
                st.info('No hay inventario conocido para graficar.')
            else:
                barras = conocidos.melt(id_vars=['nombre'], value_vars=['stock_actual', 'stock_minimo'],
                                          var_name='medida', value_name='unidades')
                barras['medida'] = barras['medida'].map({'stock_actual': 'Stock actual', 'stock_minimo': 'Stock mínimo'})
                grafico(barras, {
                    'mark': {'type': 'bar', 'cornerRadiusEnd': 3},
                    'encoding': {
                        'y': {'field': 'nombre', 'type': 'nominal', 'title': None, 'sort': conocidos['nombre'].tolist()},
                        'x': {'field': 'unidades', 'type': 'quantitative', 'title': 'Unidades'},
                        'yOffset': {'field': 'medida'},
                        'color': {'field': 'medida', 'scale': {'domain': ['Stock actual', 'Stock mínimo'],
                                                            'range': [VERDE, '#cfad54']}, 'legend': {'title': None, 'orient': 'top'}},
                        'tooltip': [{'field': 'nombre', 'title': 'Producto'}, {'field': 'medida', 'title': 'Medida'},
                                    {'field': 'unidades', 'title': 'Unidades'}],
                    },
                })
                st.caption('Hasta 10 productos, ordenados por estado y nombre. La tabla contiene la selección completa.')

    demanda = estimar_demanda(catalogo, ventas, corte, ventana)
    with reposicion:
        panel_reposicion(demanda, inventario, corte, ventana)
    with evaluacion:
        panel_evaluacion(catalogo, ventas, corte, ventana, grafico)
    with segmentos:
        panel_segmentacion(demanda, grafico)

    with alcance:
        st.subheader('Del análisis de inventario al soporte de decisiones')
        st.write('Integramos ventas e inventario con una demanda de referencia, una política de reposición explicable y escenarios de demanda, plazo y stock. La vista general conserva sus alertas descriptivas por stock mínimo.')
        uno, dos = st.columns(2)
        with uno:
            st.markdown('**Disponible en este avance**\n\n- Datos CSV, filtros e indicadores.\n- Demanda por media móvil y evaluación temporal.\n- Punto de reorden y sugerencia explicada.\n- Comparación de escenarios What-If.\n- Segmentación K-means de productos.\n- Descarga de tablas analíticas.')
        with dos:
            st.markdown('**Siguientes mejoras**\n\n- Calibrar con datos operativos reales.\n- Validar el horizonte completo de reposición.\n- Considerar pedidos en tránsito y reservas.\n- Incorporar restricciones de compra.\n- Evaluar clasificación supervisada cuando exista un histórico de quiebres etiquetado.')
        st.divider()
        st.markdown('**Datos de demostración**')
        st.write('16 productos de 4 categorías, 1 328 registros diarios del 01/08/2026 al 22/10/2026 y un corte de inventario al 22/10/2026. Una sola sede ficticia. El stock es una fotografía preparada: este dataset no simula un libro completo de entradas y salidas.')
        st.caption('Los días ausentes en un archivo cargado no se completan con ceros. La cifra de ventas suma únicamente registros disponibles; no mide demanda no atendida ni probabilidad de quiebre.')
        with st.expander('Ver columnas requeridas y descargar CSV de ejemplo'):
            for tipo, tabla in tablas.items():
                st.markdown(f'**{tipo}.csv**')
                st.code(';'.join(tabla.columns), language=None)
                st.download_button(f'Descargar ejemplo de {tipo}',
                                   (RAIZ / 'data' / 'demo' / f'{tipo}.csv').read_bytes(),
                                   file_name=f'{tipo}.csv', mime='text/csv', key=f'ejemplo_{tipo}')
            st.caption('Fechas AAAA-MM-DD; cantidades enteras no negativas; códigos como texto. Cada combinación de producto y fecha debe ser única. No se corrigen datos inválidos silenciosamente.')

    st.divider()
    st.caption('TOTTUS · CASO ACADÉMICO / SISTEMAS DE SOPORTE DE DECISIONES · Análisis de inventario y reposición')


if __name__ == '__main__':
    main()
