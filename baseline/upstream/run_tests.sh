#!/usr/bin/env bash
#
# Runner de regresion del pipeline RISC-V (week13).
# Compila y corre todos los testbenches con iverilog y reporta PASS/FAIL por cada uno.
# Uso:  ./run_tests.sh
# Exit: 0 si todos pasan, 1 si alguno falla.

set -u
cd "$(dirname "$0")"

BUILD=build
mkdir -p "$BUILD"

CORE=(rtl/*.v)

# Pruebas (programas en tests/programs/, testbenches en tests/).
#   nombre | programa (.mem) | testbench (.v)
PROGDIR=tests/programs
TBDIR=tests
TESTS=(
  "base   | riscvtest_base.mem    | testbench_base.v"
  "ctrl   | riscvtest_ctrl.mem    | testbench_ctrl.v"
  "xor    | riscvtest_xor.mem     | testbench_xor.v"
  "lui    | riscvtest_lui.mem     | testbench_lui.v"
  "shift  | riscvtest_shift.mem   | testbench_shift.v"
  "branch | riscvtest_branch3.mem | testbench_branch3.v"
  "jalr   | riscvtest_jalr.mem    | testbench_jalr.v"
  "deps   | riscvtest_deps.mem    | testbench_deps.v"
  "isa    | riscvtest_isa.mem     | testbench_isa.v"
  "forward| riscvtest_forward.mem | testbench_forward.v"
  "stall  | riscvtest_stall.mem   | testbench_stall.v"
  "flush  | riscvtest_flush.mem   | testbench_flush.v"
  "caddi  | riscvtest_caddi.mem   | testbench_caddi.v"
  "cir    | riscvtest_cir.mem     | testbench_cir.v"
  "ca     | riscvtest_ca.mem      | testbench_ca.v"
  "cb     | riscvtest_cb.mem      | testbench_cb.v"
  "mul10  | riscvtest_mul10.mem   | testbench_mul10.v"
  "clsw   | riscvtest_clsw.mem    | testbench_clsw.v"
  "clspsp | riscvtest_clspsp.mem  | testbench_clspsp.v"
  "cbz    | riscvtest_cbz.mem     | testbench_cbz.v"
  "cj     | riscvtest_cj.mem      | testbench_cj.v"
  "cjr    | riscvtest_cjr.mem     | testbench_cjr.v"
  "sumloop| riscvtest_sumloop.mem | testbench_sumloop.v"
  "gcd    | riscvtest_gcd.mem     | testbench_gcd.v"
  "bsearch| riscvtest_bsearch.mem | testbench_bsearch.v"
  "bsearch_rv32i| riscvtest_bsearch_rv32i.mem | testbench_bsearch_rv32i.v"
)

# imem.v lee "riscvtest.mem" del directorio actual: lo respaldamos y restauramos.
BACKUP=""
if [ -f riscvtest.mem ]; then
  BACKUP="$BUILD/riscvtest.mem.bak"
  cp riscvtest.mem "$BACKUP"
fi
restore() { [ -n "$BACKUP" ] && cp "$BACKUP" riscvtest.mem; }
trap restore EXIT

pass=0; fail=0
GREEN=$'\e[32m'; RED=$'\e[31m'; DIM=$'\e[2m'; RST=$'\e[0m'

printf '%s\n' "── Regresion pipeline RISC-V ─────────────────────────"

for row in "${TESTS[@]}"; do
  IFS='|' read -r name prog tb <<< "$row"
  name="${name// /}"; prog="${prog// /}"; tb="${tb// /}"

  cp "$PROGDIR/$prog" riscvtest.mem
  sim="$BUILD/sim_$name"
  if ! iverilog -g2012 -o "$sim" "${CORE[@]}" "$TBDIR/$tb" 2> "$BUILD/$name.compile.log"; then
    printf '  %-7s %sFAIL%s  %s(error de compilacion, ver %s)%s\n' \
      "$name" "$RED" "$RST" "$DIM" "$BUILD/$name.compile.log" "$RST"
    fail=$((fail+1)); continue
  fi

  out="$(vvp "$sim" 2>/dev/null | grep -v -i 'warning\|vcd')"

  if echo "$out" | grep -q -i -E 'fail|unexpected|timed out|mismatch' \
     || ! echo "$out" | grep -q -i -E 'succe|ok'; then
    printf '  %-7s %sFAIL%s\n' "$name" "$RED" "$RST"
    echo "$out" | sed 's/^/             /'
    fail=$((fail+1))
  else
    last="$(echo "$out" | grep -i 'succe\|ok' | tail -1)"
    printf '  %-7s %sPASS%s  %s%s%s\n' "$name" "$GREEN" "$RST" "$DIM" "$last" "$RST"
    pass=$((pass+1))
  fi
done

printf '%s\n' "──────────────────────────────────────────────────────"
printf 'Total: %d PASS, %d FAIL\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
