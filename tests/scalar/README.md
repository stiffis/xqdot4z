# MUL escalar — verificación de la base común

M3b parcial. El [contrato](../../isa/scalar/SPEC.md) describe una instrucción
MUL estándar y opcional, no M ni Zmmul completos. La evidencia seleccionada
se identifica en [SCALAR_STATE.json](../../docs/SCALAR_STATE.json).
La [documentación del cambio](../../kuntur/docs/SCALAR_MUL.md) separa este
paso de las correcciones previas y de XQDot4Zi.
Esta batería conserva `ENABLE_XQDOT4=0`; la convivencia con B3 se verifica
en [su propia batería](../packed_integration/README.md).

Desde la raíz: `make scalar-test`. Requiere las mismas herramientas locales
que M3a: Python, GNU binutils RISC-V, Icarus/vvp, Verilator, make y C++.
El runner no instala herramientas ni necesita FPGA o red. Cada ejecución
crea su propia carpeta en `results/`; no selecciona automáticamente un PASS.

## Batería

| Nivel | Comprobación |
|---|---|
| Aritmética aislada | 65 536 pares S8 extendidos a 32 bits; 144 pares de borde; 1024 pares de potencias de dos; 20 000 pares aleatorios = 86 704 por simulador |
| Lectura y detección de fallos | Ocho controles negativos por simulador: referencia incorrecta, vacío, truncado, columna extra, hex inválido, cuenta incorrecta, resto parcial y archivo ausente |
| Sensibilidad aritmética | Dos mutaciones en Icarus: sumar en lugar de multiplicar y truncar ambas fuentes a 16 bits |
| Encoding GNU | Las 32³ = 32 768 ternas de GPR, contra los campos binarios estándar |
| Política OP | 128 funct7 × 8 funct3 × 32 distribuciones de registros × 4 configuraciones = 131 072 comprobaciones en Icarus |
| Pipeline | 49 programas, cada uno en Icarus y Verilator; incluye las cuatro combinaciones de MUL/XQDot4Zi |
| Campaña numérica integrada | 144 pares de borde + 512 aleatorios = 656 MUL, repetidas con XQDot4Zi apagada y encendida |
| Sensibilidad del pipeline | Dos mutaciones en Icarus: quitar forwarding a una u otra fuente de MUL |

Semilla 20260911, fijada antes de ejecutar. Solo el dominio S8 indicado es
exhaustivo; no lo son los 2⁶⁴ pares de operandos completos. Las potencias de
dos comprueban bits altos y truncamiento del producto. El oráculo unitario
usa producto Python unsigned módulo 2³²; el intérprete de instrucciones usa
producto signed de enteros sin ancho fijo y normaliza al retirar.

## Pipeline e independencia de configuraciones

Se ejercitan lectura de GPR y forwarding M/W por cada fuente; MUL→MUL,
ADD, SW, branch y JALR; cargas a una o ambas fuentes; alias de registros y x0;
saltos tomados y no tomados; instrucciones descartadas; mezcla con C a
dirección PC mod 4=2; drenaje de una MUL anterior a un fallo y reset en E.
Una secuencia adicional intercala MUL→XQDot4Zi y XQDot4Zi→MUL con cargas.
Los siete miembros de M no implementados se rechazan con MUL activada,
y MUL se rechaza cuando está apagada.

Las cuatro configuraciones usan el mismo RTL, capacidades de memoria y
convenciones de reset, sin duplicar cores. El programa base es idéntico y
debe producir la misma secuencia en las cuatro. La configuración de prueba
con ambas opciones no es todavía el comparador D completo del protocolo.

Se comparan **todos** los retiros (PC, destino y dato), stores (dirección y
valor), causa/PC del diagnóstico, 31 GPR finales y operandos de cada MUL
y XQDot4Zi. Los stalls se exigen por caso. Los retiros de inicialización
forman parte de la verificación, no de una medición de rendimiento.

Se reutiliza el intérprete acotado de M3a, ampliado con `mul_enabled=False`
por defecto; no es Spike/Sail ni un ISS RISC-V completo. Los diagnósticos
de Kuntur no son traps arquitectónicos. Reset no borra GPR/RAM; el caso de
cancelación usa NOPs explícitos para las otras instrucciones afectadas.

## Trazabilidad y límites

Se conservan comandos, versiones, semilla, fuentes copiadas, vectores,
ensamblador, ELF, binario, imagen de memoria, referencia por programa y logs
sin filtrar, con inventarios SHA-256. La batería falla si cambian sus fuentes
mientras corre. Los mutantes deben fallar por el error esperado, no por un
problema de compilación. El lint de la unidad no usa excepciones; el del core
conserva solo las dos exclusiones heredadas de M3a, VARHIDDEN y UNUSEDSIGNAL.

`make check` verifica hashes y vuelve a contrastar los logs escalares fijados
con sus referencias, sin repetir simulación. Tras editar fuentes se ejecutan
de nuevo las baterías afectadas y se revisan los nuevos reportes antes de
cambiar las referencias en `docs/`. M1/M2 no se reescriben por añadir MUL.

Las ejecuciones anteriores `20260908T230834621243Z` y
`20260908T231332984555Z` se conservan. Tras integrar B3, la evidencia fijada
`20260909T041317383641Z` y su repetición `20260909T042410277125Z`
pasaron con las mismas fuentes, herramientas,
resultados y controles. Se compararon los hashes de 249 artefactos generados
(ensamblador, ELF, binarios, imágenes, expectativas y vectores): coinciden.
`make check` verifica ambas evidencias y esa correspondencia. La repetición
comprueba reproducibilidad, no añade muestras estadísticas de rendimiento.

Esta evidencia no demuestra timing, recursos, energía, rendimiento ni
conformidad ISA completa. B3 ya tiene integración verificada por separado;
quedan pendientes kernels comparables,
fronteras de medición y el costo de metadatos dinámicos.
