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
        self.assertEqual(int(app.metric[0].value), len(stock))
        self.assertEqual(int(app.metric[2].value), stock['stock_actual'].eq(0).sum())
        self.assertEqual(int(app.metric[3].value), stock['stock_actual'].lt(stock['stock_minimo']).sum())

    def test_demo_inicia_y_filtra_categoria(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.verificar_indicadores(app, self.stock)
        self.assertIn('Modelo de alertas', [control.label for control in app.selectbox])
        self.assertIn('Ver fichas de los productos seleccionados', [e.label for e in app.expander])
        app.multiselect(key='categorias').set_value(['Bebidas']).run()
        self.assertFalse(app.exception)
        self.verificar_indicadores(app, self.stock[self.stock['categoria'].eq('Bebidas')])
        app.radio(key='frecuencia_ventas').set_value('Por día').run()
        self.assertFalse(app.exception)

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
        self.assertEqual(app.metric[0].value, '1')
        self.assertEqual(app.metric[1].value, '0')

    def test_fecha_incompleta_no_muestra_resultados_enganosos(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.date_input(key='periodo').set_value((date.fromisoformat(self.corte),)).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertEqual(len(app.metric), 0)

    def test_reposicion_sin_cambios_coincide_con_base(self):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertFalse(app.exception)
        self.assertIn('Reposición y escenarios', [p.label for p in app.tabs])
        codigo = self.stock.loc[self.stock['stock_actual'].eq(0), 'producto_id'].iloc[0]
        app.multiselect(key='productos').set_value([codigo]).run()
        self.assertFalse(app.exception)
        base = next(m.value for m in app.metric if m.label == 'Unidades sugeridas · base')
        self.assertGreater(int(base.replace(' ', '')), 0)
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · escenario'), base)
        self.assertTrue(app.info)  # No hay suficientes productos para segmentar.

    def test_estres_aumenta_propuesta_y_parametros_no_alteran_ventas(self):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        unidades = app.metric[1].value
        base = int(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · base').replace(' ', ''))
        app.slider(key='variacion_demanda').set_value(50).run()
        self.assertFalse(app.exception)
        escenario = int(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · escenario').replace(' ', ''))
        self.assertGreater(escenario, base)
        self.assertEqual(app.metric[1].value, unidades)


if __name__ == '__main__':
    unittest.main()
