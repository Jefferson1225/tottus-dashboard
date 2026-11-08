import unittest

import pandas as pd

from src.segmentacion import segmentar_productos


class SegmentacionTests(unittest.TestCase):
    def test_grupos_reproducibles_y_perfiles_en_escala_original(self):
        demanda = pd.DataFrame({'producto_id': ['01', '02', '03', '04', '05', '06'],
                                'nombre': list('ABCDEF'), 'categoria': ['A'] * 6,
                                'demanda_diaria': [1., 1.1, 10., 10.1, 100., 101.],
                                'cv': [0.1] * 6})
        asignados, perfiles, silueta = segmentar_productos(demanda, 3)
        otros, _, _ = segmentar_productos(demanda, 3)
        self.assertEqual(asignados['segmento'].tolist(), otros['segmento'].tolist())
        por_id = asignados.set_index('producto_id')
        self.assertEqual(por_id.loc['01', 'segmento'], por_id.loc['02', 'segmento'])
        self.assertNotEqual(por_id.loc['01', 'segmento'], por_id.loc['06', 'segmento'])
        self.assertEqual(perfiles['productos'].sum(), 6)
        self.assertAlmostEqual(perfiles['demanda_media'].max(), 100.5)
        self.assertTrue(-1 <= silueta <= 1)

    def test_excluye_historial_desconocido_y_rechaza_falta_de_variacion(self):
        demanda = pd.DataFrame({'producto_id': ['01', '02', '03'],
                                'demanda_diaria': [10., 10., float('nan')], 'cv': [0., 0., 0.]})
        with self.assertRaises(ValueError):
            segmentar_productos(demanda, 2)


if __name__ == '__main__':
    unittest.main()
