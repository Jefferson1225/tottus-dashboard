# Metodología de demanda, reposición y segmentación

Desarrollamos este avance para relacionar el histórico de ventas con una política de inventario explicable. Los resultados utilizan datos simulados y no representan políticas verificadas de Tottus.

## Fecha de análisis y calidad del histórico

El corte elegido del inventario es también el cierre del histórico de los modelos. La ventana diaria predeterminada es de 28 días, incluidos sus ceros explícitos. Por producto, una fecha faltante deja la demanda desconocida; no asumimos ventas nulas, no interpolamos y no usamos registros posteriores al corte.

El periodo de la vista descriptiva es independiente: cambiar ese filtro no cambia la ventana del modelo. Cada panel indica qué periodo utiliza.

## Demanda de referencia

Usamos la media de unidades vendidas por día en la ventana completa. La tratamos como una referencia de demanda futura constante; no incorpora automáticamente promociones ni estacionalidad. Calculamos también la desviación estándar poblacional y el coeficiente de variación (CV = desviación / media). En una ventana completa de ceros asignamos CV igual a cero.

Las ventas observadas pueden ser inferiores a la demanda cuando hubo falta de stock. Sin un registro de demanda perdida, el modelo no corrige ese sesgo. Un producto sin ventas requiere revisión antes de decidir su abastecimiento.

## Evaluación temporal

Los últimos 14 días hasta el corte constituyen una evaluación exploratoria. Exigimos una secuencia completa de `ventana + 14` días por producto, de modo que los dos métodos compartan muestra:

- **Media móvil:** promedio de la ventana estrictamente anterior a cada día objetivo.
- **Ingenuo semanal:** unidades observadas exactamente siete días antes del objetivo.

Avanzamos un origen por día e incorporamos únicamente las observaciones ya conocidas. No mezclamos fechas aleatoriamente ni entrenamos con el valor del día a predecir. Es un backtest secuencial de un paso; no una predicción simultánea de 14 días.

Informamos MAE, RMSE y WAPE sobre pares producto-día. MAE = promedio de errores absolutos; RMSE = raíz del promedio de errores cuadrados; WAPE = 100 × suma de errores absolutos / suma de ventas reales. WAPE queda vacío si el denominador es cero. No mostramos un porcentaje de acierto para esta tarea numérica.

La ventana es un control de exploración. No elegimos automáticamente el modelo con el error mínimo de este periodo ni lo presentamos como una prueba final independiente. Una evaluación de un día tampoco demuestra el desempeño al plazo completo de reposición.

## Política de reposición

Definimos `d` como venta diaria de referencia, `L` como plazo de entrega, `R` como intervalo de revisión y `B` como días de seguridad. Los valores iniciales son L = 3, R = 7 y B = 2 días.

- Seguridad: `S = ceil(d × B)` unidades.
- Punto de reorden: `P = ceil(d × L + S)` unidades.
- Objetivo: `T = ceil(d × (L + R) + S)` unidades.
- Si el stock `I ≤ P`, cantidad sugerida `Q = max(T − I, 0)`; si `I > P`, `Q = 0`.
- Cobertura: `I / d` días cuando `d > 0`. Con ventas nulas no informamos una cobertura numérica.

El stock mínimo del CSV es un umbral descriptivo y no se reutiliza como si fuera el stock de seguridad calculado.

La prioridad es **alta** cuando `I ≤ d × L`; **media** cuando el inventario alcanza el punto de reorden pero supera la venta estimada durante el plazo; **baja** cuando `I > P`. Se presenta **Sin demanda reciente** para una ventana completa de ceros, **Demanda simulada nula** cuando el escenario reduce a cero una demanda base positiva, y **No evaluable** si faltan demanda o inventario. Estas categorías son reglas y no probabilidades ni eventos observados de quiebre.

Suponemos inventario disponible igual a stock actual, sin reservas ni pedidos en tránsito. El objetivo combina plazo y revisión, sujeto al disparador del punto de reorden; es una política simplificada del ejercicio. No optimiza costos, lotes, vencimientos, presupuesto o capacidad. La decisión de compra requiere revisión humana.

## Escenarios What-If

El escenario conserva los archivos y aplica tres cambios comunes a la selección:

- Demanda ajustada = `d × (1 + variación_demanda / 100)`.
- Plazo ajustado = plazo base + retraso adicional.
- Stock ajustado = `floor(I × (1 + variación_stock / 100))`.

Recalculamos seguridad, punto de reorden, objetivo y cantidades con esos valores. Con tres cambios iguales a cero, los resultados son idénticos a los de la política base. El CSV de comparación incluye los parámetros, el corte y la ventana para interpretar la propuesta.

## Segmentación de productos

Aplicamos StandardScaler a venta diaria media y CV, seguidos de K-means con `random_state=42` y `n_init=10`. Exigimos tantos perfiles distintos como grupos solicitados. Los productos con histórico incompleto se excluyen y se informa su cantidad.

Los números de clúster no tienen significado comercial por sí solos. Ordenamos los perfiles por venta diaria media y mostramos los promedios sin estandarizar para interpretarlos. Los grupos son relativos al catálogo filtrado y pueden cambiar al modificar la selección o la ventana.

La silueta resume separación y cohesión en las variables estandarizadas, entre -1 y 1. Solo se calcula con al menos dos grupos y más observaciones que grupos. No mide exactitud predictiva ni garantiza un número óptimo de segmentos.

## Relación con las clases

- Sesión 09: escalado, K-means y perfilamiento, adaptados de clientes a productos sin introducir datos personales.
- Sesión 11: errores de regresión y validación temporal sin información futura.
- Sesión 10: clasificación supervisada como línea futura, condicionada a disponer de un histórico de quiebres etiquetado. No generamos etiquetas a partir de las reglas para luego afirmar que un clasificador predice quiebres reales.

Las consignas y ejemplos del material de clase son referencias de aprendizaje. No forman un conjunto adicional de funcionalidades obligatorias del proyecto.

Referencias técnicas: [K-means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html), [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html), [MAE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html), [RMSE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html) y [silueta](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html).
