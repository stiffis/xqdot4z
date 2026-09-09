#!/usr/bin/env bash
set -euo pipefail

AS=riscv64-linux-gnu-as
LD=riscv64-linux-gnu-ld
OC=riscv64-linux-gnu-objcopy

src="${1:?uso: asm2mem.sh archivo.s [march]}"
march="${2:-rv32i}"
base="${src%.s}"
out="$base.mem"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

"$AS" -march="$march" -mabi=ilp32 -o "$tmp/a.o" "$src"
"$LD" -m elf32lriscv -Ttext=0x0 -e _start -o "$tmp/a.elf" "$tmp/a.o" 2>/dev/null \
  || "$LD" -m elf32lriscv -Ttext=0x0 -o "$tmp/a.elf" "$tmp/a.o"
"$OC" -O binary "$tmp/a.elf" "$tmp/a.bin"

python3 - "$tmp/a.bin" "$out" <<'PY'
import sys
data = open(sys.argv[1], "rb").read()
if len(data) % 4:
    data += b"\x00" * (4 - len(data) % 4)
with open(sys.argv[2], "w") as f:
    for i in range(0, len(data), 4):
        f.write(f"{int.from_bytes(data[i:i+4], 'little'):08x}\n")
print(f"-> {sys.argv[2]}: {len(data)} bytes, {len(data)//4} palabras")
PY
