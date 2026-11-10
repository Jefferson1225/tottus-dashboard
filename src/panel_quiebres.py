"""Comparación de clasificadores y priorización de alertas."""

import pandas as pd
import streamlit as st
from sklearn.metrics import precision_recall_curve, roc_curve

from src.datos import ErrorDatos, cargar_csv, validar_historial
from src.quiebres import evaluar_quiebres, medir_alertas

DIAS_MODELO = 84


@st.cache_data(max_entries=8, show_spinner=False)
def _evaluar(historial, corte):
    return evaluar_quiebres(historial, corte)


def panel_quiebres(productos, seleccion, ventas, inventario, corte, ejemplo, archivo_ejemplo, grafico):
    st.subheader('Alertas para el próximo cierre')
    st.caption('El objetivo es anticipar qué productos terminarán el día siguiente con stock cero.')
    st.caption(f'Los modelos usan hasta {DIAS_MODELO} días de historial hasta el corte seleccionado.')
    if ejemplo:
        origen = archivo_ejemplo
        st.caption('Fuente: historial simulado de ventas y stock al cierre, conciliado con el inventario general.')
    else:
        origen = st.file_uploader('Historial diario de stock (CSV)', type='csv', key='historial_stock')
        if origen is None:
            st.info('Carga un historial diario para calcular alertas con tus datos.')
            st.code('fecha;producto_id;unidades_vendidas;stock_cierre', language=None)
            st.download_button('Descargar formato de historial', b'fecha;producto_id;unidades_vendidas;stock_cierre\n',
                               file_name='historial_stock.csv', mime='text/csv')
            return
    try:
        historial = cargar_csv(origen, 'historial_stock')
        historial = historial[historial['fecha'].le(pd.Timestamp(corte))]
        validar_historial(historial, productos, ventas, inventario)
        inicio = pd.Timestamp(corte) - pd.Timedelta(days=DIAS_MODELO - 1)
        historial = historial[historial['fecha'].ge(inicio)]
        if len(historial) > 20000:
            raise ErrorDatos(f'Para comparar los tres modelos, usa hasta 20 000 registros dentro de los últimos {DIAS_MODELO} días del corte.')
        with st.spinner('Evaluando los modelos por fecha…'):
            evaluados, actuales, bloques = _evaluar(historial, corte)
    except (ErrorDatos, ValueError) as error:
        st.info(str(error))
        return

    a, b = st.columns(2)
    modelo = a.selectbox('Modelo de alertas', evaluados['modelo'].unique(), key='modelo_quiebres')
    umbral = b.slider('Umbral de alerta', 0.05, 0.95, .50, .05, key='umbral_quiebres',
                      help='Al bajarlo se detectan más casos, pero pueden aumentar las falsas alertas.')
    nombres = productos[['producto_id', 'nombre']]
    visibles = actuales.loc[actuales['modelo'].eq(modelo) & actuales['producto_id'].isin(seleccion['producto_id'])]
    if visibles.empty:
        st.info('No hay productos seleccionados con siete días consecutivos hasta el corte.')
    else:
        lista = visibles.merge(nombres, on='producto_id', validate='many_to_one').sort_values('puntaje', ascending=False)
        lista['alerta'] = lista['puntaje'].ge(umbral).map({True: 'Revisar abastecimiento', False: 'Seguimiento habitual'})
        objetivo = pd.Timestamp(corte) + pd.Timedelta(days=1)
        st.markdown(f'**Prioridad para el {objetivo:%d/%m/%Y} · {int(lista["puntaje"].ge(umbral).sum())} alertas**')
        st.dataframe(lista[['producto_id', 'nombre', 'stock_cierre', 'puntaje', 'alerta']].rename(columns={
            'producto_id': 'Código', 'nombre': 'Producto', 'stock_cierre': 'Stock al cierre',
            'puntaje': 'Puntaje', 'alerta': 'Acción sugerida'}).round(3), hide_index=True, width='stretch')
        exportar = lista.assign(fecha_objetivo=objetivo, umbral=umbral)
        st.download_button('Descargar alertas', exportar.to_csv(index=False, sep=';').encode('utf-8-sig'),
                           file_name=f'alertas_{objetivo:%Y%m%d}.csv', mime='text/csv')
        sin_historial = len(seleccion) - len(lista)
        if sin_historial:
            st.caption(f'{sin_historial} producto(s) de la selección quedaron sin puntaje por falta de historial al corte.')
    st.caption('El puntaje ordena la revisión. SVM transforma su margen a una escala de 0 a 1; los puntajes de los tres modelos no son probabilidades calibradas.')

    st.divider()
    st.subheader('Comparación histórica')
    actual = evaluados[evaluados['modelo'].eq(modelo)]
    prevalencia = actual['quiebre'].mean()
    st.caption(f'{len(actual):,} registros fuera de muestra en tres bloques cronológicos · '
               f'{prevalencia:.1%} con stock cero al día siguiente. La evaluación usa todo el catálogo disponible; '
               'los filtros de producto aplican a la lista de alertas del corte.')
    filas = []
    for nombre, grupo in evaluados.groupby('modelo', sort=False):
        filas.append({'Modelo': nombre, **medir_alertas(grupo['quiebre'], grupo['puntaje'], umbral)})
    metricas = pd.DataFrame(filas).set_index('Modelo')
    fila = metricas.loc[modelo]
    a, b, c = st.columns(3)
    a.metric('Precisión de las alertas', f'{fila["precision"]:.1%}', border=True)
    b.metric('Quiebres detectados', f'{fila["recall"]:.1%}', border=True)
    c.metric('Quiebres no detectados', int(fila['fn']), border=True)
    st.dataframe(metricas[['precision', 'recall', 'f1', 'roc_auc', 'ap']].rename(columns={
        'precision': 'Precisión', 'recall': 'Recall', 'f1': 'F1', 'roc_auc': 'ROC-AUC',
        'ap': 'Precisión media (AP)'}).reset_index().round(3), hide_index=True, width='stretch')
    st.caption('Precisión, recall y F1 cambian con el umbral. ROC-AUC y AP resumen el orden de los puntajes a distintos umbrales.')

    izquierda, derecha = st.columns([1.3, 1])
    with izquierda:
        curva = st.radio('Curva de evaluación', ['Precisión–recall', 'ROC'], horizontal=True, key='curva_quiebres')
        series = []
        for nombre, grupo in evaluados.groupby('modelo', sort=False):
            if curva == 'Precisión–recall':
                y, x, _ = precision_recall_curve(grupo['quiebre'], grupo['puntaje'])
            else:
                x, y, _ = roc_curve(grupo['quiebre'], grupo['puntaje'])
            series.append(pd.DataFrame({'x': x, 'y': y, 'orden': range(len(x)), 'modelo': nombre}))
        if curva == 'Precisión–recall':
            series.append(pd.DataFrame({'x': [0., 1.], 'y': [prevalencia] * 2,
                                        'orden': [0, 1], 'modelo': 'Frecuencia de quiebres'}))
        grafico(pd.concat(series, ignore_index=True), {'mark': 'line', 'encoding': {
            'x': {'field': 'x', 'type': 'quantitative', 'title': 'Recall' if curva == 'Precisión–recall' else 'Tasa de falsas alertas'},
            'y': {'field': 'y', 'type': 'quantitative', 'title': 'Precisión' if curva == 'Precisión–recall' else 'Tasa de detección'},
            'color': {'field': 'modelo', 'type': 'nominal', 'legend': {'orient': 'bottom', 'title': None}},
            'order': {'field': 'orden', 'type': 'quantitative'},
        }})
    with derecha:
        st.markdown(f'**Matriz de confusión · {modelo}**')
        st.dataframe(pd.DataFrame({
            'Observado': ['Con stock', 'Sin stock'], 'Sin alerta': [int(fila['tn']), int(fila['fn'])],
            'Con alerta': [int(fila['fp']), int(fila['tp'])],
        }), hide_index=True, width='stretch')
        st.caption('Los quiebres sin alerta son los casos que conviene revisar al elegir un umbral.')
        with st.expander('Ver fechas y tamaño de los bloques'):
            st.dataframe(bloques, hide_index=True, width='stretch')
        with st.expander('Ver quiebres sin alerta'):
            omitidos = actual[actual['quiebre'].eq(1) & actual['puntaje'].lt(umbral)]
            if omitidos.empty:
                st.caption('No hubo quiebres sin alerta con este umbral.')
            else:
                st.dataframe(omitidos[['producto_id', 'fecha', 'puntaje']].merge(nombres, on='producto_id')
                             .assign(fecha_quiebre=lambda d: d['fecha'] + pd.Timedelta(days=1))
                             [['nombre', 'fecha_quiebre', 'puntaje']].round({'puntaje': 3}), hide_index=True, width='stretch')
    with st.expander('Cómo se calculan las alertas'):
        st.write('Usamos stock al cierre, venta del día, media de ventas a siete días, días sin stock y día de semana. '
                 'El cierre siguiente aporta la etiqueta. Los bloques separan por fecha y dejan un día de margen para '
                 'evitar usar etiquetas futuras. Los modelos ponderan las clases y SVM escala las variables dentro de cada ajuste. '
                 'El umbral permite comparar el costo de alertar de más frente a pasar por alto un quiebre.')
