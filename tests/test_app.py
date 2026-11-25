from pathlib import Path
from datetime import date
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / 'app.py'
DEMO = APP.parent / 'data' / 'demo'


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.productos = pd.read_csv(DEMO / 'productos.csv', sep=';', dtype={'producto_id': str})
        inventario = pd.read_csv(DEMO / 'inventario.csv', sep=';', dtype={'producto_id': str})
        cls.corte = inventario['fecha_corte'].max()
        cls.stock = inventario[inventario['fecha_corte'].eq(cls.corte)].merge(cls.productos, on='producto_id')

    def verificar_indicadores(self, app, stock):
        self.assertEqual([m.label for m in app.metric[:3]],
                         ['Unidades vendidas', 'Productos sin stock', 'Stock bajo, aún disponible'])
        self.assertEqual(int(app.metric[1].value), stock['stock_actual'].eq(0).sum())
        bajo = stock['stock_actual'].gt(0) & stock['stock_actual'].lt(stock['stock_minimo'])
        self.assertEqual(int(app.metric[2].value), bajo.sum())
        self.assertIn(f'Productos analizados · {len(stock)}', [c.value for c in app.sidebar.caption])

    def test_demo_inicia_y_filtra_categoria(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.verificar_indicadores(app, self.stock)
        self.assertEqual([tab.label for tab in app.tabs],
                         ['Vista general', 'Inventario', 'Reposición', 'Escenarios What-If',
                          'Pronóstico y modelos', 'Datos y alcance'])
        self.assertNotIn('Modelo de alertas', [control.label for control in app.selectbox])
        self.assertIn('Ver fichas de los productos seleccionados', [e.label for e in app.expander])
        app.multiselect(key='categorias').set_value(['Bebidas']).run()
        self.assertFalse(app.exception)
        self.verificar_indicadores(app, self.stock[self.stock['categoria'].eq('Bebidas')])
        app.radio(key='frecuencia_ventas').set_value('Por día').run()
        self.assertFalse(app.exception)
        app.selectbox(key='analisis_avanzado').set_value('Alertas de quiebre').run(timeout=60)
        self.assertFalse(app.exception)
        self.assertIn('Modelo de alertas', [control.label for control in app.selectbox])
        app.selectbox(key='modelo_quiebres').set_value('SVM (RBF)')
        app.slider(key='umbral_quiebres').set_value(.75).run()
        app.selectbox(key='analisis_avanzado').set_value('Evaluación de demanda').run()
        sku = self.productos.loc[self.productos['categoria'].eq('Bebidas'), 'producto_id'].iloc[-1]
        app.selectbox(key='producto_evaluacion').set_value(sku).run()
        app.selectbox(key='analisis_avanzado').set_value('Alertas de quiebre').run()
        self.assertEqual(app.selectbox(key='modelo_quiebres').value, 'SVM (RBF)')
        self.assertEqual(app.slider(key='umbral_quiebres').value, .75)
        app.selectbox(key='analisis_avanzado').set_value('Evaluación de demanda').run()
        self.assertEqual(app.selectbox(key='producto_evaluacion').value, sku)

    def test_catalogo_sin_seleccion_y_carga_pendiente(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.multiselect(key='categorias').set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        app.radio(key='fuente').set_value('Cargar mis CSV').run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)

    def test_producto_con_cero_ventas(self):
        historial = pd.read_csv(DEMO / 'historial_stock.csv', sep=';', dtype={'producto_id': str})
        fila = historial.loc[historial['unidades_vendidas'].eq(0) & historial['stock_cierre'].gt(0)].iloc[0]
        dia = date.fromisoformat(fila['fecha'])
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.date_input(key='periodo').set_value((dia, dia))
        app.multiselect(key='productos').set_value([fila['producto_id']]).run()
        self.assertFalse(app.exception)
        self.assertIn('Productos analizados · 1', [c.value for c in app.sidebar.caption])
        self.assertEqual(app.metric[0].value, '0')

    def test_fecha_incompleta_no_muestra_resultados_enganosos(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.date_input(key='periodo').set_value((date.fromisoformat(self.corte),)).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertEqual(len(app.metric), 0)

    def test_historial_propio_se_conserva_al_cambiar_de_analisis(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.radio(key='fuente').set_value('Cargar mis CSV').run()
        archivos = {
            'productos': b'producto_id;nombre;categoria\n001;Arroz;Abarrotes\n',
            'ventas': b'fecha;producto_id;unidades_vendidas\n2026-10-01;001;2\n',
            'inventario': b'fecha_corte;producto_id;stock_actual;stock_minimo\n2026-10-01;001;5;1\n',
        }
        for tipo, contenido in archivos.items():
            app.file_uploader(key=f'archivo_{tipo}').upload(f'{tipo}.csv', contenido, 'text/csv')
        app.run()
        app.selectbox(key='analisis_avanzado').set_value('Alertas de quiebre').run()
        historial = b'fecha;producto_id;unidades_vendidas;stock_cierre\n2026-10-01;001;2;5\n'
        app.file_uploader(key='historial_stock').upload('historial_stock.csv', historial, 'text/csv').run()
        app.selectbox(key='analisis_avanzado').set_value('Evaluación de demanda').run()
        app.selectbox(key='analisis_avanzado').set_value('Alertas de quiebre').run()
        self.assertFalse(app.exception)
        self.assertIsNotNone(app.file_uploader(key='historial_stock').value)

    def test_reposicion_sin_cambios_coincide_con_base(self):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertFalse(app.exception)
        columnas = ['Producto', 'Stock actual', 'Demanda diaria', 'Punto de reorden',
                    'Prioridad por riesgo', 'Cantidad sugerida']
        self.assertTrue(any(list(tabla.value.columns) == columnas for tabla in app.dataframe))
        codigo = self.stock.loc[self.stock['stock_actual'].eq(0), 'producto_id'].iloc[0]
        app.multiselect(key='productos').set_value([codigo]).run()
        self.assertFalse(app.exception)
        base = next(m.value for m in app.metric if m.label == 'Unidades sugeridas · base')
        self.assertGreater(int(base.replace(' ', '')), 0)
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · escenario'), base)

    def test_estres_aumenta_propuesta_y_parametros_no_alteran_ventas(self):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        unidades = app.metric[0].value
        base = int(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · base').replace(' ', ''))
        app.slider(key='variacion_demanda').set_value(50).run()
        self.assertFalse(app.exception)
        escenario = int(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · escenario').replace(' ', ''))
        self.assertGreater(escenario, base)
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · base'),
                         f'{base:,}'.replace(',', ' '))
        self.assertEqual(app.metric[0].value, unidades)

    def test_escenarios_lrpd_sensibilidad_y_meta(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.multiselect(key='productos').set_value(['113708338']).run()
        for caso, esperado in [('escenario_favorable', '78'), ('escenario_estres', '165')]:
            app.button(key=caso).click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.warning)
            self.assertEqual(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · escenario'), esperado)
        tabla = next(t.value for t in app.dataframe if 'Variación de demanda (%)' in t.value)
        self.assertEqual(tabla.loc[tabla['Variación de demanda (%)'].eq(0), 'Cantidad sugerida'].item(), 110)
        app.number_input(key='dias_meta_cobertura').set_value(5).run()
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Stock para la meta'), '57')
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Unidades que faltan'), '30')

    def test_meta_entera_no_sube_una_unidad_por_redondeo_binario(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.radio(key='fuente').set_value('Cargar mis CSV').run()
        dias = pd.date_range('2026-10-01', periods=14)
        ventas = pd.DataFrame({'fecha': dias.strftime('%Y-%m-%d'), 'producto_id': '001',
                               'unidades_vendidas': [9] + [0] * 13})
        archivos = {
            'productos': b'producto_id;nombre;categoria\n001;Arroz;Abarrotes\n',
            'ventas': ventas.to_csv(sep=';', index=False).encode('utf-8'),
            'inventario': b'fecha_corte;producto_id;stock_actual;stock_minimo\n2026-10-14;001;5;1\n',
        }
        for tipo, contenido in archivos.items():
            app.file_uploader(key=f'archivo_{tipo}').upload(f'{tipo}.csv', contenido, 'text/csv')
        app.run()
        app.selectbox(key='ventana_modelo').set_value(14).run()
        app.number_input(key='dias_meta_cobertura').set_value(42).run()
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Stock para la meta'), '27')


if __name__ == '__main__':
    unittest.main()
