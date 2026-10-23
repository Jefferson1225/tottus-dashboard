# Tottus Dashboard

Sistema de soporte de decisiones para el análisis de ventas e inventario, desarrollado como proyecto del curso de Sistemas de Soporte de Decisiones.

Nuestro objetivo es apoyar la reposición de productos mediante un dashboard que reúna las ventas históricas, el stock disponible y los productos que requieren atención. Tomamos a Tottus como caso de estudio y trabajamos con datos simulados para fines académicos.

## Primer avance

En esta versión implementamos el análisis descriptivo de ventas e inventario:

- Indicadores de productos analizados, unidades vendidas, productos sin stock y productos bajo el mínimo.
- Filtros por categoría, producto, periodo de ventas y fecha de corte del inventario.
- Gráficos de evolución diaria de ventas y ventas por categoría.
- Alertas de productos sin stock o bajo el mínimo establecido.
- Detalle de inventario y comparación del stock actual frente al mínimo.
- Carga y validación de archivos CSV.
- Descarga del reporte de inventario.

El pronóstico de demanda, el punto de reorden y los escenarios de reposición forman parte de las siguientes etapas.

## Tecnologías

- Python.
- pandas para carga, validación, integración y análisis de datos.
- Streamlit para la interfaz y los gráficos interactivos.
- CSV como fuente de datos.

## Instalación y ejecución

El proyecto se ha probado con Python 3.14. Desde una terminal:

```bash
git clone https://github.com/Jefferson1225/tottus-dashboard.git
cd tottus-dashboard
python -m venv .venv
```

En Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

En Linux o macOS:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Abrir la dirección que muestra Streamlit, normalmente `http://127.0.0.1:8501`. Para detener la aplicación, presionar `Ctrl+C` en la terminal.

En Windows también se puede ejecutar `iniciar_dashboard.bat` después de instalar las dependencias.

## Datos de demostración

Incluimos un conjunto de datos para ejecutar el dashboard desde el primer inicio:

| Dato | Contenido |
| --- | --- |
| Productos | 16 |
| Categorías | Abarrotes, Bebidas, Limpieza y Cuidado personal |
| Periodo de ventas | 01/08/2026 al 22/10/2026 |
| Registros diarios | 1 328 |
| Corte de inventario | 22/10/2026 |
| Ámbito | Una sede ficticia de demostración |

Los archivos se encuentran en [`data/demo`](data/demo). No corresponden a operaciones reales de Tottus. El stock es una fotografía preparada para el ejercicio y no se reconstruye a partir de un libro de entradas y salidas.

En la demo hay 3 productos sin stock y 6 bajo el mínimo. Los productos sin stock también están incluidos en el segundo indicador, por lo que ambos conteos no deben sumarse.

Para regenerar los mismos datos en Windows:

```powershell
.\.venv\Scripts\python.exe scripts/generar_demo.py
```

El script utiliza una semilla fija y reemplaza únicamente los tres CSV de demostración.

## Carga de archivos CSV

En el menú lateral, seleccionar **Cargar mis CSV** y adjuntar los tres archivos:

| Archivo | Columnas requeridas |
| --- | --- |
| `productos.csv` | `producto_id`, `nombre`, `categoria` |
| `ventas.csv` | `fecha`, `producto_id`, `unidades_vendidas` |
| `inventario.csv` | `fecha_corte`, `producto_id`, `stock_actual`, `stock_minimo` |

Usamos codificación UTF-8, separador `;`, fechas `AAAA-MM-DD` y cantidades enteras no negativas. Los códigos de producto se tratan como texto para conservar sus ceros iniciales.

La aplicación valida campos obligatorios, fechas, cantidades, claves duplicadas y referencias al catálogo antes de calcular los indicadores. Los archivos se procesan durante la sesión y no reemplazan la demo.

El periodo seleccionado filtra las ventas; el stock corresponde a la fecha de corte elegida. Si falta un producto en el inventario, se muestra como **Sin datos**, no como stock cero. La ausencia de registros de ventas tampoco se interpreta automáticamente como cero ventas.

El [diccionario de datos](docs/diccionario-datos.md) detalla los campos y las reglas utilizadas.

## Estructura del proyecto

```text
app.py                      Interfaz, filtros y visualizaciones.
src/
  datos.py                  Lectura y validación de CSV.
  indicadores.py            Integración de datos y cálculo de indicadores.
data/demo/                  Datos de demostración.
scripts/generar_demo.py     Generación reproducible de los CSV.
tests/                      Pruebas de datos, indicadores e interfaz.
docs/                       Diccionario de datos.
.streamlit/config.toml      Configuración visual y del servidor local.
requirements.txt            Dependencias del proyecto.
iniciar_dashboard.bat       Inicio en Windows.
```

## Pruebas

Para ejecutar las pruebas en Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

En Linux o macOS, utilizar `.venv/bin/python` en lugar de `.\.venv\Scripts\python.exe`.

Comprobamos la validación de los CSV, el cálculo de los indicadores, el tratamiento de datos faltantes y el funcionamiento de los filtros de la interfaz.

## Alcance actual y siguientes pasos

Las alertas de esta versión comparan el stock disponible con el mínimo definido en el archivo. La **brecha al mínimo** indica cuántas unidades faltan para llegar a ese umbral; todavía no constituye una recomendación de compra.

En las siguientes etapas trabajaremos en:

1. Estimación y evaluación de la demanda.
2. Cálculo del punto de reorden.
3. Clasificación del riesgo de quiebre de stock.
4. Recomendaciones de reposición explicadas por producto.
5. Comparación de escenarios What-If.

El proyecto funciona de manera local y no se conecta a sistemas internos de Tottus. La decisión final de reposición corresponde al responsable de abastecimiento.

