"""Paneles de demanda, reposición y perfiles de productos."""

import pandas as pd
import streamlit as st

from src.demanda import evaluar_demanda
from src.reposicion import calcular_reposicion
from src.segmentacion import segmentar_productos


@st.cache_data(max_entries=32, show_spinner=False)
def _evaluacion(productos, ventas, corte, ventana):
    return evaluar_demanda(productos, ventas, corte, ventana, dias_prueba=14)


@st.cache_data(max_entries=32, show_spinner=False)
def _segmentos(demanda, grupos):
    return segmentar_productos(demanda, grupos)


def numero(valor):
    return '—' if pd.isna(valor) else f'{valor:,.0f}'.replace(',', ' ')


def panel_reposicion(demanda, inventario, corte, ventana):
    st.subheader('De los datos a una propuesta de reposición')
    st.caption(f'Histórico: últimos {ventana} días hasta el {corte:%d/%m/%Y}. '
               'Los parámetros son supuestos del ejercicio, comunes a los productos filtrados.')
    with st.container(border=True):
        st.markdown('**Política base**')
        a, b, c = st.columns(3)
        plazo = a.number_input('Plazo de entrega (días)', 0, 60, 3, key='plazo')
        revision = b.number_input('Revisar cada (días)', 1, 60, 7, key='revision')
        seguridad = c.number_input('Seguridad (días de venta)', 0, 30, 2, key='seguridad')
        st.caption('El stock mínimo del CSV sigue siendo una alerta descriptiva. El stock de seguridad se calcula a partir de los días definidos aquí.')
    with st.container(border=True):
        st.markdown('**What-If · modificar el escenario**')
        a, b, c = st.columns(3)
        variacion = a.slider('Variación de demanda (%)', -100, 100, 0, 10, key='variacion_demanda')
        retraso = b.slider('Retraso adicional (días)', 0, 14, 0, key='retraso')
        cambio_stock = c.slider('Variación del stock (%)', -100, 100, 0, 10, key='cambio_stock')
        st.caption('Los cambios se aplican solo al escenario. El stock simulado se redondea hacia abajo a unidades completas; los CSV permanecen iguales.')

    parametros = dict(plazo=plazo, revision=revision, seguridad=seguridad)
    base = calcular_reposicion(demanda, inventario, corte, **parametros)
    escenario = calcular_reposicion(demanda, inventario, corte, **parametros,
                                    variacion=variacion, retraso=retraso, cambio_stock=cambio_stock)
    total_base = base['cantidad_sugerida'].sum(min_count=1)
    total_escenario = escenario['cantidad_sugerida'].sum(min_count=1)
    a, b, c, d = st.columns(4)
    a.metric('Unidades sugeridas · base', numero(total_base), border=True)
    b.metric('Unidades sugeridas · escenario', numero(total_escenario),
             delta=None if pd.isna(total_escenario) else numero(total_escenario - total_base),
             delta_color='off', border=True)
    c.metric('Prioridad alta · escenario', numero(escenario['prioridad'].eq('Alta').sum()), border=True,
             help='Stock que no supera las ventas estimadas durante el plazo de entrega. Es una regla, no una probabilidad.')
    d.metric('Productos evaluables', numero(base['cantidad_sugerida'].notna().sum()), border=True)
    excluidos = base[base['prioridad'].eq('No evaluable')]
    if not excluidos.empty:
        st.warning(f'{len(excluidos)} producto(s) no evaluables por histórico incompleto o falta de inventario. Las cantidades desconocidas quedan vacías.')
        with st.expander('Revisar productos no evaluables'):
            st.dataframe(excluidos[['producto_id', 'nombre', 'explicacion']].rename(columns={
                'producto_id': 'Código', 'nombre': 'Producto', 'explicacion': 'Motivo'}), hide_index=True, width='stretch')

    comparacion = base[['producto_id', 'nombre', 'categoria', 'demanda_diaria', 'stock_evaluado',
                       'punto_reorden', 'cantidad_sugerida', 'prioridad']].rename(columns={
        'stock_evaluado': 'stock_base', 'punto_reorden': 'reorden_base',
        'cantidad_sugerida': 'pedido_base', 'prioridad': 'prioridad_base'})
    comparacion = comparacion.merge(escenario[['producto_id', 'demanda_escenario', 'stock_evaluado',
                                               'punto_reorden', 'cantidad_sugerida', 'prioridad',
                                               'stock_seguridad', 'stock_objetivo', 'cobertura_dias', 'explicacion']],
                                    on='producto_id', validate='one_to_one')
    comparacion['cambio_unidades'] = comparacion['cantidad_sugerida'] - comparacion['pedido_base']
    orden = {'Alta': 0, 'Media': 1, 'Baja': 2, 'Sin demanda reciente': 3, 'Demanda simulada nula': 4, 'No evaluable': 5}
    comparacion = comparacion.sort_values('prioridad', key=lambda serie: serie.map(orden))
    etiquetas = {'producto_id': 'Código', 'nombre': 'Producto', 'demanda_diaria': 'Venta diaria base',
                 'stock_base': 'Stock base', 'pedido_base': 'Sugerencia base', 'stock_evaluado': 'Stock escenario',
                 'cantidad_sugerida': 'Sugerencia escenario', 'punto_reorden': 'Reorden escenario',
                 'prioridad': 'Prioridad escenario', 'cambio_unidades': 'Cambio (unidades)'}
    visibles = list(etiquetas)
    st.dataframe(comparacion[visibles].rename(columns=etiquetas).round(2), hide_index=True, width='stretch')
    st.caption('Una sugerencia de 0 indica que la política no activa un pedido bajo esos supuestos. «Sin demanda reciente» no garantiza ausencia de demanda futura.')

    nombres = comparacion.set_index('producto_id')['nombre'].to_dict()
    codigo = st.selectbox('Explicar un producto', comparacion['producto_id'].tolist(),
                          format_func=lambda valor: nombres[valor], key='producto_explicacion')
    fila = comparacion.set_index('producto_id').loc[codigo]
    st.write(fila['explicacion'])
    if pd.notna(fila['demanda_escenario']):
        st.caption(f'Venta diaria estimada: {fila["demanda_escenario"]:.2f} unidades · '
                   f'Seguridad: {numero(fila["stock_seguridad"])} unidades · '
                   f'Stock objetivo: {numero(fila["stock_objetivo"])} unidades · '
                   f'Cobertura: {"sin consumo estimado" if fila["demanda_escenario"] == 0 else numero(fila["cobertura_dias"]) + " días (aprox.)"}')
    exportacion = comparacion.assign(fecha_corte=str(corte), ventana_dias=ventana, plazo_base=plazo,
                                     revision_dias=revision, seguridad_dias=seguridad,
                                     variacion_demanda_pct=variacion, retraso_dias=retraso, cambio_stock_pct=cambio_stock)
    st.download_button('Descargar comparación de escenarios', exportacion.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name=f'escenarios_{corte:%Y%m%d}.csv', mime='text/csv')
    with st.expander('Cómo se obtiene la propuesta'):
        st.markdown('''
1. **Venta diaria base:** promedio de los últimos días completos de la ventana.
2. **Seguridad:** venta diaria × días de seguridad, redondeada hacia arriba.
3. **Punto de reorden:** venta diaria × plazo de entrega + seguridad, redondeado hacia arriba.
4. **Objetivo:** venta diaria × (plazo + periodo de revisión) + seguridad, redondeado hacia arriba.
5. **Cantidad sugerida:** objetivo − stock, solo cuando el stock está en o bajo el punto de reorden; nunca negativa.

Prioridad **alta**: el stock no supera las ventas estimadas durante el plazo. **Media**: alcanza el punto de reorden con colchón de seguridad. **Baja**: stock superior al punto de reorden.

Suponemos pedidos en tránsito y reservas iguales a cero. No se consideran lotes mínimos, presupuesto, vencimientos ni capacidad. La propuesta requiere revisión del responsable y no ejecuta compras.
''')


def panel_evaluacion(productos, ventas, corte, ventana, grafico):
    st.subheader('¿Qué tan cerca está la estimación de las ventas observadas?')
    st.caption('Evaluación exploratoria de un día adelante en los últimos 14 días hasta el corte. '
               'Cada día se utiliza solo información anterior; luego se incorpora la observación conocida para el siguiente origen.')
    metricas, detalle, excluidos = _evaluacion(productos, ventas, corte, ventana)
    if not excluidos.empty:
        st.info(f'{len(excluidos)} producto(s) excluidos: se necesitan {ventana + 14} días diarios completos hasta el corte para comparar ambos métodos.')
    if metricas.empty:
        st.info('No hay histórico suficiente para evaluar. Amplía la fuente o selecciona otra ventana/corte.')
        return
    etiquetas = {'metodo': 'Método', 'mae': 'MAE (unidades/día)', 'rmse': 'RMSE (unidades/día)',
                 'wape_pct': 'WAPE (%)', 'observaciones': 'Producto-días evaluados', 'productos': 'Productos'}
    st.dataframe(metricas.rename(columns=etiquetas).round(3), hide_index=True, width='stretch')
    st.caption('Menor MAE/RMSE indica menor error en esta evaluación. WAPE queda vacío si la suma real es cero. '
               'El ingenuo semanal repite las ventas del mismo día de la semana anterior. Las métricas agrupan producto-días, no porcentajes de acierto.')
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
        'x': {'field': 'fecha', 'type': 'temporal', 'title': None, 'axis': {'format': '%d/%m'}},
        'y': {'field': 'unidades', 'type': 'quantitative', 'title': 'Unidades por día', 'scale': {'zero': True}},
        'color': {'field': 'serie', 'type': 'nominal', 'legend': {'title': None, 'orient': 'top'},
                  'scale': {'domain': ['Venta observada', 'Media móvil', 'Ingenuo semanal'],
                            'range': ['#19342a', '#16834b', '#d69b35']}},
        'tooltip': [{'field': 'fecha', 'type': 'temporal', 'format': '%d/%m/%Y'},
                    {'field': 'serie'}, {'field': 'unidades', 'format': '.2f'}],
    }})
    st.download_button('Descargar evaluación diaria', detalle.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name=f'evaluacion_{corte:%Y%m%d}.csv', mime='text/csv')
    with st.expander('Método y límites de la evaluación'):
        st.write(f'La media móvil usa {ventana} observaciones diarias previas a cada objetivo. '
                 'La ventana se fija desde el menú: esta comparación es exploratoria y no constituye una prueba final independiente. '
                 'Los dos métodos se comparan sobre exactamente los mismos productos y días, sin mezclar fechas aleatoriamente. '
                 'El error a un día no valida automáticamente el horizonte de reposición de varios días. '
                 'Las ventas pueden subestimar la demanda cuando no había stock; no se dispone de demanda perdida.')


def panel_segmentacion(demanda, grafico):
    st.subheader('Perfiles de venta de los productos')
    st.caption('K-means agrupa por venta diaria media y variabilidad relativa (desviación / media), '
               'estandarizadas con StandardScaler. Los grupos describen la selección actual; no predicen quiebres.')
    grupos = st.selectbox('Número de grupos', [2, 3, 4], index=1, key='grupos_kmeans')
    try:
        asignados, perfiles, silueta = _segmentos(demanda, grupos)
    except ValueError as error:
        st.info(str(error))
        return
    if len(asignados) < len(demanda):
        st.info(f'{len(demanda) - len(asignados)} producto(s) excluidos por histórico incompleto.')
    a, b = st.columns(2)
    a.metric('Productos segmentados', len(asignados), border=True)
    b.metric('Silueta de la agrupación', 'No definida' if silueta is None else f'{silueta:.3f}', border=True,
             help='Entre -1 y 1. Valores mayores sugieren mayor separación en estas variables; no es accuracy ni probabilidad.')
    grafico(asignados, {'mark': {'type': 'circle', 'size': 150, 'opacity': .85}, 'encoding': {
        'x': {'field': 'demanda_diaria', 'type': 'quantitative', 'title': 'Venta diaria media (unidades)'},
        'y': {'field': 'cv', 'type': 'quantitative', 'title': 'Variabilidad relativa (CV)'},
        'color': {'field': 'segmento', 'type': 'nominal', 'legend': {'title': None, 'orient': 'bottom'}},
        'tooltip': [{'field': 'nombre', 'title': 'Producto'}, {'field': 'segmento', 'title': 'Grupo'},
                    {'field': 'demanda_diaria', 'format': '.2f'}, {'field': 'cv', 'format': '.3f'}],
    }})
    st.dataframe(perfiles.rename(columns={'segmento': 'Perfil', 'productos': 'Productos',
                                          'demanda_media': 'Venta diaria media', 'cv_medio': 'Variabilidad media'}).round(3),
                 hide_index=True, width='stretch')
    st.caption('Los nombres se ordenan por promedio de venta del grupo. «Mayor» y «menor» son relativos a la selección. '
               'La variabilidad también participa del agrupamiento. Conviene revisar con más frecuencia los productos de mayor venta y contrastar los de alta variabilidad con el contexto comercial.')
    with st.expander('Ver productos por grupo'):
        st.dataframe(asignados[['producto_id', 'nombre', 'demanda_diaria', 'cv', 'segmento']].rename(columns={
            'producto_id': 'Código', 'nombre': 'Producto', 'demanda_diaria': 'Venta diaria media',
            'cv': 'Variabilidad (CV)', 'segmento': 'Grupo'}).round(3), hide_index=True, width='stretch')
    st.download_button('Descargar segmentos', asignados.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name='segmentos_productos.csv', mime='text/csv')
