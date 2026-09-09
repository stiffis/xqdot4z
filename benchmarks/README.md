# Campaña inicial y kernels futuros (M4)

La única fuente normativa es [EXPERIMENT_PROTOCOL.md](../docs/EXPERIMENT_PROTOCOL.md).
No se crea otro contrato que reformule sus métricas, frontera o política de
codegen. La futura nota de instrumentación documentará su realización en
señales/flancos y pruebas del testbench, no otro método experimental.

[campaign.json](campaign.json) es un manifiesto de diseño, no ejecutable.
Fija la selección inicial de dimensiones, semillas, perfiles y distribución
de z, estratos y compromiso de conservar todos los casos. La regla ZS es
`(phase + row_stride*r + group_stride*g) % modulus`; todos sus parámetros
están en el manifiesto. Los tensores A/W se emparejarán también entre perfiles.
La revisión 0.2 selecciona la aritmética de B1 y registra su congelación
obligatoria antes del piloto, sin afirmar que exista ya su ensamblado.

Los histogramas equilibrados se refieren a las fases ZS completas, no a cada
programa por separado ni a una distribución de una red real. Un programa
puede mezclar estratos: no se reparten sus ciclos entre ellos por frecuencia.
El arranque K=G tiene un solo grupo; la fórmula permite variación entre grupos,
pero esa sensibilidad exige una ampliación de campaña registrada antes de medir.
Con g=0, `group_stride` no afecta a esta rejilla, como declara explícitamente
el manifiesto; probar la fórmula con dos grupos no equivale a ejecutar esa carga.

Las diez semillas cubren entradas para corrección, no son diez repeticiones
estadísticas de rendimiento. Se conservan las 2280 configuraciones y sus
métricas. El piloto prefijado compara las dos primeras semillas por variante
con N=4, K=G=32, los tres controles ZC y ZS fase 0: 32 casos que ya pertenecen
a la rejilla, no casos adicionales. Comparará código/control/direcciones,
retiros y stalls además de ciclos; dos totales iguales no prueban invariancia.
Sigue bloqueado hasta verificar kernels e instrumentación. Ejecutar toda la
rejilla en ambos simuladores supondría 4560 ejecuciones antes de reintentos;
reutilizar el mismo código entre semillas ahorra generación, no esas ejecuciones.

```sh
python3 scripts/check_campaign.py
make benchmark-plan-test
make check
```

El checker enumera 2280 casos planificados (360 ZC y 1920 ZS), comprueba
30 histogramas por dimensión/semilla y detecta cambios que rompen la cobertura
o las políticas básicas. Los tests del manifiesto incluyen 32 mutaciones negativas.
Estas comprobaciones **no son ejecuciones RTL, mediciones ni una validación
automática de todas las afirmaciones del protocolo**.

[b1_arithmetic.py](b1_arithmetic.py) modela en el host una sola regla de
multiplicación por máscaras y desplazamientos, con aritmética RV32. La norma
está en la sección B1 del protocolo, no en un contrato paralelo. Se contrasta
con multiplicación entera independiente sobre las 65 536 ternas U4/U4/S8,
incluidos -128, productos negativos y los anchos especiales de z=0 y z=8.
Las nueve pruebas del directorio incluyen esos casos y el manifiesto;
`make check` también las ejecuta. No son kernels ni mediciones de ciclos.

Los campos de optimización aún no seleccionados son `null`. Junto con memoria,
generación de tensores, kernels e instrumentación, bloquean la ejecución;
no equivalen a libertad para escogerlos después de ver resultados.
La política debe cerrarse antes de escribir los kernels de rendimiento.
En particular, la reutilización de z·Sa entre filas con z iguales requiere
una decisión explícita; no se fuerza MUL/Sa cuando z=0 ni se asume que los
otros códigos impiden reducir fuerza.
Conocer A/W para generar la referencia no autoriza a precomputar Sa o salidas
en el código; esas operaciones deben ejecutarse dentro de la medición.

Conservar fuentes, desensamblados, imágenes, hashes, tensores y comandos,
incluidos fallos. Toda ampliación cambia la versión del manifiesto antes
de ejecutar sus nuevos casos. No hay todavía kernels ni mediciones M4.
