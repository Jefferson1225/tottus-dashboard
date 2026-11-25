"""Paneles de demanda, reposición y perfiles de productos."""

import pandas as pd
import streamlit as st

from src.demanda import evaluar_demanda
from src.reposicion import calcular_reposicion
from src.segmentacion import METODOS, diagnostico_kmeans, ramas_ward, segmentar_productos


ORDEN_PRIORIDAD = {'Alta': 0, 'Media': 1, 'Baja': 2, 'Sin demanda reciente': 3,
                   'Demanda simulada nula': 4, 'No evaluable': 5}


@st.cache_data(max_entries=32, show_spinner=False)
def _evaluacion(productos, ventas, corte, ventana, horizonte):
    return evaluar_demanda(productos, ventas, corte, ventana, dias_prueba=14, horizonte=horizonte)


@st.cache_data(max_entries=32, show_spinner=False)
def _segmentos(demanda, grupos, metodo):
    return segmentar_productos(demanda, grupos, metodo)


@st.cache_data(max_entries=16, show_spinner=False)
def _diagnostico(demanda):
    return diagnostico_kmeans(demanda)


def numero(valor):
    return '—' if pd.isna(valor) else f'{valor:,.0f}'.replace(',', ' ')


def panel_reposicion(demanda, inventario, corte, ventana):
    st.subheader('Propuesta de reposición')
    with st.expander('Ajustar política de reposición'):
        a, b, c = st.columns(3)
        plazo = a.number_input('Plazo de entrega (días)', 0, 60, 3, key='plazo')
        revision = b.number_input('Revisar cada (días)', 1, 60, 7, key='revision')
        seguridad = c.number_input('Seguridad (días de venta)', 0, 30, 2, key='seguridad')
    st.caption(f'Demanda estimada con {ventana} días hasta el {corte:%d/%m/%Y} · '
               f'Entrega en {plazo} días · Revisión cada {revision} días · Seguridad de {seguridad} días')

    parametros = dict(plazo=plazo, revision=revision, seguridad=seguridad)
    base = calcular_reposicion(demanda, inventario, corte, **parametros).sort_values(
        ['prioridad', 'cantidad_sugerida', 'nombre'], ascending=[True, False, True],
        key=lambda columna: columna.map(ORDEN_PRIORIDAD) if columna.name == 'prioridad' else columna)
    total_base = base['cantidad_sugerida'].sum(min_count=1)
    st.metric('Unidades sugeridas · base', numero(total_base), border=True)
    columnas = {'nombre': 'Producto', 'stock_actual': 'Stock actual', 'prioridad': 'Prioridad',
                'cantidad_sugerida': 'Cantidad sugerida'}
    st.dataframe(base[list(columnas)].rename(columns=columnas), hide_index=True, width='stretch',
                 column_config={'Cantidad sugerida': st.column_config.NumberColumn(format='%d')})
    excluidos = base['prioridad'].eq('No evaluable').sum()
    if excluidos:
        st.warning(f'{excluidos} producto(s) tienen histórico incompleto o falta de inventario.')
    st.download_button('Descargar propuesta CSV',
                       base[['producto_id', *columnas]].assign(fecha_corte=str(corte), ventana_dias=ventana, **parametros)
                       .to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name=f'reposicion_{corte:%Y%m%d}.csv', mime='text/csv')

    with st.expander('Detalle del cálculo'):
        nombres = base.set_index('producto_id')['nombre']
        codigo = st.selectbox('Explicar un producto', nombres.index.tolist(),
                              format_func=nombres.__getitem__, key='producto_explicacion')
        fila = base.set_index('producto_id').loc[codigo]
        st.write(fila['explicacion'])
        venta = fila['demanda_diaria']
        cobertura = fila['cobertura_dias']
        venta_texto = f'{venta:.2f} unidades/día' if pd.notna(venta) else '—'
        cobertura_texto = f'{cobertura:.2f} días' if pd.notna(cobertura) else '—'
        st.caption(f'Venta diaria estimada: {venta_texto} · Cobertura: {cobertura_texto}')
        st.caption(f'Punto de reorden: {numero(fila["punto_reorden"])} · '
                   f'Stock de seguridad: {numero(fila["stock_seguridad"])} · '
                   f'Stock objetivo: {numero(fila["stock_objetivo"])}')
        st.markdown('''
La prioridad es **alta** si el stock es igual o menor que la venta estimada durante el plazo de entrega.
Es **media** si el stock supera esa venta pero alcanza el punto de reorden, y **baja** si supera el punto de reorden.

El punto de reorden suma las ventas esperadas durante la entrega y el stock de seguridad. Si el producto alcanza
ese umbral, sugerimos las unidades que faltan para cubrir la entrega, el periodo entre revisiones y la seguridad.
La propuesta supone cero pedidos en tránsito y cero reservas.
''')

    if st.checkbox('Simular escenario (What-If)', key='mostrar_escenario'):
        _panel_escenario(demanda, inventario, corte, ventana, parametros, base, total_base)
    else:
        # Mantiene los ajustes cuando los controles dejan de dibujarse.
        for clave in ('variacion_demanda', 'retraso', 'cambio_stock'):
            if clave in st.session_state:
                st.session_state[clave] = st.session_state[clave]


def _panel_escenario(demanda, inventario, corte, ventana, parametros, base, total_base):
    with st.container(border=True):
        a, b, c = st.columns(3)
        variacion = a.slider('Variación de demanda (%)', -100, 100, 0, 10, key='variacion_demanda')
        retraso = b.slider('Retraso adicional (días)', 0, 14, 0, key='retraso')
        cambio_stock = c.slider('Variación del stock (%)', -100, 100, 0, 10, key='cambio_stock')
        st.caption('Se compara el escenario con la política base para el mismo corte.')

    escenario = calcular_reposicion(demanda, inventario, corte, **parametros,
                                    variacion=variacion, retraso=retraso, cambio_stock=cambio_stock)
    total_escenario = escenario['cantidad_sugerida'].sum(min_count=1)
    st.metric('Unidades sugeridas · escenario', numero(total_escenario),
             delta=None if pd.isna(total_escenario) else numero(total_escenario - total_base),
             delta_color='off', border=True)

    comparacion = base[['producto_id', 'nombre', 'categoria', 'demanda_diaria', 'stock_evaluado',
                       'punto_reorden', 'cantidad_sugerida', 'prioridad']].rename(columns={
        'stock_evaluado': 'stock_base', 'punto_reorden': 'reorden_base',
        'cantidad_sugerida': 'pedido_base', 'prioridad': 'prioridad_base'})
    comparacion = comparacion.merge(escenario[['producto_id', 'demanda_escenario', 'stock_evaluado',
                                               'punto_reorden', 'cantidad_sugerida', 'prioridad',
                                               'stock_seguridad', 'stock_objetivo', 'cobertura_dias', 'explicacion']],
                                    on='producto_id', validate='one_to_one')
    comparacion['cambio_unidades'] = comparacion['cantidad_sugerida'] - comparacion['pedido_base']
    comparacion = comparacion.sort_values('prioridad', key=lambda serie: serie.map(ORDEN_PRIORIDAD))
    etiquetas = {'nombre': 'Producto', 'prioridad_base': 'Prioridad base', 'prioridad': 'Prioridad escenario',
                 'pedido_base': 'Unidades base', 'cantidad_sugerida': 'Unidades escenario', 'cambio_unidades': 'Cambio'}
    st.dataframe(comparacion[list(etiquetas)].rename(columns=etiquetas), hide_index=True, width='stretch')
    exportacion = comparacion.assign(fecha_corte=str(corte), ventana_dias=ventana, plazo_base=parametros['plazo'],
                                     revision_dias=parametros['revision'], seguridad_dias=parametros['seguridad'],
                                     variacion_demanda_pct=variacion, retraso_dias=retraso, cambio_stock_pct=cambio_stock)
    st.download_button('Descargar comparación de escenarios', exportacion.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name=f'escenarios_{corte:%Y%m%d}.csv', mime='text/csv')


def panel_evaluacion(productos, ventas, corte, ventana, grafico):
    st.subheader('¿Qué tan cerca está la estimación de las ventas observadas?')
    horizonte = st.select_slider('Horizonte de demanda (días)', options=[1, 3, 7, 14],
                                 value=1, key='horizonte_demanda')
    st.caption(f'Comparamos las ventas acumuladas a {horizonte} día(s) desde 14 fechas de inicio por producto. '
               'Cada estimación usa solo las ventas anteriores a su fecha de inicio.')
    metricas, detalle, excluidos = _evaluacion(productos, ventas, corte, ventana, horizonte)
    if not excluidos.empty:
        st.info(f'{len(excluidos)} producto(s) excluidos: se necesitan {ventana + 13 + horizonte} días completos hasta el corte.')
    if metricas.empty:
        st.info('No hay histórico suficiente para evaluar. Amplía la fuente o selecciona otra ventana/corte.')
        return
    etiquetas = {'metodo': 'Método', 'mae': 'MAE (unidades)', 'rmse': 'RMSE (unidades)',
                 'wape_pct': 'WAPE (%)', 'observaciones': 'Pronósticos evaluados', 'productos': 'Productos'}
    st.dataframe(metricas.rename(columns=etiquetas).round(3), hide_index=True, width='stretch')
    st.caption('Menor MAE/RMSE indica menor error en esta evaluación. WAPE queda vacío si la suma real es cero. '
               'El ingenuo semanal repite los siete días anteriores para cubrir el horizonte.')
    medias = metricas.set_index('metodo')['mae']
    if medias['Media móvil'] > medias['Ingenuo semanal']:
        st.info('En este histórico, la referencia semanal obtiene menor MAE que la media móvil. Conviene revisar la estacionalidad antes de adoptar la media como política operativa.')
    nombres = productos.set_index('producto_id')['nombre'].to_dict()
    codigo = st.selectbox('Producto para revisar la evaluación', detalle['producto_id'].unique().tolist(),
                          format_func=lambda valor: nombres[valor], key='producto_evaluacion')
    puntos = detalle[detalle['producto_id'].eq(codigo)]
    reales = puntos[['fecha', 'real']].drop_duplicates('fecha').rename(columns={'real': 'unidades'})
    reales['serie'] = 'Venta observada'
    predicciones = puntos.rename(columns={'estimado': 'unidades', 'metodo': 'serie'})[['fecha', 'unidades', 'serie']]
    curvas = pd.concat([reales, predicciones], ignore_index=True)
    grafico(curvas, {'mark': {'type': 'line', 'point': True}, 'encoding': {
        'x': {'field': 'fecha', 'type': 'temporal', 'title': 'Inicio del horizonte', 'axis': {'format': '%d/%m'}},
        'y': {'field': 'unidades', 'type': 'quantitative', 'title': f'Unidades acumuladas en {horizonte} día(s)', 'scale': {'zero': True}},
        'color': {'field': 'serie', 'type': 'nominal', 'legend': {'title': None, 'orient': 'top'},
                  'scale': {'domain': ['Venta observada', 'Media móvil', 'Ingenuo semanal'],
                            'range': ['#19342a', '#16834b', '#d69b35']}},
        'tooltip': [{'field': 'fecha', 'type': 'temporal', 'format': '%d/%m/%Y'},
                    {'field': 'serie'}, {'field': 'unidades', 'format': '.2f'}],
    }})
    exportar = detalle.assign(horizonte_dias=horizonte, ventana_dias=ventana)
    st.download_button('Descargar evaluación de demanda', exportar.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name=f'evaluacion_{corte:%Y%m%d}_{horizonte}d.csv', mime='text/csv')
    with st.expander('Método y límites de la evaluación'):
        st.write(f'La media móvil usa {ventana} observaciones diarias previas a cada objetivo. '
                 'La ventana se fija desde el menú. La comparación utiliza el histórico seleccionado y no incluye una validación externa. '
                 'Los dos métodos se comparan sobre exactamente los mismos productos y días, sin mezclar fechas aleatoriamente. '
                 'Para más de un día, los horizontes consecutivos pueden compartir días observados; cada fila mide su propio pronóstico acumulado. '
                 'Las ventas pueden subestimar la demanda cuando no había stock; no se dispone de demanda perdida.')


def panel_segmentacion(demanda, grafico):
    st.subheader('Perfiles de venta de los productos')
    st.caption('Los grupos usan venta diaria media y variabilidad relativa, estandarizadas con StandardScaler.')
    a, b = st.columns(2)
    metodo = a.selectbox('Método de segmentación', METODOS, key='metodo_segmentacion')
    grupos = b.selectbox('Número de grupos', [2, 3, 4, 5, 6], index=1, key='grupos_kmeans')
    try:
        asignados, perfiles, silueta = _segmentos(demanda, grupos, metodo)
    except ValueError as error:
        st.info(str(error))
        return
    if len(asignados) < len(demanda):
        st.info(f'{len(demanda) - len(asignados)} producto(s) excluidos por histórico incompleto.')
    a, b = st.columns(2)
    a.metric('Productos segmentados', len(asignados), border=True)
    b.metric('Silueta de la agrupación', 'No definida' if silueta is None else f'{silueta:.3f}', border=True,
             help='Entre -1 y 1. Valores mayores sugieren mayor separación en estas variables; no es accuracy ni probabilidad.')
    grafico(asignados, {'mark': {'type': 'point', 'filled': True, 'size': 150, 'opacity': .85}, 'encoding': {
        'x': {'field': 'demanda_diaria', 'type': 'quantitative', 'title': 'Venta diaria media (unidades)'},
        'y': {'field': 'cv', 'type': 'quantitative', 'title': 'Variabilidad relativa (CV)'},
        'color': {'field': 'segmento', 'type': 'nominal', 'legend': {'title': None, 'orient': 'bottom'}},
        'shape': {'field': 'representante', 'type': 'nominal', 'legend': None},
        'tooltip': [{'field': 'nombre', 'title': 'Producto'}, {'field': 'segmento', 'title': 'Grupo'},
                    {'field': 'representante', 'title': 'Representante'},
                    {'field': 'demanda_diaria', 'format': '.2f'}, {'field': 'cv', 'format': '.3f'}],
    }})
    representantes = asignados.loc[asignados['representante'], ['segmento', 'nombre']]
    perfiles = perfiles.merge(representantes, on='segmento', validate='one_to_one')
    st.dataframe(perfiles.rename(columns={'segmento': 'Perfil', 'productos': 'Productos', 'nombre': 'Producto representativo',
                                          'demanda_media': 'Venta diaria media', 'cv_medio': 'Variabilidad media'}).round(3),
                 hide_index=True, width='stretch')
    st.caption('Los perfiles muestran promedios en unidades originales. Revisa con más frecuencia los grupos de mayor venta y considera más margen donde la venta sea variable.')
    if metodo == 'Jerárquico (Ward)':
        st.markdown('**Dendrograma de Ward**')
        grafico(ramas_ward(demanda), {'mark': 'line', 'encoding': {
            'x': {'field': 'x', 'type': 'quantitative', 'axis': None},
            'y': {'field': 'distancia', 'type': 'quantitative', 'title': 'Distancia de unión'},
            'detail': {'field': 'rama', 'type': 'nominal'}, 'order': {'field': 'orden', 'type': 'quantitative'},
        }})
        st.caption('Las ramas que se unen a menor altura representan perfiles más parecidos. Se muestran hasta 18 ramas terminales.')
    if metodo == 'K-means':
        with st.expander('Comparar número de grupos · codo y silueta'):
            diagnostico = _diagnostico(demanda)
            grafico(diagnostico, {'mark': {'type': 'line', 'point': True}, 'encoding': {
                'x': {'field': 'k', 'type': 'ordinal', 'title': 'Número de grupos'},
                'y': {'field': 'inercia', 'type': 'quantitative', 'title': 'Inercia'},
                'tooltip': [{'field': 'k'}, {'field': 'inercia', 'format': '.3f'}, {'field': 'silueta', 'format': '.3f'}],
            }})
            st.dataframe(diagnostico.round(3), hide_index=True, width='stretch')
            st.caption('Compara dónde se desacelera la caída de la inercia y qué separación obtiene cada configuración.')
    with st.expander('Ver productos por grupo'):
        st.dataframe(asignados[['producto_id', 'nombre', 'demanda_diaria', 'cv', 'segmento']].rename(columns={
            'producto_id': 'Código', 'nombre': 'Producto', 'demanda_diaria': 'Venta diaria media',
            'cv': 'Variabilidad (CV)', 'segmento': 'Grupo'}).round(3), hide_index=True, width='stretch')
    st.download_button('Descargar segmentos', asignados.assign(metodo=metodo, grupos=grupos).to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name='segmentos_productos.csv', mime='text/csv')
