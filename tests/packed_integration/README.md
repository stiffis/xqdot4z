# B3 — instrucción XQDot4 y corrección en Kuntur

M3b parcial. El [contrato ISA v0.1](../../isa/packed/SPEC.md) integra la
unidad B3 congelada sin modificarla. La
[evidencia fijada](../../docs/PACKED_INTEGRATION_STATE.json) es distinta
de la [prueba aislada](../packed/README.md): aquí la suma Sa, acumulación y
corrección de los fixtures se ejecutan con instrucciones en Kuntur.

## Ejecutar

Desde la raíz: `make packed-integration-test`. Se requieren Python 3 en
Linux, GNU binutils RISC-V, Icarus/vvp, Verilator, make y C++. No requiere
red ni FPGA. `make check` verifica las evidencias seleccionadas sin simular.

```asm
.include "xqdot4.inc"  # añadir isa/packed/ al include path de GNU as
xqdot4 x3, x1, x2, 0  # cuatro U4 bajos de x1 por cuatro S8 de x2
xqdot4 x4, x1, x2, 1  # cuatro U4 altos; las activaciones no cambian
```

Cada macro emite una instrucción, no una secuencia ni soporte de compilador.
Habilitar `ENABLE_XQDOT4=1` e incluir `rtl/packed/xqdot4.v` junto al core.

## Cobertura comprobada

| Nivel | Alcance |
|---|---|
| GNU frente al encoder/decoder | Las 32³ ternas de GPR en ambos h: 65 536 instrucciones |
| Decoder Python | Dos opcodes × 128 funct7 × 8 funct3: 2048 comprobaciones |
| Política RTL | Los dos opcodes custom × 128 funct7 × 8 funct3 × 32 distribuciones de GPR × ocho configuraciones: 524 288 comprobaciones en Icarus |
| Rechazo del software | Nueve entradas inválidas del encoder y dos inmediatos h inválidos del macro |
| Pipeline | 123 programas, cada uno en Icarus y Verilator |
| Campaña numérica | 516 pares W/A × ambos h = 1032 operaciones, repetidas en las cuatro configuraciones con B3 habilitada |
| Corrección en CPU | Cuatro pares de programas, ocho salidas por implementación/simulador |
| Sensibilidad | Tres mutaciones en Icarus: retirar forwarding de pesos, de activaciones o ignorar h |

Las ocho configuraciones son (MUL, XQDot4Zi, XQDot4)∈{0,1}³. El mismo
programa base debe producir las mismas trazas en todas; (1,1,1) solo prueba
convivencia. Los futuros comparadores causales usan B1=(0,0,0), B2=(1,0,0),
B3=(1,0,1), D=(1,1,0). Esto no completa sus kernels ni el protocolo.

Los tests dirigidos cubren forwarding de M/W y lectura normal para ambas
fuentes en cada configuración B3; load-use en una o ambas fuentes; cadenas
entre XQDot4, MUL y XQDot4Zi; ADD/SW/branches/JALR consumidores; alias y x0;
mezcla con C y cruce de palabra; descartes por salto; drenaje antes de un
diagnóstico; reset en E; h=0/1 con B3 apagada y nueve bits reservados.
También se exige que activar B3 no habilite accidentalmente MUL o D.

El banco y el intérprete se comparten con las baterías anteriores. Se comparan
todos los retiros, destinos/datos, stores, diagnóstico, 31 GPR finales y
operandos efectivos de las tres operaciones. Los stalls se exigen por caso.
La expectativa B3 extrae bytes/nibbles directamente de los binarios y no
usa el encoder para reconocer la instrucción. El intérprete es un subconjunto
acotado, no Spike/Sail ni un ISS completo. Ambos simuladores usan el mismo
banco y expectativas; no constituyen oráculos independientes del contrato.

## Fixtures pareados: misma salida, corrección en lugares distintos

Semilla 20260913. Se conservan los tensores en `matrix_fixtures.json`.
N=2, K=G=8, un vector de activaciones compartido entre dos filas; sin escalas.
El primer caso es manual y los otros tres se generan determinísticamente.

| Caso | z de las dos filas | Sa | Salidas INT32 |
|---|---|---:|---|
| matrix_0 | 0, 0 | 4 | 1928, −53 |
| matrix_1 | 8, 8 | 33 | −1815, −231 |
| matrix_2 | 15, 15 | 196 | −164, −1461 |
| matrix_3 | 3, 12 | −55 | −879, −520 |

B3 calcula Sa una sola vez con dos XQDot4 usando W=0x11111111. Luego
calcula dos P por fila, los acumula y resta z·Sa con MUL/SUB. Cada programa
B3 ejecuta seis XQDot4 y dos MUL; D ejecuta cuatro XQDot4Zi y acumula.
Se comprueban seis y cuatro stalls load-use respectivamente. Esas cuentas
describen este código dirigido, con preparación de RAM incluida en la traza;
no definen rendimiento ni una optimización final (incluso z=0 conserva MUL).
La reutilización se comprueba en el resultado de x11 y los operandos trazados.

Los z son conocidos al generar el programa: no es una prueba ZR. La IMEM
de prueba es 32 KiB y la DMEM 256 B; no cambian los tamaños por defecto.
Reset cancela instrucciones en vuelo pero no borra RAM/GPR. El caso de
reset usa dos NOP anteriores explícitos y reinicia en EBREAK; se excluyen
esos retiros cancelados de la expectativa, como en las otras baterías.

## Evidencia y límites

Cada ejecución conserva comandos, versiones, semilla, fuentes copiadas,
SHA-256, tensores, ensamblados, ELF, binarios, memorias, expectativas y logs.
Los mutantes deben compilar y terminar normalmente, fallando por discrepancia
de valores; no se acepta un error de herramienta como detección.
Lint del core pasa en las ocho configuraciones con solo las exclusiones
heredadas VARHIDDEN y UNUSEDSIGNAL. No se silencia Wno-fatal.

Se fijan dos ejecuciones: `make check` valida ambas, reproduce el oráculo
desde sus binarios, vuelve a contrastar los logs y verifica la igualdad de
621 artefactos de entrada/referencia. Repetir demuestra reproducibilidad
local, no añade significancia estadística. M1/M2 y la evidencia aislada B3
permanecen congeladas; las baterías base/M3a/MUL se repiten tras la integración.
Las ejecuciones seleccionadas son `20260909T042409017085Z` y
`20260909T043205252111Z`; ambas completaron también las tres mutaciones.

No hay prueba formal, conformidad RISC-V completa, síntesis ni medida de
ciclos del kernel, frecuencia, recursos, energía o aceleración. Los próximos
kernels deben incorporar estas operaciones bajo condiciones comparables.
