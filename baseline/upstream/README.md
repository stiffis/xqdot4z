# Procesador RISC-V pipelined (RV32I + extension C)

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
