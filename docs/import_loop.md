# The LDraw Import Loop — an engine-agnostic specification

This document describes how an LDraw model is turned into renderable geometry,
in enough detail to reimplement the loader against **any** target engine
(Blender, Godot, three.js, a custom renderer, an exporter, …). It is derived
from the reference implementation in this repository but deliberately abstracts
away every Blender-specific call behind a small **sink** interface (see
[§5](#5-the-engine-sink-interface)).

The core of the loader is a single recursive traversal — `LDrawNode.load` in
`ldraw_node.py`. Everything else is parsing that feeds it and mesh assembly that
consumes what it produces.

> **Scope.** This describes the pipeline as it runs under the loader's **default
> options** — the canonical flow. Behaviours a default enables are stated as
> simply happening; non-default toggles (Geometry-Nodes instancing, normal
> recomputation, separate edge objects, step animation, shortcut-as-model, …) are
> omitted.

> Notation: pseudocode is imperative and language-neutral. `A @ B` is 4×4 matrix
> multiplication (column-vector convention: `A @ B` applies `B` first, then `A`).
> `v'` = `M @ v` transforms point `v` by `M`. Vectors are LDraw XYZ unless noted.

---

## Contents

1. [Pipeline overview](#1-pipeline-overview)
2. [Coordinate system, units, and the matrix convention](#2-coordinate-system-units-and-the-matrix-convention)
3. [The parsed data model](#3-the-parsed-data-model)
4. [Phase 1 — Parsing](#4-phase-1--parsing)
5. [The engine sink interface](#5-the-engine-sink-interface)
6. [Phase 2 — The traversal (`load`)](#6-phase-2--the-traversal-load)
7. [Accumulated-state reference](#7-accumulated-state-reference)
8. [The part/subpart boundary — where a new object begins](#8-the-partsubpart-boundary--where-a-new-object-begins)
9. [BFC and winding](#9-bfc-and-winding)
10. [Color resolution](#10-color-resolution)
11. [The `!TEXMAP` state machine](#11-the-texmap-state-machine)
12. [The `PE_TEX` state machine (Stud.io)](#12-the-pe_tex-state-machine-studio)
13. [Model loose-geometry hoisting](#13-model-loose-geometry-hoisting)
14. [Deduplication keys](#14-deduplication-keys)
15. [Mesh assembly and post-processing](#15-mesh-assembly-and-post-processing)
16. [Implementation order](#16-implementation-order)

---

## 1. Pipeline overview

```
 file path
    │
    ▼
┌───────────────┐   locate + read + split MPD + classify + parse each line
│  PARSE        │──────────────────────────────────────────────────────────►  LDrawFile{ header, child_nodes[] }
└───────────────┘                                                              (cached by filename)
    │
    ▼
┌───────────────┐   depth-first walk; accumulate transform/color/BFC/texmap;
│  TRAVERSE     │   decide object boundaries; collect faces into GeometryData
│  (load)       │──────────────────────────────────────────────────────────►  GeometryData per unique (file,color,texmap…)
└───────────────┘                                                              + a stream of "emit object" calls
    │
    ▼
┌───────────────┐   build vertex/face buffers, weld, mark edges, assign
│  ASSEMBLE     │   materials, smooth, scale                                ►  engine mesh + engine objects
└───────────────┘
```

Three phases, three data levels:

| Phase    | Input            | Output                                             |
|----------|------------------|----------------------------------------------------|
| Parse    | text lines       | `LDrawFile` trees of `LDrawNode` (cached)          |
| Traverse | root `LDrawFile` | `GeometryData` buffers + object-emission events    |
| Assemble | `GeometryData`   | engine meshes + engine objects                     |

Parsing and assembly are pure and cacheable. The traversal is where all the
LDraw semantics live, and is the subject of most of this document.

---

## 2. Coordinate system, units, and the matrix convention

**LDraw space** is right-handed with **−Y up**. One LDraw Unit (LDU) ≈ 0.4 mm; a
standard brick is 20 LDU wide and 24 LDU tall. Most engines are **+Z up** (or
+Y up), so a fixed **axis conversion** is required.

Define one rotation that maps LDraw axes to your engine's axes. For a +Z-up
engine that is a −90° rotation about X:

```
ROOT_CONV       = RotateX(-90°)      # LDraw (−Y up)  →  engine (+Z up)
ROOT_CONV_INV   = RotateX(+90°)      # inverse
```

A subfile reference line (`1 …`) carries a 3×4 placement written as translation
`(x y z)` plus a row-major 3×3 `(a b c / d e f / g h i)`. Assemble it as:

```
M = | a b c x |
    | d e f y |
    | g h i z |
    | 0 0 0 1 |
```

### The placement invariant

For any face vertex `v_local` authored in a part's own local frame, its final
world position is:

```
v_world = ROOT_CONV @ (M_root · M_1 · M_2 · … · M_k) @ v_local
```

where `M_1…M_k` is the chain of subfile placement matrices from the root down to
the part containing the face. That is the entire spatial story: **compose the
subfile matrices top-to-bottom, prepend the axis conversion, done.**

### How the axis conversion is split (mesh sharing)

Every identical part+color is stored **once** as a shared mesh that many objects
reference, so geometry must be placement-independent. The invariant is factored so
the **mesh** is baked in a canonical frame and the **object transform** carries
the placement:

- Faces of a part are collected in the part's **local** frame (identity), so the
  mesh is placement-independent and can be deduplicated (see [§14](#14-deduplication-keys)).
- When the mesh is realized, it is baked with `ROOT_CONV` (mesh vertices become
  `ROOT_CONV @ v_local`).
- The object transform is therefore `M_chain @ ROOT_CONV_INV`, so that
  `object_transform @ mesh_vertex = M_chain @ ROOT_CONV_INV @ ROOT_CONV @ v_local
  = M_chain @ v_local` — and the single `ROOT_CONV` injected at the root restores
  the global axis flip.
- The **root** node multiplies its own matrix by `ROOT_CONV` once, which
  propagates down the chain and supplies the leading `ROOT_CONV` of the invariant.

### Scale

One similarity transform is applied at assembly time, never during traversal: the
**import scale** — a uniform scale (0.02) baked into each mesh so the model is a
convenient size in the engine.

(The format's tooling can also apply a small per-part *gap* shrink so adjacent
bricks show a seam; it is disabled in this flow and never runs.)

---

## 3. The parsed data model

Parsing produces two record types.

```
LDrawFile:
    name            # canonical lowercase filename, e.g. "3001.dat"
    part_type       # classification: model | part | shortcut | subpart |
                    #   primitive | configuration | None(→model)
    child_nodes[]   # ordered LDrawNode, one per meaningful body line
    geometry_commands  # multiset of which of "2".."5"/"1"→geometry appeared
                       # (used only for has_geometry())
    # …header fields: description, author, license, keywords, etc.

LDrawNode:                       # one body line, already interpreted
    meta_command    # "1".."5"  → geometry/subfile
                    # "bfc","texmap","step","save","clear","print",
                    #   "group_*","leocad_camera",
                    #   "pe_tex_path","pe_tex_info","pe_tex_next_shear"
    line            # the cleaned source line (single-spaced)
    color_code      # for "1".."5": the line's color token (string)
    matrix          # for "1": the 4×4 placement
    file            # for "1": the referenced LDrawFile (already resolved)
    vertices[]      # for "2".."5": the raw vertex list (LDraw coords)
    uvs[]           # for "3" with explicit UVs: 3 UV pairs, else empty
    meta_args{}     # parsed args for meta lines (e.g. bfc command word)
```

Geometry buffers produced by the traversal:

```
FaceData:                        # one collected 2/3/4/5 line
    vertices[]      # copied from the node, winding-normalized, then transformed
    color_code      # effective color for this face
    winding         # "CCW"/"CW"/None (input to normalization)
    inverted        # accumulated BFC inversion (used only by PE_TEX seeding)
    texmap          # active !TEXMAP projector, or None
    pe_tex_path     # active PE_TEX projector, or None

GeometryData:                    # one shareable mesh's worth of geometry
    key             # dedup key (see §14)
    file            # source LDrawFile
    bfc_certified   # certification state at the part root (material hint)
    edge_data[]     # type-2 lines   (hard edges)
    face_data[]     # type-3/4 lines (surfaces)
    line_data[]     # type-5 lines   (optional/conditional lines)
```

---

## 4. Phase 1 — Parsing

### 4.1 File loading and MPD splitting

A `.ldr`/`.dat`/`.mpd`/`.io` file is read as UTF-8 (tolerate a BOM). `.io` is a
zip; read `model.ldr` from inside it.

An **MPD** (multi-part document) packs many named sub-files into one physical
file using `0 FILE <name>` … `0 NOFILE` blocks. Split it so each `0 FILE`
section becomes its own logical `LDrawFile` in the filename cache. The first
`0 FILE` name is the document's entry point. `0 !DATA <name>` … blocks embed
base64 PNGs (Stud.io textures); collect them into a named-image store.

Resolve subfile names against a search path: the current file's directory, then
the LDraw library (`p/`, `parts/`, `models/`, unofficial mirrors). Names are
matched case-insensitively and with `\` normalized to `/`.

**Cache aggressively.** The same primitive (`4-4cyli.dat`, `stud.dat`, …) is
referenced thousands of times; parse each filename at most once and reuse the
`LDrawFile`.

### 4.2 Line classification

Trim, collapse runs of whitespace to single spaces, and dispatch on the first
token:

- `0 …` — a comment or meta command. Recognize the meta commands you support
  (`BFC`, `STEP`, `!TEXMAP`, `PE_TEX_*`, group metas, `!LEOCAD CAMERA`, …) and
  turn each into an `LDrawNode` with the right `meta_command`; **header** metas
  (`Name:`, `Author:`, `!LDRAW_ORG`, `!KEYWORDS`, …) update the file record and
  emit no node. Unknown `0` lines are ignored.
- `1 <color> <x y z a…i> <file>` — a subfile reference. Parse color and matrix,
  **resolve and parse the referenced file now** (recursively), store as a node
  with `meta_command="1"`.
- `2 <color> <6 floats>` — a line (edge): 2 vertices.
- `3 <color> <9 floats> [6 UV floats]` — a triangle: 3 vertices, optional UVs.
- `4 <color> <12 floats>` — a quad: 4 vertices.
- `5 <color> <12 floats>` — an optional/conditional line: 2 real + 2 control
  vertices.

Vertices are stored in LDraw coordinates exactly as written. Preserve child
order — texmap/BFC state is positional.

### 4.3 File classification (`part_type`)

From the `0 !LDRAW_ORG <type>` header (or unofficial variants), classify into:
`model`, `part`, `shortcut`, `subpart`, `primitive`, `configuration`. **A file
with no type is treated as a model** (models are user-authored and often
untyped). Derived predicates used by the traversal:

```
is_like_model(f)  = f.part_type ∈ {model, submodel, None, …}
is_part(f)        = f.part_type ∈ {part, …}
is_like_part(f)   = is_part(f)
                    OR is_shortcut(f)                              # shortcut → one object
                    OR (has_geometry(f) AND NOT is_like_model(f))  # loose-geometry file
is_geometry(f)    = f.part_type ∈ {subpart, primitive}   # cannot stand alone
has_geometry(f)   = f contains ≥1 of line types 2/3/4/5, or a "1" to a geometry file
```

These predicates are the **entire basis** for deciding where objects begin
([§8](#8-the-partsubpart-boundary--where-a-new-object-begins)).

---

## 5. The engine sink interface

Abstract every engine call behind this interface. The traversal calls only
these; a port implements them.

```
sink.material(color_code, bfc_certified, slopes, texmap, pe_texmaps) -> Material
        # resolve an LDraw color code (+ context) to an engine material.
        # Color 16/24 have already been resolved to a concrete code by the caller.

sink.realize_mesh(key, geometry_data, color_code) -> Mesh
        # build (or fetch cached) a mesh from collected geometry. Idempotent by key.
        # See §15 for what "build" entails.

sink.emit_object(mesh, placement_matrix, color_code, group)      # one object per placement

sink.begin_group(name) / sink.end_group()                        # scene grouping
sink.named_image(name) -> Image                                  # texture store lookup
```

`group` is whatever your engine uses to organize a scene (collection, node,
layer).

---

## 6. Phase 2 — The traversal (`load`)

This is the heart of the loader: a depth-first walk of the parsed tree that
threads accumulated state down and collects geometry / emits objects as it goes.

The full accumulated state is listed in [§7](#7-accumulated-state-reference). The
pseudocode below is the reference `load`, cleaned of disabled experiments,
non-default options, and engine specifics.

```
function load(node, state):
    file = node.file

    # ── 0. cheap skips ────────────────────────────────────────────────
    if file.is_edge_logo(): return              # edge logos are not imported

    # ── 1. transforms ─────────────────────────────────────────────────
    # parent_matrix : placement of the level above this one
    # accum_matrix  : product of every transform above (used for some emits)
    m = node.matrix
    if node.is_root:
        m = m @ ROOT_CONV                       # inject the axis conversion once

    current_matrix = state.parent_matrix @ m    # placement of THIS node
    child_accum    = state.accum_matrix @ current_matrix
    child_matrix   = current_matrix             # placement passed to children

    color = state.color_code                    # effective color entering here

    # ── 2. classify this node ─────────────────────────────────────────
    # geometry_data is None until we cross into a part; then it is passed
    # down so nested subparts/primitives merge into the SAME mesh.
    top_part  = (state.geometry_data is None) and file.is_like_part()
    top_model = (state.geometry_data is None) and file.is_like_model()

    key = build_key(file.name, color, state.texmap, state.pe_tex_paths)   # §14

    if top_part:
        part_count += 1
        geometry_data = mesh_cache.get(key)     # may be None (not built yet)
        # bake the axis-conversion split for a shareable mesh (§2):
        current_matrix = current_matrix @ ROOT_CONV_INV
        round_matrix(current_matrix, 6)         # kill float noise for dedup
        child_matrix = IDENTITY                 # collect faces in local space
    else if top_model:
        current_model_filename = file.name

    if top_part or top_model:
        # a part defines its own BFC world; reset inherited winding/cull state
        state.accum_cull    = True
        state.accum_invert  = False
        state.bfc_certified = None

    group = state.group or default_group_for(file, top_model)   # §5

    # ── 3. should we process children at all? ─────────────────────────
    # If this is a part whose mesh is already cached, skip the whole subtree.
    is_top = top_part
    model_geometry = None            # synthetic loose-geometry buffer (§13)

    if (not is_top) or (geometry_data is None):
        if is_top:
            geometry_data = new GeometryData()

        # ── per-file BFC + PE_TEX cursors (reset for each file) ────────
        local_cull  = True
        winding     = "CCW"
        invert_next = False
        current_pe_tex_path = None
        next_shear  = False
        subfile_index = 0            # counts only "1" lines (PE_TEX addressing)

        # ── 4. the child loop ─────────────────────────────────────────
        for child in file.child_nodes:
            cmd = child.meta_command

            if cmd in {1,2,3,4,5} and not state.texmap_fallback:
                child_color = determine_color(color, child.color_code)   # §10

                # Decide the target buffer: model-level loose geometry and
                # bare primitive/subpart refs are HOISTED into model_geometry
                # (see §13); everything inside a part goes to geometry_data.
                hoist = (geometry_data is None) and
                        (cmd != 1 or (child.file != None and child.file.is_geometry()))
                target        = geometry_data
                target_matrix = child_matrix
                if hoist:
                    model_geometry = model_geometry or new GeometryData()
                    target         = model_geometry
                    target_matrix  = IDENTITY

                if cmd == 1:
                    child_pe = descend_pe_tex(state, child, subfile_index)   # §12
                    load(child, state.derive(
                        color_code   = child_color,
                        parent_matrix= target_matrix,
                        accum_matrix = child_accum,
                        geometry_data= target,
                        accum_cull   = state.bfc_certified and state.accum_cull and local_cull,
                        accum_invert = state.accum_invert XOR invert_next,
                        group        = group,
                        pe_tex_paths = child_pe,
                        # texmap fields pass through unchanged
                    ))
                    subfile_index += 1
                    handle_group_nxt(node, child)                # LDCAD group nesting

                else:   # a geometry line 2/3/4/5 — collect now, transform at part close
                    collect_face(target, child, target_matrix, child_color,
                                 winding, state, invert_next)

            else if cmd == "bfc":
                (local_cull, winding, invert_next, state.bfc_certified) =
                    meta_bfc(child.line, child_matrix, local_cull, winding,
                             invert_next, state.accum_invert, state.bfc_certified)   # §9

            else if cmd == "texmap":
                (state.texmap, state.texmap_start, state.texmap_next,
                 state.texmap_fallback) =
                    meta_texmap(child.line, child_matrix, state.texmaps, …)   # §11

            else if cmd startswith "pe_tex_":
                (current_pe_tex_path, next_shear) =
                    parse_pe_tex(child, current_pe_tex_path, next_shear, state)   # §12

            else:
                # model-level metas: only meaningful when geometry_data is None,
                # never cached, so run every time encountered.
                dispatch_scene_meta(cmd, child, child_matrix)   # step/save/clear/print/group/camera

            # NEXT texture ends after exactly one geometry line (§11)
            if state.texmap_next and cmd in {1,2,3,4,5}:
                (state.texmap, state.texmap_start, state.texmap_next,
                 state.texmap_fallback) = set_texmap_end(state.texmaps)

            # INVERTNEXT applies to exactly the next line
            if cmd != "bfc" or child.meta_args["command"] != "INVERTNEXT":
                invert_next = False

    # ── 5. emit the model's hoisted loose geometry, if any (§13) ───────
    if model_geometry != None:
        emit_part(file, f"{file.name}:geometry", model_geometry,
                  child_matrix @ ROOT_CONV_INV, color, group)

    # ── 6. emit this part, if this call owns one ──────────────────────
    if is_top:
        if key not in mesh_cache and geometry_data != None:
            geometry_data.key = key
            geometry_data.bfc_certified = state.bfc_certified
            geometry_data.process()               # transform every collected face
            geometry_data.project_pe_texmaps()    # §12 flood-fill box decals
            mesh_cache[key] = geometry_data
        geometry_data = mesh_cache[key]

        mesh = sink.realize_mesh(key, geometry_data, color)
        obj  = sink.emit_object(mesh, current_matrix, color, group)
        return obj
```

Key control-flow facts to preserve exactly:

- **`geometry_data is None` is the "am I above a part?" flag.** It is None while
  walking models; it becomes a fresh buffer the moment a part starts and is then
  threaded down so every subpart/primitive merges into that one buffer.
- **A cached part short-circuits its whole subtree.** If `key` is already in the
  mesh cache, the children are never walked. This is the main performance lever.
- **Face collection and object emission are decoupled.** Faces accumulate into
  `GeometryData`; the object is emitted once, at the part root.
- **Faces are transformed in bulk at part close.** They are collected untransformed
  during the walk; the whole `GeometryData` is processed once, just before the mesh
  is built.

---

## 7. Accumulated-state reference

State threaded into each `load` call. "Derived" = recomputed for the child; the
rest pass through unchanged unless a handler rewrites them mid-file.

| Field            | Meaning                                                        | At root        |
|------------------|----------------------------------------------------------------|----------------|
| `color_code`     | effective color entering this node (16/24 resolved by parent)  | user color     |
| `parent_matrix`  | placement of the level above                                   | identity       |
| `accum_matrix`   | product of all transforms above                                | identity       |
| `geometry_data`  | current mesh buffer; **None ⇒ still above a part**             | None           |
| `accum_cull`     | BFC: is back-face culling active down to here                  | True           |
| `accum_invert`   | BFC: accumulated INVERTNEXT/mirror parity                      | False          |
| `bfc_certified`  | BFC: certification state (True/False/None)                     | None           |
| `group`          | scene grouping handle                                          | root group     |
| `texmap`         | active `!TEXMAP` projector or None                             | None           |
| `texmap_start`   | inside a `START…END` texmap block                              | False          |
| `texmap_next`    | a `NEXT` texmap is armed for one line                          | False          |
| `texmap_fallback`| inside a `FALLBACK` section (ignore its geometry)              | False          |
| `texmaps`        | stack of saved outer texmap states (for nesting)               | empty          |
| `pe_tex_paths`   | pending Stud.io PE_TEX projectors, keyed by target subfile idx | empty          |

Per-**file** cursors (reset at the top of each `load`, never inherited):
`local_cull`, `winding`, `invert_next`, `current_pe_tex_path`, `next_shear`,
`subfile_index`.

---

## 8. The part/subpart boundary — where a new object begins

This is the single most important rule and the easiest to get wrong.

- Entering a file with `geometry_data == None` **and** `is_like_part(file)` starts
  a **new object**: allocate a `GeometryData`, and from here down pass it to all
  descendants. Subparts and primitives referenced beneath a part therefore have a
  non-None `geometry_data` on entry → they are **not** new objects; their faces
  merge into the part's mesh.
- Entering a file with `geometry_data == None` and `is_like_model(file)` is a
  **model**: it keeps its structure. Each child subfile becomes its own object
  (recurse with `geometry_data` still None); loose geometry directly in the model
  is hoisted ([§13](#13-model-loose-geometry-hoisting)).
- A **shortcut** is treated as a part: it collapses into a single object.

Consequences worth internalizing:

- The same file can be either an object or merged geometry depending on the
  context it is reached in — so the dedup key ([§14](#14-deduplication-keys))
  must **not** depend on placement, only on content.
- A primitive/subpart reached **directly from a model** is hoisted (it cannot
  stand alone); reached **from a part** it merges into that part.

---

## 9. BFC and winding

Back-Face Culling metadata (`0 BFC …`) determines each face's **vertex order**,
which in turn is the face's **normal direction** — normals are taken from this
winding and never recomputed, so getting it right is what makes them point outward
consistently.

### 9.1 The per-file BFC cursor

`meta_bfc` updates four values as `0 BFC …` lines are encountered. `matrix` is
the current placement (`child_matrix`); `accum_invert` is the inherited parity.

```
function meta_bfc(line, matrix, local_cull, winding, invert_next, accum_invert, bfc_certified):
    params = tokens(line) after "0 BFC"

    # Certification (only while not already de-certified):
    if bfc_certified != False:
        if bfc_certified == None and "NOCERTIFY" not in params: bfc_certified = True
        if "CERTIFY"   in params: bfc_certified = True
        if "NOCERTIFY" in params: bfc_certified = False
        if determinant(matrix) == 0: bfc_certified = False   # degenerate ⇒ cannot cull

    # Clipping (culling on/off) — applies regardless of certification:
    if "CLIP"   in params: local_cull = True
    if "NOCLIP" in params: local_cull = False

    # Winding, with accumulated inversion folded in:
    if "CCW" in params: winding = (accum_invert ? "CW"  : "CCW")
    if "CW"  in params: winding = (accum_invert ? "CCW" : "CW")

    if "INVERTNEXT" in params: invert_next = True

    # A mirrored (negative-determinant) placement flips winding, UNLESS an
    # explicit INVERTNEXT is already accounting for the flip (they cancel):
    if determinant(matrix) < 0 and not invert_next:
        winding = (winding == "CW" ? "CCW" : "CW")

    return (local_cull, winding, invert_next, bfc_certified)
```

Notes:

- A file's **first** `0 BFC` with no prior state and no `NOCERTIFY` implies
  `CERTIFY`. A file with **no** BFC lines stays `bfc_certified = None` (unknown).
- `CLIP`/`NOCLIP`/`CW`/`CCW`/`INVERTNEXT` and the determinant flip apply **even in
  a NOCERTIFY file** — they are outside the certification guard.

### 9.2 Winding normalization at face collection

Every triangle/quad is stored in a **canonical CCW order**. When the effective
`winding` is `"CW"`, reverse the vertex order:

```
function collect_face(buffer, node, matrix, color, winding, state, invert_next):
    verts = copy(node.vertices)
    if node.meta_command in {3,4} and winding == "CW":
        verts = reverse_face(verts)          # tri: [0,2,1]; quad: [0,3,2,1]
    face = FaceData(verts, color,
                    winding  = winding,
                    inverted = state.accum_invert XOR invert_next,   # PE_TEX only
                    texmap   = state.texmap,
                    pe_tex_path = state.pe_tex_path)
    buffer.append_to_right_list(node.meta_command, face)   # 2→edges,3/4→faces,5→lines
    face.matrix = matrix                       # applied in face.process()
    return face
```

- `reverse_face` swaps to make a CW-authored face CCW, so **all stored faces are
  CCW** and produce outward normals.
- `inverted` records BFC parity for **PE_TEX projection seeding only** ([§12](#12-the-pe_tex-state-machine-studio));
  it does not affect the winding reversal, which already folded `accum_invert`
  into `winding` via `meta_bfc`.
- Winding is normalized **unconditionally** — every CW face is reversed to CCW,
  whether or not culling is active — which keeps mirrored geometry's normals
  consistent.

### 9.3 `face.process()`

At part close, every collected face is processed:

```
face.process():
    face.vertices = [face.matrix @ v for v in face.vertices]   # to part-local space
    if node.meta_command == 4: fix_bowtie(face.vertices)       # repair self-crossing quads
    if face.pe_tex_path: face.pe_texmaps = build_explicit_uv_texmaps(...)  # §12
```

> **Bow-tie repair is an expensive step.** `fix_bowtie` runs on every quad (type-4
> line): it computes three edge cross-products to detect a self-crossing
> "bow-tie" quad and swaps two vertices to undo it. Because it touches every quad
> in the model — the hot path — it is a meaningful cost; a performance-sensitive
> port may batch or skip it, accepting the occasional folded quad.

---

## 10. Color resolution

LDraw color codes are strings. Two are special and **inherit**:

- **16** — "main" color: use the color passed down from the parent.
- **24** — "edge/complement" color: use the parent's edge color (handled in the
  material layer, not the geometry layer).

The geometry layer resolves 16 only:

```
function determine_color(parent_color, this_color):
    return (this_color == "16") ? parent_color : this_color
```

So a part referenced with color `4` (red) renders its `16` faces red; a stud
inside it referenced as `16` stays red; a face hard-coded `1` (blue) is blue
regardless. Concrete codes (0–511, plus direct `0x2RRGGBB` colors) map to
materials in `sink.material(...)`.

---

## 11. The `!TEXMAP` state machine

`!TEXMAP` is the official texture spec. A `START`/`NEXT` line defines a
**projector** (planar, cylindrical, or spherical) and an image; following
geometry lines receive projected UVs until the texture ends.

Projector parameters (after the method keyword) are points in the **current
placement frame** — transform them by `child_matrix` when parsing:

- **PLANAR** — 3 points (origin, U-axis end, V-axis end).
- **CYLINDRICAL** — 3 points + 1 angle.
- **SPHERICAL** — 3 points + 2 angles.

State transitions (`meta_texmap`):

```
"0 !TEXMAP START <method> <pts> <image> [glossmap]"
        push current (texmap, texmap_start, texmap_fallback) if a texmap is active
        texmap = new projector;  texmap_start = True;  texmap_fallback = False
"0 !TEXMAP NEXT  <method> <pts> <image>"
        (as START but) texmap_next = True   # applies to exactly ONE following line
"0 !TEXMAP FALLBACK"
        texmap_fallback = True               # ignore geometry until END (it's for
                                             # non-texmap renderers)
"0 !TEXMAP END"
        pop the saved outer state, or clear to (None,False,False); texmap_next=False
```

Ending rules the loop enforces:

- **NEXT** ends automatically after the next single `1..5` line (equivalent to a
  `START` immediately followed by `END` around that one line).
- **STEP** ends any active texture and clears the whole nesting stack.
- **FALLBACK…END** geometry is skipped entirely (the `cmd in {1..5} and not
  texmap_fallback` guard in [§6](#6-phase-2--the-traversal-load)).

A face that carries a projector gets its UVs computed at mesh-assembly time by
projecting each vertex through the projector's inverse and reading off the U/V
percentages. Type-3 lines may also carry **explicit** UVs in the file (6 trailing
floats), which bypass projection.

---

## 12. The `PE_TEX` state machine (Stud.io)

`PE_TEX_*` is Stud.io / Part Designer's private texture format (never published;
its semantics are reverse-engineered). It coexists with `!TEXMAP` and is threaded
through the traversal via `pe_tex_paths`.

Three line kinds, parsed in order within a file:

```
"0 PE_TEX_PATH <idx…>"     start a projector aimed at a target subfile path
                           (idx = which "1" line(s) it descends into; -1 = "this file")
"0 PE_TEX_NEXT_SHEAR"      mark the NEXT PE_TEX_INFO's box as shear-calibrated
"0 PE_TEX_INFO <b64>"                       image only → attach to current path
"0 PE_TEX_INFO <12+4 floats> <b64>"         box: 3×4 projection matrix + 2 corner
                                            points defining a stamp box + image
```

Per-file cursors: `current_pe_tex_path` (the projector being built) and
`next_shear` (consumed by the next `INFO`). A bare `INFO` with no preceding
`PATH` targets path `-1` ("this file"). Completed projectors are filed into
`pe_tex_paths`:

- target `-1` → the `None` slot (applies to this file's own faces);
- target `k ≥ 0` → keyed by subfile index `k` (applies down a specific `1` line).

### Descent into subfiles

When recursing into the `i`-th `1` line, build the child's `pe_tex_paths`:

- the parent's `None`-slot projector **descends**: rebase its box into the child's
  local frame via the child's matrix (`descend_tex_info`), so a stamp aimed at a
  parent surface follows the geometry down to wherever the real faces live;
- any path keyed exactly `i` is handed down; if its remaining path has length 1 it
  becomes the child's `None` slot, otherwise its head index is popped and it is
  re-filed by its next index.

### Two projection modes

- **Explicit-UV** `INFO` (image only): resolved **per face** at `face.process()`
  via `build_explicit_uv_texmaps` using the face's own UVs.
- **Box** `INFO` (16 floats): resolved **once per mesh**, after all faces are
  collected, by `geometry_data.project_pe_texmaps()`. This seeds the faces the
  stamp box intersects and **flood-fills** across connected faces (shared-vertex
  adjacency), so a decal follows a curved/concave surface. The `inverted` flag
  from BFC ([§9](#92-winding-normalization-at-face-collection)) sets the seed
  normal direction.

The exact projection math (box → UV, shear recombination, flood-fill criteria) is
a self-contained subsystem and is out of scope for this loop specification;
implement it against the Part Designer behavior and the LDraw `!TEXMAP` spec.

---

## 13. Model loose-geometry hoisting

A model file keeps its structure — each referenced part is its own object — but a
model may also contain **loose geometry**: direct `2/3/4/5` lines, or `1`
references to bare primitive/subpart files (which cannot stand alone). Those are
collected into a single synthetic object:

- During the child loop, when `geometry_data is None` (model level) and the line
  is loose geometry (`hoist` is true in [§6](#6-phase-2--the-traversal-load)),
  route its faces into a `model_geometry` buffer, collected in **model-local
  space** (identity matrix) so instances of the model share it.
- After the loop, if `model_geometry` is non-empty, emit it as a part-like object
  named `"<model>:geometry"`, content-keyed and cached like any part, placed with
  the model's own transform (`child_matrix @ ROOT_CONV_INV`).

This mirrors Part Designer moving a model's loose geometry into a synthetic child
part. Without it, loose lines in a model would either be lost or wrongly merge the
whole model subtree into one mesh.

---

## 14. Deduplication keys

Two placements of the same part in the same color must share one mesh. The key
must therefore capture **everything that changes the geometry or UV output, by
content**, and **nothing about placement**:

```
key = filename
    + effective_color_code
    + (if texmap:  method, image, glossmap, and every projector parameter)
    + (for each pending PE_TEX path, in a deterministic order:
         target index, the path indices, and for each tex_info:
         image name, shear flag, projection matrix, and box corner points)
```

Rules:

- **Color is part of the key** because faces resolve color 16 at collection time,
  so a red instance and a blue instance are genuinely different meshes — each is
  built and shared under its own key.
- **Texmap/PE_TEX parameters are in the key**, not just the image name: the same
  image projected from two different boxes is two different meshes.
- Serialize to a stable string; if it exceeds the engine's mesh-name limit, map
  it through a `long-key → uuid` table so names stay unique and stable within a
  run.
- Round matrices before keying (e.g. 6 decimals) so float noise from otherwise
  identical placements doesn't split the cache.

---

## 15. Mesh assembly and post-processing

`sink.realize_mesh(key, geometry_data, color)` turns collected geometry into an
engine mesh. Build once per key; return the cache on repeat. Steps:

1. **Faces.** For each `face_data`, add its vertices and a face; assign a material
   from `sink.material(color, bfc_certified, slopes, texmap, pe_texmaps)` (resolve
   color 16/24 per face first); shade the face **smooth**; attach UVs from
   `texmap`/`pe_texmaps`.
2. **Weld.** Merge coincident vertices within a small distance (0.05 LDU) so
   shared corners connect. Do this **after** faces are added so adjacency forms.
3. **Normals.** Keep the authored winding from BFC ([§9](#9-bfc-and-winding)); the
   pipeline does not recompute normals.
4. **Sharp edges.** Type-2 lines mark **hard** edges: find mesh edges whose two
   endpoints sit near a type-2 line's endpoints (a KD-tree proximity match) and
   flag them sharp, so shading splits there (an edge-split on the object). Type-5
   optional lines are parsed but unused for surface meshing.
5. **Bake axis + scale.** Transform the mesh by `ROOT_CONV` ([§2](#2-coordinate-system-units-and-the-matrix-convention))
   and by the import-scale matrix (0.02).

At object emission the mesh — already axis-baked and scaled — is placed by the
object's placement matrix from [§6](#6-phase-2--the-traversal-load).

---

## 16. Implementation order

The canonical pipeline in dependency order — each stage builds on the previous. A
model is recognizably correct after stage 6 and matches the reference output after
stage 9.

1. **Parser** — line types `0/1/2/3/4/5`, MPD `0 FILE` splitting, subfile
   resolution, aggressive file caching ([§4](#4-phase-1--parsing)).
2. **Classification** — `part_type` and the `is_like_part` / `is_like_model` /
   `is_geometry` predicates ([§4.3](#43-file-classification-part_type)).
3. **Traversal** — the recursive walk, the transform chain, and the
   `geometry_data is None` object-boundary rule ([§6](#6-phase-2--the-traversal-load), [§8](#8-the-partsubpart-boundary--where-a-new-object-begins)).
4. **Color** — color-16 inheritance ([§10](#10-color-resolution)) and a
   color→material map.
5. **Dedup + placement** — content-keyed mesh sharing ([§14](#14-deduplication-keys)),
   the axis conversion, and import scale ([§2](#2-coordinate-system-units-and-the-matrix-convention)).
6. **BFC winding** — vertex-order normalization for correct normals ([§9](#9-bfc-and-winding)).
7. **Mesh finish** — vertex welding, hard-edge marking from type-2 lines, smooth
   shading, and bow-tie repair ([§15](#15-mesh-assembly-and-post-processing)).
8. **Loose-geometry hoisting** — synthetic `<model>:geometry` objects ([§13](#13-model-loose-geometry-hoisting)).
9. **Textures** — `!TEXMAP` projection ([§11](#11-the-texmap-state-machine)) and
   `PE_TEX` decals ([§12](#12-the-pe_tex-state-machine-studio)); the most involved
   stage, and the reason texmap state is threaded through the entire traversal.

Stages 1–6 yield a correctly shaped and colored model; 7–9 add the edges and
decals that bring it to full fidelity.
