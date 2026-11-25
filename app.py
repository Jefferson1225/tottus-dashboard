"""Dashboard de inventario, demanda y soporte a la reposición."""

from base64 import b64encode
from pathlib import Path

import pandas as pd
import streamlit as st

from src.datos import ErrorDatos, cargar_csv, validar_relaciones
from src.indicadores import indicadores, preparar_resumen
from src.demanda import estimar_demanda
from src.panel_analisis import panel_reposicion, panel_escenarios, panel_evaluacion, panel_segmentacion
from src.panel_quiebres import panel_quiebres


RAIZ = Path(__file__).resolve().parent
DATOS_EJEMPLO = RAIZ / 'data' / 'demo'
VERDE = '#16834b'
COLORES = {'Sin stock': '#ce5547', 'Bajo mínimo': '#d69b35',
           'En nivel mínimo': '#647fbb', 'Disponible': VERDE, 'Sin datos': '#8b9490'}
CONTROLES_ANALISIS = {
    'Evaluación de demanda': ('horizonte_demanda', 'producto_evaluacion'),
    'Alertas de quiebre': ('modelo_quiebres', 'umbral_quiebres', 'curva_quiebres'),
    'Segmentación': ('metodo_segmentacion', 'grupos_kmeans'),
}
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
    logo_svg = b64encode((RAIZ / 'assets' / 'tottus.svg').read_bytes()).decode('ascii')
    logo = f'<img class="tottus-logo" src="data:image/svg+xml;base64,{logo_svg}" alt="Tottus">'
    st.markdown('''
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 2rem; max-width: 1540px;}
      h1, h2, h3 {letter-spacing: -.035em;}
      [data-testid="stSidebar"] {border-right: 1px solid #e3e9e1;}
      [data-testid="stMetric"] {background: white; border-radius: 14px; padding: 0;}
      [data-testid="stMetricValue"] {font-size: 2.2rem; font-weight: 650;}
      [data-testid="stMetricLabel"] {color: #63756a;}
      .hero {background: linear-gradient(110deg, #103d2c, #1d6141); color: white;
             padding: 26px 30px; border-radius: 18px; margin-bottom: 20px;
             display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;}
      .hero .eyebrow {font-size: 11px; letter-spacing: .16em; color: #b6d5bd; font-weight: 700;}
      .hero h1 {font-size: 32px; color: white; margin: 8px 0; padding: 0; line-height: 1.25;}
      .hero p {color: #d8e6db; font-size: 14px; margin: 8px 0 0;}
      .tottus-logo {display: block; width: 160px; max-width: 100%; height: auto;}
      .hero .tottus-logo {box-sizing: content-box; padding: 14px 16px; background: white; border-radius: 12px;}
      .brand-sub {font-size: 11px; letter-spacing: .12em; color: #63756a; margin: 10px 0 18px;}
      [data-testid="stTabs"] button {font-weight: 600;}
    </style>
    ''', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f'{logo}<div class="brand-sub">SOPORTE DE DECISIONES</div>', unsafe_allow_html=True)
        st.caption('INVENTARIO · ANÁLISIS · REPOSICIÓN')
        fuente = st.radio('Fuente de información', ['Datos de ejemplo', 'Cargar mis CSV'], key='fuente')

    st.markdown(f'''<div class="hero"><div><div class="eyebrow">ABASTECIMIENTO / PANEL DE CONTROL</div>
        <h1>Inventario y reposición</h1>
        <p>Revisa tus ventas, identifica faltantes y prioriza los productos que necesitan atención.</p>
        </div>{logo}</div>''', unsafe_allow_html=True)

    try:
        if fuente == 'Datos de ejemplo':
            tablas = {tipo: cargar_csv(DATOS_EJEMPLO / f'{tipo}.csv', tipo)
                      for tipo in ['productos', 'ventas', 'inventario']}
            st.caption('Catálogo público de Tottus Perú · Ventas e inventario simulados para una sede de Lima.')
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
                st.info('Carga los tres CSV para ver el panel o selecciona «Datos de ejemplo» en el menú lateral.')
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
        st.caption(f'Productos analizados · {len(catalogo):,}'.replace(',', ' '))

        limites = (ventas['fecha'].min().date(), ventas['fecha'].max().date())
        periodo = st.date_input('Periodo de ventas', value=limites, min_value=limites[0], max_value=limites[1],
                                format='DD/MM/YYYY', key='periodo')
        cortes = sorted(inventario['fecha_corte'].dt.date.unique(), reverse=True)
        corte = st.selectbox('Corte de inventario', cortes, format_func=lambda fecha: fecha.strftime('%d/%m/%Y'), key='corte')
        st.caption('El periodo filtra las ventas. El stock corresponde únicamente al corte seleccionado.')
        with st.expander('Ventana de análisis'):
            ventana = st.selectbox('Ventana del modelo (días)', [14, 28, 42, 56], index=1, key='ventana_modelo')
            st.caption('El cálculo de demanda usa el histórico hasta el corte de inventario.')

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
    columnas = st.columns(3)
    for columna, etiqueta, clave, ayuda in zip(
        columnas, ['Unidades vendidas', 'Productos sin stock', 'Stock bajo, aún disponible'],
        ['unidades', 'sin_stock', 'bajo_minimo'],
        ['Suma de las unidades vendidas en el periodo seleccionado.',
         'Productos con stock igual a cero en el corte de inventario.',
         'Productos con stock mayor a cero y menor que el mínimo en el corte de inventario.'],
    ):
        columna.metric(etiqueta, f'{valores[clave]:,}'.replace(',', ' '), border=True, help=ayuda)

    if valores['sin_inventario']:
        st.warning(f'{valores["sin_inventario"]} producto(s) sin inventario en este corte. Se muestran como «Sin datos» y se excluyen de las alertas de stock.')
    sin_ventas = int(resumen['unidades_vendidas'].isna().sum())
    if sin_ventas:
        st.caption(f'{sin_ventas} producto(s) sin registros de ventas en el periodo; no se interpretan automáticamente como cero ventas.')

    general, detalle, reposicion, escenarios, avanzado, alcance = st.tabs([
        'Vista general', 'Inventario', 'Reposición', 'Escenarios What-If', 'Pronóstico y modelos', 'Datos y alcance'])
    ventas_filtradas = ventas[ventas['producto_id'].isin(catalogo['producto_id']) &
                              ventas['fecha'].between(pd.Timestamp(inicio), pd.Timestamp(fin))]
    with general:
        izquierda, derecha = st.columns([1.65, 1])
        with izquierda, st.container(border=True):
            st.subheader('Evolución de ventas')
            frecuencia = st.radio('Ver evolución', ['Por mes', 'Por día'], horizontal=True, key='frecuencia_ventas')
            diarias = ventas_filtradas.groupby('fecha', as_index=False)['unidades_vendidas'].sum()
            if diarias.empty:
                st.info('No hay registros de ventas para esta selección.')
            else:
                mensual = frecuencia == 'Por mes'
                if mensual:
                    serie = diarias.groupby(pd.Grouper(key='fecha', freq='MS'))['unidades_vendidas'].mean().dropna().reset_index()
                    st.caption('Promedio diario por mes. Se cuentan los días con registros dentro del periodo seleccionado.')
                else:
                    serie = diarias
                    st.caption('Unidades registradas por día dentro del periodo seleccionado.')
                formato = '%m/%Y' if mensual else '%d/%m/%Y'
                unidad = 'Promedio diario' if mensual else 'Unidades'
                grafico(serie, {
                    'mark': {'type': 'area', 'line': {'color': VERDE, 'strokeWidth': 2.5},
                             'color': {'gradient': 'linear', 'x1': 0, 'y1': 0, 'x2': 0, 'y2': 1,
                                       'stops': [{'offset': 0, 'color': '#8fcaa4'}, {'offset': 1, 'color': '#f6faf5'}]}},
                    'encoding': {
                        'x': {'field': 'fecha', 'type': 'temporal', 'title': None, 'axis': {'format': formato, 'grid': False}},
                        'y': {'field': 'unidades_vendidas', 'type': 'quantitative', 'title': unidad},
                        'tooltip': [{'field': 'fecha', 'type': 'temporal', 'title': 'Mes' if mensual else 'Fecha', 'format': formato},
                                    {'field': 'unidades_vendidas', 'type': 'quantitative', 'title': unidad, 'format': '.1f' if mensual else ',d'}],
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

    with detalle:
        st.subheader('Inventario por producto')
        st.caption('Los productos sin stock y los que tienen stock bajo aparecen primero.')
        tabla_productos(resumen, 'tabla_inventario')
        st.download_button('Descargar detalle CSV',
                           resumen.rename(columns=NOMBRES).to_csv(index=False, sep=';').encode('utf-8-sig'),
                           file_name=f'inventario_{corte:%Y%m%d}.csv', mime='text/csv')
        st.caption('Los campos vacíos indican que falta el dato correspondiente.')

    demanda = estimar_demanda(catalogo, ventas, corte, ventana)
    with reposicion:
        base, parametros = panel_reposicion(demanda, inventario, corte, ventana)
    with escenarios:
        panel_escenarios(demanda, inventario, corte, ventana, parametros, base)
    with avanzado:
        analisis = st.selectbox('Elegir análisis', list(CONTROLES_ANALISIS), key='analisis_avanzado')
        # Streamlit limpia los valores de los widgets que no dibuja en este ciclo.
        for opcion, claves in CONTROLES_ANALISIS.items():
            if opcion != analisis:
                for clave in claves:
                    if clave in st.session_state:
                        st.session_state[clave] = st.session_state[clave]
        ejemplo = fuente == 'Datos de ejemplo'
        historial = DATOS_EJEMPLO / 'historial_stock.csv'
        if not ejemplo:
            with st.expander('Historial para alertas'):
                historial = st.file_uploader('Historial diario de stock (CSV)', type='csv', key='historial_stock')
        if analisis == 'Alertas de quiebre':
            panel_quiebres(productos, catalogo, ventas, inventario, corte, ejemplo, historial, grafico)
        elif analisis == 'Evaluación de demanda':
            panel_evaluacion(catalogo, ventas, corte, ventana, grafico)
        elif analisis == 'Segmentación':
            panel_segmentacion(demanda, grafico)

    with alcance:
        st.subheader('Origen de los datos')
        if fuente == 'Datos de ejemplo':
            st.markdown('**Catálogo y procedencia**')
            total_ventas = f'{len(ventas):,}'.replace(',', ' ')
            st.write(f'{len(productos)} productos de {productos["categoria"].nunique()} categorías y '
                     f'{total_ventas} registros de ventas del {limites[0]:%d/%m/%Y} al {limites[1]:%d/%m/%Y}. '
                     f'Hay {len(cortes)} cortes de inventario.')
            st.caption('Las fichas provienen de Tottus Perú. El historial de ventas, los mínimos y el stock al cierre '
                       'se simulan para una sola sede. La fecha de consulta corresponde al catálogo, no al historial.')
            referencia = pd.read_csv(DATOS_EJEMPLO / 'catalogo_referencia.csv', sep=';', dtype={'producto_id': str})
            referencia = referencia[referencia['producto_id'].isin(catalogo['producto_id'])]
            with st.expander('Ver fichas de los productos seleccionados'):
                st.dataframe(referencia[['producto_id', 'nombre', 'categoria', 'familia', 'marca', 'fuente_url',
                                          'fecha_consulta']].rename(columns={**NOMBRES, 'familia': 'Familia',
                                                                             'marca': 'Marca', 'fecha_consulta': 'Consulta'}),
                             column_config={'fuente_url': st.column_config.LinkColumn('Fuente', display_text='Ver en Tottus')},
                             hide_index=True, width='stretch')
                st.download_button('Descargar catálogo de referencia', referencia.to_csv(index=False, sep=';').encode('utf-8-sig'),
                                   file_name='catalogo_referencia.csv', mime='text/csv')
        st.caption('Los días ausentes en un archivo cargado no se completan con ceros. La cifra de ventas suma únicamente registros disponibles; no mide demanda no atendida ni probabilidad de quiebre.')
        with st.expander('Ver columnas requeridas y descargar CSV de ejemplo'):
            for tipo, tabla in tablas.items():
                st.markdown(f'**{tipo}.csv**')
                st.code(';'.join(tabla.columns), language=None)
                st.download_button(f'Descargar ejemplo de {tipo}',
                                   (DATOS_EJEMPLO / f'{tipo}.csv').read_bytes(),
                                   file_name=f'{tipo}.csv', mime='text/csv', key=f'ejemplo_{tipo}')
            st.caption('Fechas AAAA-MM-DD; cantidades enteras no negativas; códigos como texto. Cada combinación de producto y fecha debe ser única. No se corrigen datos inválidos silenciosamente.')

    st.divider()
    st.caption('Inventario y reposición · Soporte de decisiones')


if __name__ == '__main__':
    main()
