# MASTER README — Presentación Final (Beamer)

> Documento de handoff para continuar armando la **presentación final** del
> proyecto en una conversación nueva. Contiene: de qué trata el proyecto, cómo
> trabajamos, dónde está cada cosa, qué contiene cada documento/bitácora, el
> estado actual de la presentación y qué falta pulir.

---

## 1. De qué trata el proyecto

Procesador **RISC-V segmentado (pipelined) con extensión C (RVC)**, escrito en
Verilog y probado con Icarus (`iverilog`/`vvp`). Es un proyecto universitario
(UTEC, Arquitectura de Computadoras, 2026-I) dividido en 3 entregas + una
presentación final.

Proyecto en: **`/home/stiff/kirky-arqui/`** (repo git standalone, rama `main`,
se commitea directo a main sin ramas).

| Entrega | Qué es | Estado |
|---|---|---|
| **E1** (5 pts) | Pipeline de 5 etapas + **Hazard Unit** (forward/stall/flush) + ISA del Cuadro 1 (24 instr. RV32I) | Entregada ✅ |
| **E2** (4 pts) | Extensión C parte 1: **11 instrucciones comprimidas** de ALU/reg-inmediato | Entregada ✅ |
| **E3** (3 pts) | Extensión C parte 2: **10 instrucciones** de memoria y control de flujo | Entregada ✅ (30/06) |
| **Presentación Final** (8 pts) | 15 min + preguntas grupales/individuales | **EN CURSO** ← estamos aquí |

**Idea técnica clave de RVC:** *descomprimir en Fetch*. El `decompressor.v` es
un módulo **combinacional** que expande las instrucciones de 16 bits a su
equivalente RV32I de 32 bits **antes** del registro IF/ID. Así, ni el pipeline,
ni el control, ni la hazard unit se modifican. Además: **ventana deslizante** en
`imem` (para PC desalineado a palabra) e **incremento variable** del PC (+2/+4).
Costo en ciclos: **cero** (todo combinacional).

---

## 2. Cómo trabajamos (convenciones — IMPORTANTE)

- **Por fases incrementales**, una familia de instrucciones a la vez. Cada fase:
  implementar → programa `.mem` de prueba → testbench → `make test` sigue verde
  → generar waveform (`.vcd` + `.gtkw`) → actualizar bitácora. (Ej: E2.1, E2.2…,
  E3.1, E3.2…)
- **Sin comentarios en el código** que se genere (nada de `//`, `#`, `"""`,
  inline). El usuario lo pidió explícitamente.
- **No poner Co-Authored-By** ni "co-autor" en los commits.
- **Avisar antes de tocar el Verilog de la universidad** (el de `week13`). El
  proyecto `kirky-arqui` es la copia sobre la que sí se trabaja.
- **Diagramas**: se dibujan en TikZ en `/home/stiff/graphics-processor/`
  (proyecto aparte, ver §5). En las notas de Obsidian se usa TikZ + TikZJax.
- **Compilar LaTeX**: `pdflatex -interaction=nonstopmode <archivo>.tex` (dos
  pasadas si hay referencias/`\tableofcontents`).
- **No limpiar los `.aux/.log/.nav/...` tras cada compilación** mientras se está
  editando (gasta tokens y aún hay ediciones pendientes). Limpiar solo al final.
- **No leer el PDF tras cada micro-edición** salvo que se necesite verificar algo
  visual concreto (ahorro de tokens/contexto).
- Ritmo objetivo de la presentación: **15 min ≈ 15-20 frames** de contenido.

---

## 3. Mapa de archivos

```
/home/stiff/kirky-arqui/                  <- PROYECTO (repo git, main)
├── rtl/                                  <- Verilog del procesador
│   ├── decompressor.v   *** núcleo de RVC (E2+E3), combinacional 16->32
│   ├── imem.v           ventana deslizante
│   ├── datapath.v, controller.v, hazardunit.v, alu.v, aludec.v, maindec.v,
│   ├── extend.v, regfile.v, dmem.v, riscvpipe.v, top.v, mux2/3.v, flop*.v, adder.v
├── tests/
│   ├── programs/         riscvtest_*.s y .mem (base, ctrl, xor, lui, shift,
│   │                     branch3, jalr, deps, isa, forward, stall, flush,
│   │                     caddi, cir, ca, cb, mul10, clsw, clspsp, cbz, cj, cjr, sumloop)
│   └── testbench_*.v
├── waves/<test>/<test>.vcd + .gtkw       <- waveforms curados
├── run_tests.sh          regresión completa (make test) -> 23/23 PASS
├── run_hazard_demo.sh    demo forward/stall/flush CON hazard unit
├── toolchain/
│   ├── asm2mem.sh        ensambla .s -> .mem (usa riscv64-linux-gnu-as, -march rv32i/rv32ic)
│   └── gen_wave.sh       genera .vcd de un test (usa tests/dump.v)
├── IMPLEMENTACION_PIPELINE_BASE.md   *** bitácora E1 (ver §4)
├── IMPLEMENTACION_RVC.md             *** bitácora E2+E3 (ver §4)
├── TODO_ENTREGA1.md                  mejoras pendientes de E1 para la presentación
├── README.md
└── docs/
    ├── informe.tex / informe.pdf     *** informe completo (E1+E2+E3), 27 pág
    ├── teoria_rvc.tex/pdf            material teórico de RVC
    ├── presentacion/
    │   ├── presentacion.tex          *** LA PRESENTACIÓN (Beamer)
    │   ├── presentacion.pdf
    │   └── README.md                 <- ESTE ARCHIVO
    └── (figuras, ver §6)

/home/stiff/graphics-processor/           <- DIAGRAMAS TikZ (proyecto aparte)
├── datapath/datapath.tex             *** datapath completo con control
├── alu_extended/alu_extended.tex     *** ALU con operaciones extra en rojo
├── alu_internal/, mux/, registro/, imem/, alu/, extend/, regfile/, and/,
│   xor/, muxn/, zeroext/, shifter/    <- componentes/piezas reutilizables

/home/stiff/kirky-arqui-nohazard/         <- COPIA con hazardunit.v neutralizada
                                             (solo para waveforms del FALLO sin
                                             unidad de riesgos: forward/stall/flush)
```

---

## 4. Qué contiene cada bitácora / documento

- **`IMPLEMENTACION_PIPELINE_BASE.md`** — bitácora de la Entrega 1. Cómo se pasó
  de single-cycle a pipeline, las 10 fases de implementación del ISA, la
  hazard unit, decisiones (ej. regfile write-first en negedge para distancia-3).

- **`IMPLEMENTACION_RVC.md`** — bitácora de E2 y E3. Tabla de fases (E2.1–E2.5,
  E3.1–E3.6), y por cada fase: meta, cómo se implementó y por qué, programa de
  prueba, validación, estado. Incluye bugs encontrados (ej. destino de `c.lw` en
  `c[4:2]` no `c[9:7]`). El "flujo de trabajo por fase" está documentado ahí.

- **`TODO_ENTREGA1.md`** — 4 mejoras de E1 pensadas para la presentación:
  (1) diagramas de datapath [✅ hecho], (2) reemplazar "programa ISA sin
  dependencias" por testbenches por etapa [pendiente], (3) programa de
  dependencias más complejo [pendiente], (4) waveforms del fallo sin hazard unit
  [✅ hecho].

- **`docs/informe.tex`** — informe completo (27 pág). Parte 1: pipeline + hazard
  unit (con figuras del datapath, ALU modificada, waveforms del fallo sin/​con
  hazard unit). Parte 2: RVC (E2+E3), tabla de encoding de las 21 instrucciones,
  algoritmo sumloop, comparativa tamaño/performance. **Fuente de verdad del
  contenido** — la presentación reutiliza sus figuras y tablas.

- **Memoria global** en `~/.claude/projects/-home-stiff-class-notes/memory/`
  (se carga sola cada sesión vía `MEMORY.md`): `no-comentarios-codigo`,
  `riscy-vs-verilog-boundary`, `obsidian-tikzjax-diagramas`, etc.

---

## 5. Diagramas TikZ (`/home/stiff/graphics-processor/`)

Se construyeron **pieza por pieza** (mux, registro, ALU, imem, regfile, extend,
compuertas AND/OR/XOR, shifter, zeroext…) y luego se ensamblaron:

- **`datapath/datapath.tex`** → datapath completo de 5 etapas con **Control Unit**
  (azul) y las adiciones propias en **rojo** (Jalr, funct3E, ALUControl de 4
  bits, mux de PCTargetE). Copiado al informe como `docs/datapath_final.pdf`.
- **`alu_extended/alu_extended.tex`** → ALU interna (Fig. 5.18b de Harris) con las
  operaciones añadidas en **rojo** (xor, lui, shifter sll/srl/sra), mux de salida
  de 5→10 entradas, ALUControl 3→4 bits. Copiado como `docs/alu_modificada.pdf`.

Convención de color: **rojo = lo que agregamos/modificamos** sobre la base de
Harris & Harris. Se compila con `pdflatex`.

---

## 6. Figuras disponibles en `docs/` (para reusar en la presentación)

| Archivo | Qué muestra |
|---|---|
| `pipeline_diagram.png` | Fig. 7.51 genérica de Harris (pipeline con control) |
| `datapath_final.pdf` | **Nuestro** datapath con control (adiciones en rojo) |
| `alu_modificada.pdf` | ALU interna con operaciones extra en rojo |
| `hazard_forward_nohu.png` / `_stall_` / `_flush_` | **Fallo** sin hazard unit (waveform) |
| `hazard_forward_waveform.png` / `_stall_` / `_flush_` | Funcionando **con** hazard unit |
| `hazard_demo.png` / `hazard_fail.png` | Salidas de terminal de los scripts |
| `mul10_waveform.png` | Algoritmo mul10 (E2, shift-and-add) |
| `sumloop_waveform.png` | **Algoritmo E3** (bucle suma 5+4+3+2+1=15) |
| `waveform_isa.png` | Programa ISA sin dependencias (E1) |
| `utec_logo.jpg` | Logo |

---

## 7. Estado actual de la PRESENTACIÓN

Archivo: **`docs/presentacion/presentacion.tex`** — compila OK (~26 frames).

- Clase `beamer`, tema **Madrid + colortheme default**.
- Preámbulo: `listings` (estilo verilog), `xcolor`, `booktabs`, `amssymb`.
- **`\AtBeginSection`** muestra el índice resaltando la sección actual.
- **Portada**: título "Procesador RISC-V Pipelined con Extensión C", subtítulo,
  autores en **3 columnas** (apellidos arriba, nombres abajo), instituto UTEC,
  fecha "Julio 2026" (solo en portada, no en el pie).
- **Pie de página (footline) personalizado**: dos mitades — izquierda
  "Ildefonso, Paucar, Rosillo"; derecha título corto + "N / total" pegado a la
  esquina derecha. Está en un bloque `\makeatletter … \setbeamertemplate{footline}`.
- **REGLA BEAMER CRÍTICA**: cualquier frame con `lstlisting`/verbatim necesita
  `\begin{frame}[fragile]{...}`. Si falta, explota en cascada de errores.

**Autores (nombres completos):**
- Steve Andy Ildefonso Santos
- Miguel Luis Paucar Barrios
- Marcelo Mateo Rosillo Rodríguez

### Frames actuales (por sección)
1. **Pipeline y Hazard Unit**: 5 etapas · Riesgos · Fallo sin hazard unit ·
   Solución forward/stall/flush · Datapath final.
2. **Extensión C**: ¿Qué es RVC? · Cambios en datapath · Módulos · ALU
   modificada · Las 21 instrucciones · Ejemplo c.lw/c.sw (con el bug real) ·
   Ejemplo desambiguación c.jr/c.jalr/c.add · Encoding (tabla de las 21) ·
   Limitaciones.
3. **Resultados**: Programa sumloop · Waveform · Comparativa tamaño/performance ·
   Validación (23/23 PASS).
4. **Conclusiones**: conclusiones, desafíos y mejoras.
5. Frame final "Gracias / Preguntas".

Nota: `c.mv` NO se presenta como instrucción propia (es subproducto de la
desambiguación del cuadrante 2); solo se menciona en el código.

---

## 8. Rúbrica de la Presentación Final (8 pts) — checklist

Presentación (5 pts, 15 min):
- [x] Explicación Pipeline funcionando con Hazard unit — 0.5
- [x] Explicación implementación instrucciones C — 2 pts
  - [x] instrucciones importantes (ejemplos c.lw/c.sw, c.jr/c.jalr/c.add)
  - [x] módulos agregados / cambios en el datapath
  - [x] **Encoding** (tabla de las 21)
  - [x] Limitaciones
- [x] Test programa ISA-algoritmo (sumloop) — 2 pts
  - [x] explicación de resultados (waveform)
  - [x] comparativa tamaño y performance
- [x] Conclusiones, desafíos y mejoras — 0.5

Preguntas grupal e individual (1 + 2 pts, 5 min): **prepararse** — cada
integrante debe poder explicar cualquier módulo (decompressor, hazard unit,
datapath). No es un frame, es preparación oral.

**Cobertura de contenido: 100% de la rúbrica.** Lo que queda es pulido visual y
preparación oral (ver §9).

---

## 9. Qué falta / próximos pasos para la presentación

- **Pulido visual** de frames (lo que se estaba haciendo): espaciados, tamaños de
  figura, que ninguna diapositiva quede sobrecargada de texto.
- (Opcional, TODO_ENTREGA1 #2 y #3) reforzar E1 con testbenches por etapa y un
  programa de dependencias más complejo — no bloquea la presentación.
- **Notas del orador / guion** por frame (quién dice qué, para los 15 min).
- **Ensayo** para cronometrar 15 min y preparar respuestas a preguntas.
- Al terminar de editar: limpiar auxiliares (`rm -f presentacion.{aux,log,nav,out,snm,toc,vrb}`).

## 10. Datos rápidos que se preguntan seguido

- Regresión: **23/23 PASS** (`./run_tests.sh` desde `kirky-arqui/`).
- 21 instrucciones comprimidas totales (11 de E2 + 10 de E3).
- Comparativa sumloop: 24 B (RV32I) → 18 B (RVC) = **25% menos**; mismos ciclos.
- Formatos RVC usados: CI, CR, CA, CB, CL, CS, CSS, CJ.
- Distinción 16/32 bits: `instr[1:0] != 2'b11` ⇒ comprimida.
- Ventana deslizante: `rd = a[1] ? {w1[15:0], w0[31:16]} : w0` (combinacional).
- El fallo sin hazard unit se reproduce en `/home/stiff/kirky-arqui-nohazard/`
  (hazardunit con todas las salidas en no-op).
