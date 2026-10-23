# Datos simulados para fines académicos

Estos archivos no representan operaciones reales de Tottus.

- Ámbito: una sede ficticia de demostración.
- Catálogo: 16 productos contables de 4 categorías; no se incluyen productos vendidos por peso.
- Ventas: 83 días completos, del 01/08/2026 al 22/10/2026, por producto. Incluye ceros explícitos para un producto sin ventas.
- Inventario: fotografía preparada al 22/10/2026. No se deriva de las ventas ni de un libro de movimientos; no se dispone de entradas, reservas o pedidos en tránsito.
- Fuente: `scripts/generar_demo.py`, semilla fija `20261022` del generador estándar de Python. Permite reproducir los CSV sin una API externa.
- Formato: UTF-8, separado por `;`, fechas `AAAA-MM-DD` y códigos de texto con ceros iniciales.

Controles manuales del corte: 16 productos, 3 con stock cero y 6 con stock menor que el mínimo. Los 3 productos sin stock también están dentro de los 6 bajo mínimo; no se suman ambos contadores. Hay 1 producto exactamente en su mínimo.
