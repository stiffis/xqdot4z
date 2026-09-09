# TODO — Mejoras a la Entrega 1 (pendientes, para después)

Estos puntos corresponden a la Entrega 1 (pipeline + hazard unit), que ya se
entregó pero se puede mejorar de cara a la presentación final. No bloquean E2.

## 1. Diagramas de datapath final (los dos)

La rúbrica pide "Diagrama de datapath final" en DOS secciones:
- [ ] Diagrama del datapath con la **implementación de instrucciones** (pipeline base).
- [ ] Diagrama del datapath con la **hazard unit** integrada (forwarding/stall/flush,
      señales `ForwardAE/BE`, `StallF/D`, `FlushD/E`).

## 2. Programa ISA sin dependencias — respaldarlo con los testbenches por etapa

- [ ] En el informe, mostrar el "programa ISA sin dependencias" ilustrado/reemplazado
      con los **testbenches consecutivos** que se hicieron en cada etapa de la
      implementación incremental: `base`, `ctrl`, `xor`, `lui`, `shift`, `branch3`,
      `jalr`. Es decir, evidenciar que cada familia de instrucciones se validó por
      separado conforme se implementó.

## 3. Programa con dependencias más complejo

- [ ] Reemplazar el programa de dependencias actual (corto) por uno **más complejo /
      realista** en la sección del "programa con dependencias" (o en el punto 1),
      para que la evidencia sea más fuerte.

## 4. Mostrar el fallo SIN hazard unit (programas 2, 3 y 4) con waveform

- [ ] Explicar y mostrar con **waveform** cómo los programas de prueba de hazards
      (forward / stall / flush, los programas 2, 3 y 4) **fallan** cuando se corren
      SIN la hazard unit, antes de mostrar que CON la hazard unit funcionan.
      Es justo lo que pide la rúbrica ("mostrar que sin Hazard unit los programas
      2, 3 y 4 no funcionan correctamente").
