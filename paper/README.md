# Dos versiones del mismo borrador IEEE

Versión editorial 0.9: explicita especialización estática, distribución del
zero-point y amenazas a la validez como subsección. Se compactó el resumen
de verificación sin alterar sus evidencias ni conclusiones. El
[protocolo único](../docs/EXPERIMENT_PROTOCOL.md) y el
[manifiesto de diseño](../benchmarks/campaign.json) contienen el detalle.
Los kernels comparables siguen pendientes; no se confunde verificación con aceleración.

- `main_es.tex` → `main_es.pdf`: versión en español para trabajo y discusión.
- `main_en.tex` → `main_en.pdf`: versión equivalente en inglés.
- `ieee_preamble.tex`: paquetes y formato compartidos.
- `comparison_figure.tex`: único diagrama TikZ, con etiquetas bilingües.
- `references.bib`: bibliografía compartida; estilo `IEEEtran.bst`.

Se usa `\documentclass[conference,letterpaper]{IEEEtran}` (10 pt, dos columnas).
No se alteran márgenes, tipografía base, espaciado, encabezados ni captions.
Por indicación del autor, no se usa Nord ni ningún tema visual: texto negro,
páginas blancas y diagramas TikZ monocromos, sin rellenos de color.
Se equilibran las columnas finales con `balance`; al cambiar el texto debe
revisarse de nuevo la posición de `\balance` en ambos idiomas.
El diagrama se declara tras la introducción y se permite flotar en la segunda
columna de la primera página; `\suppressfloats[t]` preserva el resumen como
primer contenido de la primera columna. No se modifican los márgenes.

Los dos textos contienen las mismas secciones, ecuaciones, citas, alcance y
estado de resultados. Se editan juntos. No son dos artículos independientes
ni dos envíos. La aceptación de una versión en español depende del venue.
En ambos artículos se utiliza únicamente Kuntur como nombre del procesador.
La identidad del proyecto de origen se documenta fuera del artículo, en los
metadatos de procedencia y el registro de correcciones del core.

El modo conferencia es una base provisional, no una decisión de convocatoria.
Cuando se elija una, se verificará su plantilla, papel, páginas, anonimato,
idioma y proceso de validación PDF. No se ha declarado un límite IEEE universal.

Compilar desde la raíz: `make paper`. Revisar: `make check`.
La evaluación de rendimiento y las conclusiones siguen pendientes; no se llena espacio para
alcanzar un número artificial de páginas. Los campos de autoría son marcadores
de borrador, no autores ni afiliaciones reales.

Revisión local v0.9, 2026-09-09: ambos PDF tienen dos páginas Letter y fuentes
Type 1 incrustadas. Se revisaron visualmente las cuatro páginas después de
incorporar las amenazas a la validez, sin recortes ni solapamientos.
No hay citas indefinidas ni avisos Overfull. Quedan siete avisos Underfull
de espaciado en párrafos españoles; el ajuste editorial final sigue pendiente
antes de un eventual envío. En inglés no aparecen esos avisos.
Esto no sustituye la validación exigida por un venue.

El informe largo anterior se conserva íntegro en `docs/archive/paper-v0.1/`.
Los antiguos `sections/`, `style.tex` y `metadata.tex` de esta carpeta son
material de procedencia v0.1 y NO se cargan en los documentos IEEE.
`main.tex` es solo un acceso compatible a la versión española.

La justificación y las fuentes oficiales están en `../docs/IEEE_FORMAT.md`.
