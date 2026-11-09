# Tottus Dashboard

Sistema de soporte de decisiones para el análisis de ventas, inventario y reposición.

Reunimos las ventas históricas y el stock disponible para identificar los productos que necesitan reposición. El dashboard se puede explorar con datos de ejemplo o con archivos CSV propios.

## Funciones

Integramos el análisis de ventas e inventario con una política de reposición:

- Indicadores de productos analizados, unidades vendidas, productos sin stock y productos bajo el mínimo.
- Filtros por categoría, producto, periodo de ventas y fecha de corte del inventario.
- Gráficos de evolución diaria de ventas y ventas por categoría.
- Alertas de productos sin stock o bajo el mínimo establecido.
- Detalle de inventario y comparación del stock actual frente al mínimo.
- Carga y validación de archivos CSV.
- Descarga del reporte de inventario.
- Demanda de referencia mediante media móvil sobre un histórico diario completo.
- Evaluación temporal de ventas acumuladas a 1, 3, 7 o 14 días con MAE, RMSE y WAPE.
- Punto de reorden, cobertura, prioridad de atención y cantidad sugerida explicada.
- Comparación What-If de demanda, plazo de entrega y stock.
- Segmentación por venta diaria y variabilidad con K-means, K-medoids y Ward.
- Alertas para el próximo cierre con CART, Random Forest y SVM. Podemos ajustar el umbral y comparar los quiebres detectados y omitidos.

La prioridad indica el orden de atención según el stock disponible y la demanda estimada; no expresa una probabilidad de quiebre.

## Tecnologías

- Python.
- pandas para carga, validación, integración y análisis de datos.
- Streamlit para la interfaz y los gráficos interactivos.
- CSV como fuente de datos.
- scikit-learn para agrupamiento, estandarización y métricas.

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

Los archivos de [`data/demo`](data/demo) contienen datos simulados. Las ventas atendidas, el saldo diario y el corte de inventario proceden de la misma simulación.

En el corte de ejemplo hay 1 producto sin stock y 8 bajo el mínimo. El producto sin stock también está incluido en el segundo indicador, por lo que ambos conteos no deben sumarse.

Para regenerar los mismos datos en Windows:

```powershell
.\.venv\Scripts\python.exe scripts/generar_demo.py
```

El script utiliza semillas fijas y reemplaza los cuatro CSV de ejemplo. `historial_stock.csv` conserva las ventas atendidas y el stock al cierre de cada día para el panel de alertas.

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

Para calcular **Alertas de quiebre** con archivos propios, carga también `historial_stock.csv` desde esa pestaña. Este archivo es opcional para el resto del dashboard. Debe contener el stock al cierre y las ventas de cada producto por día.

## Estructura del proyecto

```text
app.py                      Interfaz, filtros y visualizaciones.
assets/tottus.svg            Logo del encabezado y la barra lateral.
src/
  datos.py                  Lectura y validación de CSV.
  indicadores.py            Integración de datos y cálculo de indicadores.
  demanda.py                Media móvil y evaluación temporal.
  reposicion.py             Política de reposición y escenarios.
  segmentacion.py           Agrupamiento K-means y perfiles.
  panel_analisis.py          Paneles de análisis y comparación.
  quiebres.py                Variables, clasificadores y evaluación por fecha.
  panel_quiebres.py          Alertas, curvas y matriz de confusión.
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

Comprobamos la validación de los CSV, los indicadores, el tratamiento de datos faltantes, la ausencia de información futura en las predicciones, las fórmulas de reposición, la reproducibilidad de los grupos y los filtros de la interfaz.

## Análisis de demanda y reposición

La **vista general** mantiene las alertas de stock frente al mínimo del CSV. La **brecha al mínimo** describe ese faltante y es independiente de la política del panel **Reposición y escenarios**.

La demanda de referencia es el promedio de ventas diarias de los últimos 28 días hasta el corte de inventario. La ventana puede cambiarse entre 14, 28, 42 y 56 días. Exigimos registros para todos los días; los ceros conocidos son válidos y los días ausentes no se imputan. El filtro de periodo afecta a la vista descriptiva; los modelos utilizan su ventana hasta el corte.

La política base usa un plazo de entrega de 3 días, revisión cada 7 días y seguridad de 2 días de venta estimada. Podemos modificar estos parámetros desde el panel:

1. Stock de seguridad = venta diaria estimada × días de seguridad.
2. Punto de reorden = venta diaria estimada × plazo de entrega + stock de seguridad.
3. Stock objetivo = venta diaria estimada × (plazo + revisión) + stock de seguridad.
4. Si el stock está en o bajo el punto de reorden, sugerimos la diferencia hasta el objetivo; de otro modo, la sugerencia es cero.

Redondeamos hacia arriba seguridad, reorden y objetivo. No se calculan cantidades con histórico incompleto o inventario desconocido. El escenario modifica demanda, plazo y stock sin cambiar los CSV; su descarga incluye los parámetros utilizados.

La prioridad **alta** indica que el stock no supera las ventas estimadas durante el plazo. La **media** indica que se alcanza el punto de reorden con su colchón de seguridad, y la **baja** que el stock supera ese punto. Si no hay ventas en toda la ventana, mostramos **Sin demanda reciente**, con cantidad cero bajo ese supuesto.

## Evaluación, segmentación y alertas

- **Evaluación temporal:** comparamos la media móvil y una referencia semanal sobre 14 fechas de inicio por producto. El horizonte configurable acumula las ventas previstas y observadas. Cada estimación usa solo datos anteriores a su inicio. MAE y RMSE miden el error en unidades del horizonte; WAPE queda vacío si el total observado es cero.
- **Segmentación:** comparamos K-means, K-medoids y Ward sobre las mismas variables estandarizadas. Mostramos perfiles en escala original, productos representativos y silueta. K-means incluye el análisis del codo; Ward muestra el dendrograma.
- **Alertas:** entrenamos CART, Random Forest y SVM para anticipar stock cero en el siguiente cierre. Los bloques de evaluación se separan por fecha. El panel muestra precisión, recall, F1, ROC-AUC, AP y la matriz de confusión. El puntaje ordena la atención y es independiente de la cantidad sugerida de reposición.

La [metodología del análisis](docs/metodologia-analisis.md) detalla supuestos, fórmulas, evaluación y relación con las sesiones de clase.

## Siguientes pasos

En las siguientes etapas trabajaremos en:

1. Calibrar parámetros por producto con datos operativos.
2. Contrastar el desempeño con más temporadas y horizontes de reposición.
3. Incorporar pedidos en tránsito, reservas, lotes mínimos y restricciones de compra.
4. Calibrar las alertas con históricos operativos y medir su costo de omisión.

El proyecto funciona de manera local y no se conecta a sistemas internos de Tottus. La decisión final de reposición corresponde al responsable de abastecimiento.

