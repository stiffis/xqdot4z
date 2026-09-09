# MUL escalar opcional — M3b parcial

Este cambio pertenece a la base común de la investigación, no a las
correcciones C01–C10 ni a una supuesta mejora de rendimiento de XQDot4Z.
Solo se modifica Kuntur. El original y `baseline/upstream/` se preservan.

## Registro de cambios

| Archivos | Cambio | Por qué |
|---|---|---|
| `rtl/scalar_mul.v` | Producto combinacional con salida baja de 32 bits | Semántica de MUL, sin implementar productos altos ni división |
| `rtl/top.v`, `rtl/riscvpipe.v` | Propagar `ENABLE_MUL`, por defecto 0 | Comparar el mismo core, con y sin multiplicación, sin bifurcar el RTL |
| `rtl/instruction_policy.v` | Admitir solo opcode OP, funct7=1, funct3=0 al habilitar MUL | Evitar alias con ADD y rechazar el resto de M |
| `rtl/datapath.v` | Bit MulD→MulE, flush/reset, fuentes reenviadas y selector de resultado | Reutilizar hazards, M/W y writeback sin una espera adicional en E |
| `tests/integration/oracle.py`, en la raíz | Opción MUL apagada por defecto, producto entero signed y traza de fuentes | Referencia funcional acotada que decodifica los bytes independientemente del RTL |
| `tests/integration/tb_integration.sv`, en la raíz | Parámetro MUL, traza MEXEC y reset durante MUL o QDot | Comprobar convivencia y cancelación; preservar el modo M3a anterior |
| `tests/scalar/`, `scripts/verify_scalar.py`, en la raíz | Aritmética, encoding, decode, pipeline y controles de sensibilidad | Evidencia reproducible en ambos simuladores |

No cambian `controller.v`, `maindec.v`, la ALU, el banco de registros,
memorias ni la unidad de riesgos en este paso. El control OP existente
selecciona writeback normal; el bit MulE sustituye únicamente el resultado
que entra a M. La ALU sigue produciendo sus resultados de control habituales.
Las fuentes del multiplicador son `SrcAE` y `WriteDataE`, después del forwarding.
Suprimir una de esas conexiones es una de las mutaciones que deben fallar.

## Uso y límites

Desde la raíz de investigación: `make scalar-test`, `make core-test`,
`make integration-test`, y después revisión deliberada de evidencias.
`make check` comprueba las referencias fijadas y los logs; no simula de nuevo.
Con `ENABLE_MUL=1`, incluir `rtl/scalar_mul.v` del clon (los builds que toman
`kuntur/rtl/*.v` ya lo incluyen). XQDot4Zi se habilita independientemente y
sigue requiriendo la unidad de la raíz `rtl/xqdot4z.v`.

El [contrato](../../isa/scalar/SPEC.md) y la [guía de pruebas](../../tests/scalar/README.md)
delimitan el soporte. MUL sola no es M ni Zmmul, y no completa RV32IC.
No hay prueba de frecuencia, DSP/LUT, energía, FPGA ni aceleración. El período
de reloj del testbench no se interpreta como timing sintetizado.

## Conservación de evidencia

[CORE_STATE.json](../../docs/CORE_STATE.json) identifica la regresión actual con
las tres opciones en 0, tras la posterior [integración B3](PACKED_INTEGRATION.md).
[INTEGRATION_STATE.json](../../docs/INTEGRATION_STATE.json) identifica M3a con
MUL/B3=0. [SCALAR_STATE.json](../../docs/SCALAR_STATE.json) identifica la
batería MUL sola y con XQDot4Zi, repetida sobre las nuevas fuentes con B3=0.

Las fuentes previas a este cambio permanecen copiadas y hashadas dentro de la
evidencia M3a `tests/integration/results/20260908T181809095468Z/sources/`.
No se reescriben sus logs ni se los presenta como prueba del RTL nuevo.
M1 y M2 conservan exactamente sus fuentes y evidencias anteriores.

El primer intento de la batería escalar encontró un aviso WIDTHTRUNC en
el testbench: se usaba `!fd` para el descriptor entero de archivo. Se cambió
a `fd==0`, sin suprimir el aviso. El intento fallido se conserva en
`tests/scalar/results/20260908T230803158106Z/`.
