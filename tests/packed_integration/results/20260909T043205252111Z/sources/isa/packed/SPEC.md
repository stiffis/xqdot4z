# XQDot4 — interfaz ISA B3 experimental v0.1

Esta instrucción privada integra la [unidad B3 v0.1](../../rtl/packed/SPEC.md)
sin cambiar su aritmética, la unidad D ni el encoding de XQDot4Zi.
`xqdot4 rd, rs1, rs2, h` entrega P, sin corrección ni acumulación implícita.
El nombre del módulo y del macro coincide; no implica estandarización.

## Semántica

W=X[rs1], A=X[rs2]; `X[rd] = sum(i=0..3) U4(W,i+4*h)*S8(A,i)`.
Salida exacta extendida a 32 bits; P∈[−7680,7620]. h∈{0,1} selecciona pesos
bajos/altos sin modificar A. No hay z, tercer puerto GPR, CSR ni estado oculto.
PC avanza 4 bytes. rd puede coincidir con fuentes; x0 se lee como cero y
descarta escritura sin suprimir el retiro. No hay saturación ni flags.

## Encoding y justificación

| Bits | Campo |
|---|---|
| 31:28 | 0000, reservados |
| 27 | h |
| 26:25 | 00, reservados |
| 24:20 | rs2, activaciones |
| 19:15 | rs1, pesos |
| 14:12 | funct3=000 |
| 11:7 | rd |
| 6:0 | 0101011 = 0x2b, custom-1 |

Reconocimiento: `(instr & 0xf600707f) == 0x0000002b`.
Solo hay dos combinaciones funct7/funct3 válidas: (0,0) y (4,0).
El [mapa RISC-V v20260120](https://docs.riscv.org/reference/isa/v20260120/unpriv/rv-32-64g.html)
reserva custom-0…3 para extensiones propias. Elegir custom-1 mantiene
intacta la política v0.1 de custom-0 para D, incluidos sus patrones rechazados.
No garantiza compatibilidad con extensiones privadas ajenas.
El selector conserva bit 27 y ambas instrucciones ocupan 32 bits.

El [macro GNU](xqdot4.inc) utiliza el [formato R de .insn](https://sourceware.org/binutils/docs/as/RISC_002dV_002dFormats.html);
no se modifica binutils ni se declara soporte de compilador. El
[encoder Python](xqdot4.py) valida tipos/rangos y el decoder todos los campos.
Fuentes oficiales consultadas el 2026-09-09 UTC. Los campos y la operación
concretos son decisiones locales, no una propuesta ratificada por RISC-V.

## Integración y configuraciones

`ENABLE_XQDOT4=0` por defecto, independiente de MUL y XQDot4Zi. Con 1, incluir
`rtl/packed/xqdot4.v` de la raíz junto con `kuntur/rtl/*.v`. Con 0 no se
instancia la unidad ni se requiere su archivo para los builds históricos.

El bit de operación y h viajan D→E con flush/reset. Se reutilizan las fuentes
reenviadas, E→M→W y los hazards normales. No hay espera dedicada en E; esto
no prueba timing físico. Un load anterior que produce una fuente requiere
el stall normal. Disabled/reservadas producen el diagnóstico existente,
sin retiro ni escritura joven. Un salto puede descartarlas antes de E.
El reset cancela el pipeline sin borrar GPR/RAM; no se implementan traps/CSR.

Tuplas de prueba (MUL,D,B3): las ocho combinaciones de 0/1. Para la comparación
causal prevista: B1=(0,0,0), B2=(1,0,0), B3=(1,0,1), D=(1,1,0).
(1,1,1) verifica convivencia, no es el diseño D del protocolo. No se cambian
memorias, banco de registros, reloj ni anchos de las unidades al alternar
estas configuraciones. No se presume igualdad de recursos o frecuencia.

## Corrección separada y frontera de esta etapa

Un uso válido de la misma instrucción es calcular Sa con W=0x11111111:
cada peso vale uno y el resultado es la suma de las cuatro activaciones.
Sa puede acumularse por grupo y reutilizarse entre filas; la corrección
`P - z*Sa` usa MUL y SUB fuera de la unidad. Esta opción debe permitirse
en B3 al comparar; no se obliga al baseline a extraer y sumar bytes escalares.

Se prueban pequeños programas que calculan Sa y corrigen dos filas dentro
de Kuntur, frente a D sobre los mismos tensores. Son fixtures de verificación:
incluyen preparación explícita de RAM, controlan z conocido al generar código
y no definen una frontera de medición ni una campaña de benchmarks.
No resuelven el costo de suministrar z dinámico a D. Los kernels, política
experimental final, conteos de rendimiento y síntesis siguen pendientes.
