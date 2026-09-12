# XQDot4Z — productos punto cuantizados en RV32

Estado: **M0 a M5 realizados**. Las cuatro variantes (B1, B2, B3 y D) tienen
kernels verificados bajo una sola política de generación de código congelada, y
la campaña registrada corrió **2280 de 2280 casos en `pass`** en dos simuladores
sin ninguno ausente. Los resultados están en el artículo ES/EN con sus costos y
sus límites. No se ha calculado ningún speedup agregado ni se ha reducido la
rejilla; agregar regímenes sigue prohibido por el manifiesto.

Pendientes: **M6**, síntesis y evidencia física —área, frecuencia y energía—;
el régimen **ZR** con puntos cero leídos en ejecución, que esta interfaz no
puede expresar; y los ejes **K y G** de RQ3, con su costo medido y su plan en
[docs/EXTENSION_PLAN.md](docs/EXTENSION_PLAN.md).

El proyecto docente original se conserva intacto fuera de este repositorio; su
exportación fijada por hash está en `baseline/upstream/`.

## Por dónde leer

1. [Artículo en español](paper/main_es.pdf) · [fuente](paper/main_es.tex).
2. [Artículo en inglés](paper/main_en.pdf) · [fuente](paper/main_en.tex).
3. [Por qué este formato IEEE](docs/IEEE_FORMAT.md) y [estructura editorial](docs/PAPER_PLAN.md).
4. [Kuntur: cambios del procesador y límites](kuntur/docs/CORE_CORRECTIONS.md).
5. [Verificación reproducible](kuntur/verification/README.md) y [evidencia fijada](docs/CORE_STATE.json).
6. [Contrato numérico de XQDot4Z](model/SPEC.md), [referencia Python](model/xqdot4z.py)
   y [guía para ejecutar sus pruebas](model/README.md).
7. [Unidad Verilog y batería M2](rtl/README.md), con [evidencia fijada](docs/RTL_STATE.json).
8. [Interfaz ISA y decisiones](isa/SPEC.md), [pruebas M3a](tests/integration/README.md)
   y [evidencia de integración](docs/INTEGRATION_STATE.json).
9. [MUL común: cambios del core](kuntur/docs/SCALAR_MUL.md),
   [pruebas escalares](tests/scalar/README.md) y [evidencia](docs/SCALAR_STATE.json).
10. [Contrato aritmético B3](rtl/packed/SPEC.md),
    [pruebas de B3 aislado](tests/packed/README.md) y [evidencia](docs/PACKED_STATE.json).
11. [ISA de B3](isa/packed/SPEC.md), [cambios de integración](kuntur/docs/PACKED_INTEGRATION.md),
    [pruebas en el procesador](tests/packed_integration/README.md) y
    [evidencia](docs/PACKED_INTEGRATION_STATE.json).
12. [Manifiesto inicial y comprobaciones](benchmarks/README.md), con el
    [protocolo experimental único](docs/EXPERIMENT_PROTOCOL.md).

Los dos artículos son versiones equivalentes del mismo borrador. Usan
IEEEtran en modo conferencia: dos columnas, fondo blanco y diagrama TikZ
en blanco y negro, sin temas visuales. La convocatoria sigue abierta. Reportan la
campaña registrada con sus costos y sus límites; la evidencia física —área,
frecuencia y energía— sigue pendiente y no se anticipa.
El informe extenso anterior se conserva en `docs/archive/paper-v0.1/`.

## Qué investigamos

¿Bajo qué condiciones fusionar la corrección del zero-point en cuatro productos
U4×S8 reduce el costo de ejecutar productos punto y matriz–vector, frente a
multiplicación escalar y producto punto empacado con corrección factorizada,
considerando reutilización de activaciones y suministro del zero-point?

Primero exactitud y ciclos RTL, sin placa. Recursos, tiempo físico, energía
y calidad de una red completa requerirán otras evidencias. La primera interfaz
lleva z y h como inmediatos, con dos GPR fuente y sin estado oculto. No resuelve
el suministro de zero-points leídos en ejecución ni es una extensión estándar.

## Cómo usaremos tu procesador

- `baseline/upstream/`: exportación histórica de 143 archivos, con commit y
  manifiesto SHA-256. Solo para procedencia y reproducción de defectos.
- `kuntur/`: Kuntur, core de investigación derivado de kirky-arqui,
  ahora versionado como carpeta normal del repositorio principal.
  Su historial Git anterior está preservado en un bundle recuperable.
  Aquí están las correcciones, las pruebas y sus logs. No se hizo push.
- Las futuras variantes compartirán las correcciones: no se atribuirán a la
  extensión mejoras que provienen de arreglar bugs del procesador.
- [CORE_PRE_M3.json](docs/CORE_PRE_M3.json) identifica una copia archivada de
  las entradas verificadas del core corregido antes de integrar la operación.
  No es otro core activo ni reemplaza el snapshot del proyecto original.

La regresión corregida pasó 26 programas históricos, 28 483 vectores de
descompresión, 10 036 comparaciones signed, pruebas de política/hazards,
memoria, registros, cuatro programas de integración y lint.
Esto **no certifica RV32IC completo**: se delimita y rechaza lo no implementado.
MUL está disponible con `ENABLE_MUL=1`, apagada por defecto; no es M ni
Zmmul completos. No hay protocolo multiciclo. Las memorias siguen siendo
combinacionales, con 256 B cada una por defecto y capacidad parametrizable.

## Organización

```text
xqdot4z/
├── baseline/       # exportación intacta, identidad y hashes
├── audit/          # auditoría y evidencia del original
├── kuntur/         # Kuntur: RTL corregido, docs y verification/
├── docs/           # decisiones, evidencia fijada y archivo del informe anterior
├── paper/          # IEEE ES/EN, TikZ y bibliografía
├── model/          # contrato, referencia Python y evidencia numérica
├── isa/            # contrato ISA inmediato, encoder y macro GNU
├── rtl/            # unidades XQDot4Z y packed/XQDot4; no otro core
├── tests/          # pruebas del modelo, unidad y programas de integración
├── benchmarks/     # manifiesto, kernels de las cuatro variantes e inventario
├── results/        # esquema y evidencia de campaña; sin speedup agregado
└── scripts/        # auditoría y comprobaciones del proyecto
```

## Reproducir

Desde este directorio:

```sh
make baseline-check   # integridad del snapshot original
make audit            # reproduce la auditoría histórica en copia temporal
make core-test        # regresión ampliada del clon; evidencia nueva
make model-test       # referencia numérica: pruebas, logs y vectores
make rtl-test         # unidad aislada, dos simuladores, lint y controles negativos
make integration-test # ISA inmediata y pipeline, con extensión activada/desactivada
make scalar-test      # MUL aislada, pipeline y convivencia con XQDot4Zi
make packed-test      # B3 aislado, comparación aritmética con D y reconstrucción
make packed-integration-test # ISA B3, ocho configuraciones y corrección en Kuntur
make check            # identidad, hashes de evidencia y coherencia ES/EN
make paper            # genera main_es.pdf, main_en.pdf y main.pdf (alias ES)
```

Herramientas: Python 3, Icarus Verilog/vvp, Verilator y binutils RISC-V para
pruebas; pdfLaTeX, latexmk, BibTeX, IEEEtran y TikZ para artículos.
No se necesita red ni shell-escape para compilar.

M2/M3a, MUL y B3 requieren también make y C++ para el segundo simulador.
`make audit` comprueba la ejecución histórica, no conformidad: conserva los
defectos observados. `make check` comprueba evidencia fijada, no vuelve a
simular ni reemplaza `make core-test`, `make model-test`, `make rtl-test` o
`make integration-test`, `make scalar-test`, `make packed-test` o
`make packed-integration-test`. Tras cambiar el
RTL, el modelo, su contrato o sus tests se debe volver a verificar y actualizar
la referencia de evidencia correspondiente deliberadamente.

## Próximo paso, sin ampliar todavía el alcance

M1 está realizado: contrato, referencia entera, 15 tests agrupados,
524 288 inserciones de un término y 20 000 productos punto aleatorios,
con evidencia fijada en [MODEL_STATE.json](docs/MODEL_STATE.json).
M2 también está realizado: 556 734 comparaciones por simulador (Icarus y
Verilator), ocho controles negativos en cada uno, cuatro mutaciones detectadas
en Icarus y lint estricto sin excepciones. La aritmética es combinacional.

M3a está realizado: 25 programas en ambos simuladores, 1056 operaciones en
la campaña numérica integrada, encoding contra GNU, decodificación dirigida,
forwarding, stalls, flush, reset y dos mutaciones detectadas. Se activa con
`ENABLE_XQDOT4Z=1`; el valor por defecto es 0. La regresión histórica completa
se volvió a ejecutar con 0. No se ha sintetizado ni medido aceleración.

M3b está parcialmente realizado: MUL escalar opcional, 86 704 vectores por
simulador, 49 programas en ambos, cuatro configuraciones MUL/XQDot4Zi,
ocho controles por simulador y cuatro mutaciones (dos aritméticas, dos de
pipeline) en Icarus. La regresión base y M3a también pasaron sobre el RTL nuevo.

B3 ya tiene unidad aislada: 67 910 vectores por simulador, diez controles
negativos por simulador y cuatro mutaciones de RTL detectadas. Se reconstruyen
336 salidas por fila/grupo en 24 fixtures, a partir de 1680 respuestas RTL,
reutilizando Sa entre filas en el verificador. No son kernels en Kuntur.

B3 también está integrada: `ENABLE_XQDOT4=1`, apagada por defecto e
independiente de MUL y XQDot4Zi. Se verifican 123 programas en dos simuladores,
ocho configuraciones y tres mutaciones de integración. Cuatro pares de
fixtures de dos filas calculan ocho resultados iguales en B3 y D dentro de
Kuntur. B3 calcula Sa una vez con pesos iguales a uno, la reutiliza y ejecuta
MUL/SUB para corregir. Estos programas verifican exactitud; no son benchmarks
optimizados ni proporcionan una medición de aceleración.

El siguiente paso es cerrar las configuraciones y el régimen inicial de
metadatos, implementar kernels B1/B2/B3/D y fijar su frontera de medición.
La disponibilidad de MUL no completa aún los comparadores. El régimen de metadatos dinámicos
sigue abierto; no se deducen sus costos a partir de esta interfaz inmediata.
[Acta](docs/RESEARCH_CHARTER.md),
[protocolo](docs/EXPERIMENT_PROTOCOL.md) y [decisiones](docs/DECISIONS.md) son
notas de planificación revisables, no compromisos cerrados.

Antes de cualquier publicación se acordarán autoría, afiliación, permisos del
código docente, licencia y convocatoria. No se ha enviado ni publicado nada.

## Control de versiones

Desde 2026-09-09, este directorio es un repositorio Git autocontenido en `main`,
con un único commit inicial para establecer la base de investigación.
Los siguientes commits serán pequeños y coherentes, con mensajes Karma en
inglés: [convención](CONTRIBUTING.md). El
[registro de organización e historial](docs/VERSION_CONTROL.md) explica cómo
se conserva el Git anterior de Kuntur sin convertirlo en un submódulo.
