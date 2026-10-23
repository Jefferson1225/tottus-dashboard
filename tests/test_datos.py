import io
import unittest

import pandas as pd

from src.datos import ErrorDatos, cargar_csv, validar_relaciones


class DatosTests(unittest.TestCase):
    def test_conserva_ceros_del_identificador(self):
        tabla = cargar_csv(io.BytesIO(b'producto_id;nombre;categoria\n001;Arroz;Abarrotes\n'), 'productos')
        self.assertEqual(tabla.iloc[0]['producto_id'], '001')

    def test_rechaza_datos_invalidos_sin_descartarlos(self):
        casos = [
            ('producto_id;nombre\n001;Arroz\n', 'productos'),
            ('producto_id;nombre;categoria\n001;Arroz;A\n001;Aceite;A\n', 'productos'),
            ('producto_id;nombre;categoria\n001; ;A\n', 'productos'),
            ('fecha;producto_id;unidades_vendidas\n2026-02-30;001;2\n', 'ventas'),
            ('fecha;producto_id;unidades_vendidas\n2026-10-01;001;-1\n', 'ventas'),
            ('fecha;producto_id;unidades_vendidas\n2026-10-01;001;1.5\n', 'ventas'),
            ('fecha;producto_id;unidades_vendidas\n2026-10-01;001;inf\n', 'ventas'),
            ('fecha;producto_id;unidades_vendidas\n2026-10-01;001;\n', 'ventas'),
            ('producto_id;nombre;categoria\n', 'productos'),
        ]
        for contenido, tipo in casos:
            with self.subTest(contenido=contenido), self.assertRaises(ErrorDatos):
                cargar_csv(io.BytesIO(contenido.encode()), tipo)

    def test_rechaza_producto_ajeno_al_catalogo(self):
        productos = pd.DataFrame({'producto_id': ['001']})
        ventas = pd.DataFrame({'producto_id': ['999']})
        inventario = pd.DataFrame({'producto_id': ['001']})
        with self.assertRaises(ErrorDatos):
            validar_relaciones(productos, ventas, inventario)

    def test_rechaza_fila_con_mas_campos_que_el_encabezado(self):
        contenido = b'producto_id;nombre;categoria\n001;Arroz;A;EXTRA\n'
        with self.assertRaises(ErrorDatos):
            cargar_csv(io.BytesIO(contenido), 'productos')

    def test_rechaza_encabezados_duplicados_con_stocks_contradictorios(self):
        contenido = (b'fecha_corte;producto_id;stock_actual;stock_actual;stock_minimo\n'
                     b'2026-10-22;001;100;0;10\n')
        with self.assertRaises(ErrorDatos):
            cargar_csv(io.BytesIO(contenido), 'inventario')


if __name__ == '__main__':
    unittest.main()
