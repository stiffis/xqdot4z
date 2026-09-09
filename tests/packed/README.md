# B3 — producto punto empacado sin corrección, aislado

Estado: aritmética aislada verificada, M3b parcial. La
[unidad xqdot4](../../rtl/packed/xqdot4.v) y su
[contrato v0.1](../../rtl/packed/SPEC.md) implementan P, no el resultado
corregido d. [PACKED_STATE.json](../../docs/PACKED_STATE.json) fija la evidencia.
Esta evidencia no cubre encoding ni integración. La etapa posterior tiene
[ISA propia](../../isa/packed/SPEC.md) y [pruebas en Kuntur](../packed_integration/README.md),
sin modificar esta unidad ni su batería. No hay resultados de rendimiento.

Desde la raíz: `make packed-test`. Se requieren Python, Icarus/vvp,
Verilator, make y C++; no se instala nada ni se necesita placa o red.
Los demás bancos y el core no se modificaron para esta unidad.

## Qué se verifica

Cada vector contiene `W A z h P d`: se comprueban P contra `xqdot4` y d
contra la unidad XQDot4Z congelada. Además, el banco comprueba la igualdad
`P - z*sum(A) = d`. Esta corrección dentro del banco **no es hardware de B3**
ni demuestra el costo de implementarla en el procesador.

Ejemplo: pesos [5,9,10,4] y activaciones [4,−3,2,1] dan P=17 y Sa=4.
Con z=8, la salida corregida es 17−8·4=−15. B3 entrega 17; la operación
fusionada entrega −15. Solo son alternativas equivalentes cuando se incluye
la corrección que le falta a B3.

| Grupo | Vectores por simulador |
|---|---:|
| Casos fijados en M1, con P añadido a la referencia original d | 2068 |
| 4096 pares U4×S8, cada uno en las ocho posiciones físicas de W | 32 768 |
| Extremos en las cuatro vías, todo z/h | 8192 |
| 10 000 palabras aleatorias, ambas mitades | 20 000 |
| Pares con la mitad no utilizada invertida | 2048 |
| Transiciones de cada uno de los 65 bits de entrada de B3 | 130 |
| 32 entradas, ambos h y los 16 z; P debe permanecer independiente de z | 1024 |
| Bloques utilizados en las pruebas matriz–vector | 1680 |
| **Total** | **67 910** |

Se usa la semilla 20260912. Las cuentas son verificaciones, no entradas
necesariamente únicas. La exhaustividad se limita a un producto U4×S8, no
al espacio completo de entradas de cuatro vías. Los dos simuladores usan
el mismo banco y expectativas; no son pruebas independientes del contrato.

El runner extrae pesos a partir de dígitos hexadecimales y activaciones con
`struct.unpack("4b", ...)`, calcula P y d y los contrasta con M1. Los 2068
casos iniciales mantienen W/A/z/h y d de M1; el formato tiene una columna
adicional P y no reemplaza ni modifica sus vectores originales. El rango P
es [−7680,7620]; el de d sigue siendo [−7680,7680].

## Reutilización de Sa entre filas

Se generan 24 fixtures de corrección: N∈{1,4,16}, G∈{8,32}, dos grupos
(K=2G), y cuatro políticas z: constante 0/8/15 o variable por fila/grupo.
Son dimensiones de verificación, **no una selección final de benchmarks**.
Cada fixture tiene un vector A compartido por sus filas, pesos por fila,
dos Sa y un resultado esperado por fila/grupo; se conservan todos en JSON.

El banco emite 1680 respuestas P/d del RTL con sus índices de vector. El
verificador vincula cada respuesta a sus tensores/mitad/z y reconstruye
336 salidas por fila/grupo, de dos formas: sumar P y restar z·Sa, o sumar
los d fusionados. Ambas deben coincidir con el cálculo directo sobre los
tensores. Hay 48 sumas Sa distintas por posición vector/grupo, compartidas
entre las filas; sus valores numéricos pueden coincidir accidentalmente.

En esta batería las acumulaciones, Sa y la corrección se realizan en Python.
**Estos fixtures no ejecutan un kernel matriz–vector en Kuntur**, ni miden cargas, instrucciones,
ciclos, recursos, frecuencia o energía. Verificar la identidad no resuelve
el suministro de zero-points dinámicos en la interfaz ISA de D.

## Sensibilidad a errores y trazabilidad

Cada simulador debe rechazar diez controles: P incorrecto, d incorrecto,
archivo vacío, vector truncado, resto parcial, columna extra, hexadecimal
inválido, h fuera de rango, cantidad incorrecta y archivo inexistente.
Se exige la causa esperada, no cualquier salida de error.

Cuatro mutaciones del RTL B3 se detectan en Icarus: pesos interpretados como
S4, activaciones unsigned, selector de mitad ignorado y salida extendida
con ceros. Compilan antes de fallar por discrepancia aritmética. Dos controles
adicionales del verificador de matrices detectan Sa de grupo incorrecta y
un bloque omitido; no cuentan como nuevas ejecuciones del RTL.

El lint de la unidad pasa con `-Wall`, sin excepciones. Cada ejecución
conserva fuentes copiadas, hashes, versiones, semilla, vectores, matrices y
logs sin filtrar. `make check` valida la evidencia fijada y reconstruye de
nuevo las salidas desde los logs, sin simular.

El primer intento, `20260909T035347597506Z`, falló en la compilación del
banco por cuatro avisos WIDTHEXPAND al sumar S8 en un destino S32. Se hizo
explícita la extensión de signo a 32 bits, sin silenciar los avisos. Se
conserva el intento fallido; el RTL B3 no cambió por esa corrección del banco.
Los nombres de ejecución usan UTC; la fecha local de trabajo es 2026-09-08.

La ejecución fijada `20260909T035450467910Z` y su repetición
`20260909T035610026868Z` pasaron con las mismas fuentes, herramientas,
referencias, conteos, controles, vectores y fixtures. Ambas evidencias se
comprueban con `make check`. La repetición demuestra reproducibilidad local,
no significancia estadística ni medición de rendimiento.

## Siguiente puerta

La integración posterior y cuatro pares de fixtures con corrección en CPU
se fijan en [PACKED_INTEGRATION_STATE.json](../../docs/PACKED_INTEGRATION_STATE.json).
Las banderas de no integración en PACKED_STATE describen esta etapa aislada,
no el estado global. Siguen pendientes kernels comparables y mediciones.
