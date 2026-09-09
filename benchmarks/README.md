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

Los histogramas equilibrados se refieren a las fases ZS completas, no a cada
programa por separado ni a una distribución de una red real. Un programa
puede mezclar estratos: no se reparten sus ciclos entre ellos por frecuencia.
El arranque K=G tiene un solo grupo; la fórmula permite variación entre grupos,
pero esa sensibilidad exige una ampliación de campaña registrada antes de medir.

```sh
python3 scripts/check_campaign.py
python3 -m unittest discover -s tests/benchmarks -p 'test_*.py' -v
make check
```

El checker enumera 2280 casos planificados (360 ZC y 1920 ZS), comprueba
30 histogramas por dimensión/semilla y detecta cambios que rompen la cobertura
o las políticas básicas. Los tests incluyen quince mutaciones negativas.
Estas comprobaciones **no son ejecuciones RTL, mediciones ni una validación
automática de todas las afirmaciones del protocolo**.

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
