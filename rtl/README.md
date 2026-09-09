# Unidad aritmética XQDot4Z — M2

[xqdot4z.v](xqdot4z.v) implementa el [contrato numérico v0.1](../model/SPEC.md)
como una unidad combinacional de cuatro vías. M2 verifica este módulo aislado.
La fase posterior [M3a](../isa/SPEC.md) lo instancia opcionalmente en Kuntur;
no se modificó la unidad para esa integración. El contrato numérico y la
interfaz ISA se versionan por separado.

El candidato B3 sin corrección se desarrolla por separado en
[packed/xqdot4.v](packed/xqdot4.v), con su [contrato](packed/SPEC.md) y
[batería aislada](../tests/packed/README.md). Esa unidad no modifica M2.
Su [interfaz ISA](../isa/packed/SPEC.md) la integra opcionalmente en Kuntur,
con [pruebas propias](../tests/packed_integration/README.md).

## Interfaz y decisiones

| Puerto | Bits | Uso |
|---|---:|---|
| `weights_word` | 32 | Ocho códigos U4; índice cero en bits bajos |
| `activations_word` | 32 | Cuatro bytes S8; índice cero en bits bajos |
| `zero_point` | 4 | Un U4 compartido por los cuatro términos |
| `half` | 1 | Elige cuatro pesos bajos/altos, sin cambiar las activaciones |
| `result` | 32 | Subtotal exacto en complemento a dos, extendido con signo |

Se extienden los U4 con cero antes de restarlos como S5. Cada vía conserva
un producto S13; las sumas de parejas usan S14 y la suma final S15.
Después se extiende a 32 bits. Los anchos son conservadores: el resultado
legal está en [−7680, 7680], aunque el contrato permitiría almacenar el
subtotal en S14. No hay saturación, acumulador, redondeo ni escalas.

No hay reloj, reset ni handshake. La estructura contiene cuatro operadores
de multiplicación y un árbol de sumas; no determina cuántos DSP o LUT usará
una herramienta de síntesis. El módulo usa construcciones sintetizables,
pero **todavía no se ha sintetizado**. No se promete una instrucción de un
ciclo, frecuencia, latencia física ni ahorro de energía. El `#1` del banco
de pruebas solo deja estabilizar la simulación funcional.

## Verificación reproducible

Desde la raíz: `make rtl-test`. Requiere Python 3 en Linux, Icarus/vvp,
Verilator con `--binary --timing`, make y un compilador C++ compatible.
No requiere placa, red ni paquetes Python externos.

El [runner](../scripts/verify_rtl.py) verifica primero los hashes de M1,
genera expectativas con su referencia congelada y las contrasta con extracción
por bytes/hexadecimal y aritmética factorizada escrita por separado.
El mismo [testbench](../tests/rtl/tb_xqdot4z.sv) se ejecuta en ambos simuladores.

| Grupo | Comparaciones por simulador |
|---|---:|
| Vectores ya fijados en M1 | 2068 |
| Las 65 536 ternas de un término, en ocho posiciones | 524 288 |
| Combinaciones de extremos en las cuatro vías, todo z y h | 8192 |
| 10 000 palabras aleatorias, ambas mitades | 20 000 |
| 1024 pares con la mitad no seleccionada invertida | 2048 |
| Transiciones individuales de los 69 bits de entrada | 138 |
| **Total** | **556 734** |

Semilla adicional: 20260909, distinta de la de M1. Los grupos pueden contener
entradas repetidas; el total cuenta comparaciones, no entradas únicas.
La exhaustividad corresponde a **un término**, no a las entradas completas
de 69 bits. Dos simuladores ejecutando el mismo banco no son dos verificaciones
independientes del contrato. No se ha realizado prueba formal ni cobertura
estructural; los estados X/Z de entrada quedan fuera del contrato.

Cada simulador debe detectar ocho controles negativos: resultado esperado
incorrecto, archivo vacío, registro truncado, h fuera de rango, cantidad
incorrecta de vectores, archivo inexistente, registro parcial sobrante y
columna adicional. Además, en Icarus se compilan
y rechazan cuatro mutaciones del RTL: activaciones sin signo, pesos U4
interpretados como S4, selector ignorado y extensión de salida con ceros.
Las mutaciones se guardan únicamente como evidencia y no se usan en el diseño.
Esto comprueba fallos concretos, no garantiza detectar cualquier error posible.

El lint de la unidad usa `verilator --lint-only --Wall` sin excepciones.
El banco verifica bits con `!==` y exige la cantidad exacta de comparaciones;
una compilación correcta o un archivo vacío no cuentan como aprobación.

## Evidencia y siguiente paso

Cada ejecución crea `rtl/results/<fecha-UTC>/`, sin reemplazar las anteriores.
Conserva fuentes identificadas por hash, versiones, comandos, logs, controles,
mutaciones y todos los vectores en `vectors.txt.gz` (gzip determinista).
Los ejecutables y archivos temporales de construcción se eliminan al terminar.
La evidencia revisada se fija en [RTL_STATE.json](../docs/RTL_STATE.json);
`make check` comprueba su integridad sin volver a simular.

Las cinco columnas hexadecimales descomprimidas son W, A, z, h y result.
El banco exige el formato exportado: 8/8/1/1/8 dígitos, espacios simples y
fin de línea LF (31 bytes por registro), sin comentarios ni líneas vacías.
El resumen conserva también el hash del texto descomprimido y los conteos.
Consultar [results/README.md](results/README.md) para el historial.

La integración inmediata se describe en [isa/SPEC.md](../isa/SPEC.md) y se
fija en [INTEGRATION_STATE.json](../docs/INTEGRATION_STATE.json). La bandera
`integrated_in_kuntur: false` de `RTL_STATE.json` describe la instantánea M2,
no el estado global posterior. M2 no verifica dependencias ni retiro del core.
El core corregido sigue en [../kuntur/rtl/](../kuntur/rtl/); su regresión se
ejecuta con `make core-test`. El snapshot histórico permanece intacto.
