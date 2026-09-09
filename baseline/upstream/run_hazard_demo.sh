#!/usr/bin/env bash
#
# Demostracion: los programas con dependencias pasan con la unidad de riesgos.
# Corre los testbenches forward / stall / flush sobre el procesador actual
# y muestra que forwarding, stall y flush resuelven los tres casos.
# Uso:  ./run_hazard_demo.sh

set -u
cd "$(dirname "$0")"

BUILD=build
mkdir -p "$BUILD"

CORE=(rtl/*.v)

# nombre | programa (.mem) | testbench (.v) | resultado esperado
TESTS=(
  "forward | riscvtest_forward.mem | testbench_forward.v | Mem[0] = 8"
  "stall   | riscvtest_stall.mem   | testbench_stall.v   | Mem[0] = 14"
  "flush   | riscvtest_flush.mem   | testbench_flush.v   | solo Mem[4] = 5"
)

PROGDIR=tests/programs
TBDIR=tests

BACKUP=""
if [ -f riscvtest.mem ]; then
  BACKUP="$BUILD/riscvtest.mem.bak"
  cp riscvtest.mem "$BACKUP"
fi
restore() { [ -n "$BACKUP" ] && cp "$BACKUP" riscvtest.mem; }
trap restore EXIT

RED=$'\e[31m'; GREEN=$'\e[32m'; DIM=$'\e[2m'; RST=$'\e[0m'
pass=0

printf '%s\n' "== Dependencias CON unidad de riesgos =================="

for row in "${TESTS[@]}"; do
  IFS='|' read -r name prog tb expected <<< "$row"
  name="${name// /}"; prog="${prog// /}"; tb="${tb// /}"
  expected="$(echo "$expected" | sed 's/^ *//; s/ *$//')"

  cp "$PROGDIR/$prog" riscvtest.mem
  iverilog -g2012 -o "$BUILD/sim_$name" "${CORE[@]}" "$TBDIR/$tb" 2>/dev/null
  out="$(vvp "$BUILD/sim_$name" 2>/dev/null | grep -v -i 'warning\|vcd')"

  if echo "$out" | grep -q -i 'succeeded'; then
    printf '  %-8s %sPASS%s  %s%s%s\n' "$name" "$GREEN" "$RST" "$DIM" "$expected" "$RST"
    pass=$((pass+1))
  else
    printf '  %-8s %sFAIL%s  %s(esperaba %s)%s\n' "$name" "$RED" "$RST" "$DIM" "$expected" "$RST"
  fi
done

printf '%s\n' "-------------------------------------------------------"
printf 'Total: %d PASS, %d FAIL\n' "$pass" "$((3-pass))"
