#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

name="${1:?uso: gen_wave.sh <test>   (ej: forward, stall, flush, isa)}"
prog="tests/programs/riscvtest_${name}.mem"
tb="tests/testbench_${name}.v"

[ -f "$prog" ] || { echo "no existe $prog"; exit 1; }
[ -f "$tb" ]   || { echo "no existe $tb"; exit 1; }

mkdir -p build "waves/${name}"

if [ -f riscvtest.mem ]; then cp riscvtest.mem build/riscvtest.mem.bak; fi
trap '[ -f build/riscvtest.mem.bak ] && cp build/riscvtest.mem.bak riscvtest.mem' EXIT
cp "$prog" riscvtest.mem

iverilog -g2012 -o "build/sim_wave_${name}" rtl/*.v tests/dump.v "$tb"
vvp "build/sim_wave_${name}" 2>/dev/null | grep -v -i 'warning\|vcd' || true
mv -f wave.vcd "waves/${name}/${name}.vcd"

echo "-> waves/${name}/${name}.vcd"
