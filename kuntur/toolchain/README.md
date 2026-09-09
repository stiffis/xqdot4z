# toolchain/

Utilidades para generar imagenes de memoria `.mem` a partir de codigo
ensamblador RISC-V. Las `.mem` son palabras de 32 bits en hex (una por linea)
que `imem.v` carga con `$readmemh`.

## asm2mem.sh

Ensambla un `.s` y lo empaqueta al formato `.mem`. Trocea el binario en
palabras de 32 bits little-endian, asi que sirve igual para RV32I puro y para
programas mixtos RV32I + RVC (las comprimidas de 16 bits quedan empaquetadas de
a dos por palabra, y una instruccion de 32 bits puede quedar partida entre dos
palabras: eso es lo que resuelve el fetch de ventana deslizante).

```sh
./asm2mem.sh programa.s          # RV32I (sin comprimir)
./asm2mem.sh programa.s rv32ic   # permite que el ensamblador comprima
```

Genera `programa.mem` junto al `.s`.

Para usar una imagen con los runners:

```sh
cp programa.mem ../riscvtest.mem    # imem.v lee riscvtest.mem del cwd
```

## examples/

`suma.s` con sus dos versiones (`suma_rv32i.mem`, `suma_rvc.mem`) como
demostracion de la comparativa de tamano que pide la rubrica.

Requiere: `riscv64-linux-gnu-{as,ld,objcopy}` y `python3`.
