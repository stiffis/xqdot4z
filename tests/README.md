# Pruebas del contrato numérico XQDot4Z

[test_xqdot4z.py](test_xqdot4z.py) usa unittest de la biblioteca estándar.
Los [ejemplos](data/qdot4z_examples.json) son valores esperados explícitos,
no resultados obtenidos de un RTL.

```sh
# Desde la raíz del proyecto:
make model-test
# Solo pruebas, sin exportar evidencia:
python3 -m unittest discover -s tests -p test_xqdot4z.py -v
```

La batería consta de 15 tests agrupados. Sus bucles comprueban:

| Grupo | Casos |
|---|---:|
| Ejemplos documentados | 4 |
| Código U4 en cada posición | 128 |
| Valor S8 en cada posición | 1024 |
| Ternas (peso, punto cero, activación) | 65 536 |
| Ternas insertadas en las ocho posiciones de W | 524 288 |
| Entradas completas aleatorias, semilla 20260908 | 10 000 |
| Productos punto aleatorios, dos mitades por entrada | 20 000 |
| Invariancia respecto de pesos no seleccionados | 1000 entradas |
| Pares de puntos cero para identidad afín | 256 |
| Permutaciones conjuntas de cuatro elementos | 24 |
| Patrones S32 del intervalo [−7680, 7680] | 15 361 |

También se comprueban cancelación, entradas neutras, relleno de colas,
little-endian, límites de tipos/ancho y rechazo de longitudes incorrectas.
Las cantidades de esta tabla no deben sumarse como si fueran dominios
independientes: por ejemplo, las 524 288 inserciones reutilizan las 65 536 ternas.

Las expectativas usan aritmética factorizada, valores manuales y operaciones
de bytes/struct independientes de las funciones de packing del modelo.
Esta batería M1 no compara hardware ni cubre completamente las entradas
de 69 bits de la operación.

## Pruebas RTL separadas — M2

`make rtl-test` ejecuta [tb_xqdot4z.sv](rtl/tb_xqdot4z.sv) en Icarus y
Verilator contra 556 734 vectores revisados con el oráculo Python. Incluye
ocho controles negativos por simulador y cuatro mutaciones del diseño en
Icarus. El [desglose y las instrucciones](../rtl/README.md) distinguen
comparaciones, ternas y pares de invariancia; no deben sumarse los conteos
de M1 y M2 como si fueran entradas independientes.

Las pruebas del procesador están en `../kuntur/verification/` y no se mezclan
con esta batería. La integración inmediata se verifica por separado en
[M3a](integration/README.md), sin modificar la referencia ni el banco M2.
La base común MUL se verifica mediante `make scalar-test` en
[tests/scalar](scalar/README.md), con aritmética, decode, pipeline y convivencia.
La aritmética B3 aislada se verifica con `make packed-test` en
[tests/packed](packed/README.md), incluyendo reconstrucción de salidas por
fila/grupo desde respuestas de las unidades; no son kernels en el core.
`make packed-integration-test` verifica la [ISA y el pipeline B3](packed_integration/README.md),
incluidos fixtures que sí ejecutan Sa y corrección dentro de Kuntur,
sin convertir esos programas dirigidos en mediciones de rendimiento.
