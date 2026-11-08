from pathlib import Path
from datetime import date
import unittest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / 'app.py'


class DashboardTests(unittest.TestCase):
    def test_demo_inicia_y_filtra_categoria(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '16')
        self.assertEqual(app.metric[2].value, '3')
        self.assertEqual(app.metric[3].value, '6')
        app.multiselect(key='categorias').set_value(['Bebidas']).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '4')
        self.assertEqual(app.metric[2].value, '1')
        self.assertEqual(app.metric[3].value, '1')

    def test_catalogo_sin_seleccion_y_carga_pendiente(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.multiselect(key='categorias').set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        app.radio(key='fuente').set_value('Cargar mis CSV').run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)

    def test_producto_con_cero_ventas(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.multiselect(key='productos').set_value(['0016']).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '1')
        self.assertEqual(app.metric[1].value, '0')
        self.assertEqual(app.metric[2].value, '0')

    def test_fecha_incompleta_no_muestra_resultados_enganosos(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.date_input(key='periodo').set_value((date(2026, 10, 22),)).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertEqual(len(app.metric), 0)

    def test_reposicion_compara_escenario_y_respeta_demanda_nula(self):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertFalse(app.exception)
        self.assertIn('Reposición y escenarios', [p.label for p in app.tabs])
        app.multiselect(key='productos').set_value(['0016']).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · base'), '0')
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Unidades sugeridas · escenario'), '0')
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
