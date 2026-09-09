# Kuntur — procesador RISC-V de investigación

Kuntur deriva del proyecto docente kirky-arqui y conserva su historial, pero **no afirma
conformidad completa RV32IC**. Los cambios del núcleo se realizan únicamente
aquí; el original permanece intacto. Desde 2026-09-09, esta carpeta forma parte
del repositorio raíz en `main`. El historial anterior de
`research/core-corrections` se conserva en un
[bundle recuperable](../docs/VERSION_CONTROL.md).

- [Correcciones, interfaces, evidencia y límites](docs/CORE_CORRECTIONS.md).
- [Pruebas reproducibles](verification/README.md): ejecutar `make verify`.
- [Procedencia del clon](UPSTREAM.json).

La carpeta activa es `stuff/xqdot4z/kuntur/`. Kuntur nombra al procesador;
XQDot4Z sigue siendo el nombre de la operación propuesta. Las menciones a
kirky-arqui en la procedencia y en documentos históricos no nombran este clon.

XQDot4Zi está integrada con punto cero inmediato, desactivada por defecto
(`ENABLE_XQDOT4Z=0`). La [interfaz experimental](../isa/SPEC.md) y su
[verificación de pipeline](../tests/integration/README.md) se mantienen en la
raíz de investigación. Con 1, el build debe incluir `../rtl/xqdot4z.v`.
MUL escalar está disponible con `ENABLE_MUL=1`, independiente y también
apagada por defecto: [cambios y límites](docs/SCALAR_MUL.md). No implementa
M ni Zmmul completos. XQDot4 (B3 sin corrección) se activa por separado con
`ENABLE_XQDOT4=1`, incluyendo `../rtl/packed/xqdot4.v` en el build:
[integración, pruebas y límites](docs/PACKED_INTEGRATION.md).
Las tres opciones están apagadas por defecto. Los documentos y programas
del curso se conservan; el texto siguiente describe el proyecto de origen,
y debe leerse junto con el registro de correcciones anterior.

## Descripción del proyecto docente original

Procesador RISC-V de 5 etapas (Fetch, Decode, Execute, Memory, Writeback) con
unidad de riesgos (forwarding, stall, flush), basado en Harris & Harris.
Proyecto 2 de Arquitectura de Computadoras.

## Estructura

```
rtl/         Modulos de diseno (Verilog sintetizable)
tests/       Testbenches (.v), programs/ (.mem) y dump.v (volcado de waveforms)
toolchain/   asm2mem.sh (ensambla .s -> .mem) y gen_wave.sh (genera .vcd)
waves/       Un subdir por test: <test>/<test>.gtkw (versionado) + .vcd (ignorado)
docs/        Informe LaTeX e imagenes
Makefile     Atajos de simulacion
run_tests.sh        Regresion completa (PASS/FAIL por testbench)
run_hazard_demo.sh  Demostracion de forwarding / stall / flush
```

`imem.v` carga el programa desde `riscvtest.mem` (en el directorio de
ejecucion); los runners copian ahi el programa de cada prueba. La fuente de
verdad de los programas esta en `tests/programs/*.mem`.

## Uso

```sh
make test            # regresion completa
make hazard          # demo de la unidad de riesgos
make demo-hazard     # mismo programa sin NOPs: falla sin hazard unit
make wave PROG=isa   # genera waves/isa/isa.vcd
make clean           # borra artefactos
```

## Waveforms

```sh
make wave PROG=forward          # -> waves/forward/forward.vcd
gtkwave waves/forward/forward.vcd
```

Cada test tiene su carpeta en `waves/<test>/`. El `.vcd` se genera con
`gen_wave.sh` (via el modulo reutilizable `tests/dump.v`) y esta ignorado por
git. El `.gtkw` (la vista de senales de GTKWave) se guarda a mano desde GTKWave
y si se versiona, junto a su `.vcd`.

## Generar programas

```sh
toolchain/asm2mem.sh programa.s          # RV32I
toolchain/asm2mem.sh programa.s rv32ic   # con instrucciones comprimidas
cp programa.mem riscvtest.mem
```

## Requisitos

`iverilog`, `gtkwave`, `python3` y `riscv64-linux-gnu-{as,ld,objcopy}`.
