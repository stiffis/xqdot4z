# Referencia numérica de XQDot4Z — M1

El contrato v0.1 está en [SPEC.md](SPEC.md) y la implementación en
[xqdot4z.py](xqdot4z.py). Solo requiere Python 3 y su biblioteca estándar.
No es un simulador RISC-V ni un modelo de ciclos.

## Probar y reproducir

Desde la raíz de investigación:

```sh
make model-test
make check
```

El primer comando ejecuta las pruebas y crea una ejecución nueva en
`model/results/<fecha-UTC>/`. El segundo verifica la evidencia fijada en
[MODEL_STATE.json](../docs/MODEL_STATE.json), sin volver a ejecutar los tests.
Tras un cambio numérico hay que revisar y fijar deliberadamente una nueva evidencia.

Ejemplo desde esa misma raíz:

```python
from model.xqdot4z import qdot4z, qdot4z_bits

d = qdot4z(0x00004A95, 0x0102FD04, zero_point=8, half=0)
bits = qdot4z_bits(0x00004A95, 0x0102FD04, zero_point=8, half=0)
print(d)                  # -15
print(f"0x{bits:08X}")     # 0xFFFFFFF1
```

## Qué se entrega

- Funciones de packing/desempaquetado con índices bajos en bits bajos.
- Suma directa y corrección factorizada escritas por separado.
- Selección lo/hi de pesos, activaciones S8 y resultado exacto con signo.
- Conversión explícita a los bits de salida; entradas inválidas rechazadas.
- Casos documentados, controles exhaustivos de un término y pruebas aleatorias.
- Vectores reutilizados en el testbench RTL de M2.

La guía externa `stuff/ai_review/verify_examples.py` sirvió como punto de
partida para los ejemplos y se conserva intacta. Es material complementario
fuera de este repositorio, no una dependencia de sus pruebas. La API actual es
más estricta: exige ocho pesos al empacar y half entero 0/1, no bool.

La unidad aislada ya se verifica por separado en [M2](../rtl/README.md).
La interfaz inmediata y la integración opcional se verifican en
[M3a](../tests/integration/README.md). El suministro de z leído en ejecución
sigue pendiente.
Los resultados de estas pruebas no son mediciones de aceleración.

El contrato, la referencia y la evidencia M1 se conservan sin cambios. Las
frases sobre RTL futuro en esos artefactos y `rtl_implemented: false` en
`MODEL_STATE.json` describen el hito M1, no el estado global posterior.
El estado del hardware se registra en [RTL_STATE.json](../docs/RTL_STATE.json).

Se comprobó reproducibilidad: las ejecuciones `20260908T130619554724Z` y
`20260908T131153442155Z` pasaron con las mismas fuentes y produjeron los
mismos `vectors.txt` y `vectors.jsonl`, comparados byte a byte.
Los tiempos del runner y los timestamps pueden diferir; no son ciclos del core.
