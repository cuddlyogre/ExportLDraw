# Sticking Flat Pictures onto 3D Bricks

### The math behind LDraw `!TEXMAP` and Stud.io `PE_TEX`, explained from scratch

This guide explains how a flat PNG image ends up wrapped around a 3D LEGO part —
the minifig face on a head, the control panel on a slope, the logo on a torso.
It assumes no comfort with high school math. Every idea is built up from zero,
with real numbers you can check on a calculator.

There are two systems to cover:

1. **`!TEXMAP`** — the official LDraw texture spec. The part file describes a
   *projector* (flat, cylinder-shaped, or sphere-shaped), and the renderer does
   the math to figure out which spot of the picture lands on each corner.
2. **`PE_TEX`** — Stud.io / Part Designer's private format (never published;
   everything known about it comes from reverse-engineering Part Designer).
   It either writes the answers directly into the file, or describes an
   invisible *stamp box* that presses the picture onto whatever it touches.

Both systems exist to answer exactly one question, over and over:

> **For this corner of this triangle, which spot of the picture goes here?**

Everything below is just different ways of computing that answer.

---

## 1. The picture's address system: U and V

A picture on disk is a grid of colored dots (pixels). We need a way to point at
a spot on it. We could count pixels ("column 512, row 348"), but then everything
would break if someone saved the picture at a different resolution.

So instead, graphics people use **percentages**.

- **U** is how far *across* the picture you are: `0` = left edge, `1` = right
  edge, `0.5` = halfway.
- **V** is how far *up or down* you are: `0` at one edge, `1` at the other.

That's all U and V are: **two percentages, written as decimals.** The point
`(U, V) = (0.25, 0.5)` means "a quarter of the way across, halfway up." It
doesn't matter if the image is 64×64 or 2048×2048 — the address still works.

Every corner of every textured triangle ends up with one `(U, V)` pair. The
graphics card takes it from there, smoothly blending the picture across the
triangle between the corners.

**One annoying detail we'll hit twice:** image files traditionally count rows
from the **top** (like reading a page), while Blender counts from the
**bottom** (like a graph in math class). So when this add-on hands UVs to
Blender it sometimes has to flip: `v_blender = 1 − v_file`. It's not deep —
it's the same reason page 1 of a book is at the top of the stack.

---

## 2. The toolbox — three ideas that do almost all the work

You only need three math tools to understand `!TEXMAP`'s planar mode and most
of `PE_TEX`. Two more small tools get added later for cylinders, spheres, and
stamp boxes.

### 2.1 Points and arrows (vectors)

A **point** is a location in 3D space, written as three numbers `(x, y, z)` —
think of it as a street address: how far east, how far up, how far north.
(In LDraw files, the y-axis actually points *down*, which is a historical
quirk. It changes nothing about the ideas here.)

An **arrow** (the math word is *vector*) is the difference between two points:
which direction, and how far. You get one by subtracting:

```
arrow from A to B  =  B − A     (subtract each number separately)

A = (10, 0, 5)
B = (40, 0, 5)
arrow = (40−10, 0−0, 5−5) = (30, 0, 0)     "30 units east"
```

### 2.2 Length of an arrow

How long is the arrow `(30, 0, 40)`? You use the diagonal-shortcut rule
(Pythagoras), extended to 3D:

```
length = √(x² + y² + z²)
       = √(30² + 0² + 40²)
       = √(900 + 0 + 1600)
       = √2500 = 50
```

One special trick: if you take an arrow and shrink it so its length is exactly
1, you get a **pure direction** — like a compass needle. All it says is "that
way." You make one by dividing each number by the length. These are called
*unit vectors*, and they matter because of the next tool.

### 2.3 The dot product — the "how far along?" tool

This is the workhorse of all texture math, so take it slowly.

The **dot product** of two arrows is a single number. Computing it is easy:
multiply the matching parts, add them up.

```
(a, b, c) · (d, e, f)  =  a×d + b×e + c×f
```

The magic is what that number *means*. If one of the arrows is a pure
direction (length 1), then the dot product answers:

> **"How far does the other arrow reach *in that direction*?"**

Think of it as a shadow. Shine a light from the side, and the dot product is
the length of your arrow's shadow on the direction line.

Worked example. Direction = `(1, 0, 0)` ("east," length exactly 1). Your
position, measured from some corner point, is the arrow `(10, 20, 0)`:

```
(10, 20, 0) · (1, 0, 0) = 10×1 + 20×0 + 0×0 = 10
```

You are 10 units east of the corner — the 20 units of sideways travel don't
count, because they're not *in* that direction. That's the whole trick.

The dot product has a second superpower: its **sign** (plus or minus) tells you
whether two arrows point in generally the same or generally opposite
directions:

| dot product | meaning |
|---|---|
| positive | pointing the same general way |
| zero | perfectly sideways to each other (90°) |
| negative | pointing generally opposite ways |

Remember that — it's how the computer asks *"is this triangle facing the
projector, or facing away from it?"*

### 2.4 (For later) The cross product — "which way does this triangle face?"

Take two edges of a triangle, feed them to the **cross product**, and out comes
a new arrow that sticks straight out of the triangle's surface, like a flagpole
on flat ground. That arrow is called the **normal**, and it's the triangle's
facing direction. We won't compute one by hand — just remember: *cross product
of two edges = the direction the triangle is looking.*

Combined with tool 2.3: **`normal · projector_direction` positive means the
triangle is looking at the projector.** That one line of math decides which
faces of a part receive a decal.

### 2.5 (For later) Planes and "distance from a plane"

A **plane** is an infinite flat sheet — a wall with no edges. It's described by
one point that lies on it and one pure direction that points straight out of
it. The **distance from a point to a plane** is measured straight toward the
sheet — and it's computed with, you guessed it, a dot product:

```
distance = (your position − point on plane) · plane's facing direction
```

It's just the shadow trick again: "how far do I stick out from the wall?"
This distance can be *negative*, which simply means you're on the back side of
the wall. That turns out to be useful, not a problem.

---

## 3. `!TEXMAP` method one: PLANAR — the slide projector

The file line looks like this (simplified):

```
0 !TEXMAP START PLANAR  x1 y1 z1  x2 y2 z2  x3 y3 z3  picture.png
```

Those are three **points in 3D space**, and they are three corners of the
picture as it hangs in the air in front of the part:

```
        p1 ────────────── p2
        │                     p1 = the picture's origin corner
        │                     p1→p2 = the direction "across the picture" (U)
        │                     p1→p3 = the direction "down the picture" (V)
        p3
```

Imagine a slide projector infinitely far away, shining the picture straight at
the part. Every point on the part gets hit by exactly one spot of the picture.
The math to find that spot:

> **U** = (how far your point is from the plane through p1 that faces along
> p1→p2) ÷ (length of p1→p2)
>
> **V** = the same thing using p1→p3

That sounds like a mouthful, but with tool 2.5 it's two shadow measurements
and two divisions. Let's do one with real numbers.

**Worked example.** A flat 40×40 wall panel. The file says:

```
p1 = (0, 0, 0)      the picture's top-left corner
p2 = (40, 0, 0)     40 units east  → the picture is 40 wide
p3 = (0, 40, 0)     40 units down  → the picture is 40 tall
```

Question: a triangle corner sits at the point `(10, 20, 0)`. Where on the
picture is it?

Step 1 — arrows for the picture edges:

```
across = p2 − p1 = (40, 0, 0), length 40 → direction (1, 0, 0)
down   = p3 − p1 = (0, 40, 0), length 40 → direction (0, 1, 0)
```

Step 2 — shadow measurements (dot products) from p1:

```
position from p1 = (10, 20, 0)
along "across":  (10,20,0) · (1,0,0) = 10
along "down":    (10,20,0) · (0,1,0) = 20
```

Step 3 — turn into percentages:

```
U = 10 ÷ 40 = 0.25    (a quarter of the way across)
V = 20 ÷ 40 = 0.5     (halfway down)
```

Done. That corner wears the spot a quarter across, halfway down the picture.
That's genuinely all of planar mapping: **two shadows, two divisions.**
(In this add-on it's `__map_planar` in `texmap.py` — the code is a direct
transcription of those three steps, plus the top-vs-bottom flip from
section 1.)

**What if the answer comes out below 0 or above 1?** Then that part of the
surface lies outside the picture. The picture is *not* repeated like bathroom
tiles — the surface just shows its ordinary plastic color, as if the projector
beam simply ends at the slide's edge.

---

## 4. `!TEXMAP` method two: CYLINDRICAL — the soup-can label

Some parts are round, and a flat projector would smear a picture across a
curved surface (the sides would get stretched). For those, the spec wraps the
picture around like the **label on a soup can**.

The file gives:

```
p1 = center of the can's bottom
p2 = center of the can's top
p3 = a point on the bottom rim where the CENTER of the label sits
a  = how many degrees of the can the label covers (360 = all the way around)
```

Two new small ideas, then the formulas.

**Angles.** Stand at the can's axis and look toward p3 — call that the "front."
Any other point on the can sits some number of degrees to the left (negative)
or right (positive) of front. Computers get this angle from a function called
`atan2`: you hand it "how far forward" and "how far sideways" (two dot products
against two perpendicular directions — the shadow trick twice), and it hands
back the angle. Think of it as reading where a clock hand points.

```
     view from above the can:

            back (±180°)
              ·  ·  ·
          ·             ·
        ·      p1 ·       ·      p1 = the axis, seen end-on
          ·             ·
              ·  ·  ·
            front (0°)  ← direction of p3, center of the label
```

**U from the angle.** The label's center touches the front, so front = the
middle of the picture = 50%. Going right adds, going left subtracts, and the
whole label spans `a` degrees:

```
U = 0.5 + (angle ÷ a)
```

Worked example: the label covers the whole can (`a = 360`). A point 90° to the
right of front:

```
U = 0.5 + 90/360 = 0.5 + 0.25 = 0.75      (three quarters across the label)
```

A point at the very back (180°) gives `0.5 + 0.5 = 1.0` — the right edge of the
label. The same physical spot approached from the left gives `0.5 − 0.5 = 0.0`
— the left edge. Same place, two names. That line down the back is the
**seam**, exactly like the glue line on a real can label. Triangles that
straddle the seam need special care (one corner says "0.99," the next says
"0.01," and naively blending between those would smear the entire label
backwards across the gap). The importer detects this and nudges the numbers so
they count continuously — e.g. `0.99 → 1.01` — and the picture is allowed to
wrap around for full-circle labels.

**V from the height.** This one's easy — it's the planar math again, along the
can's axis:

```
V = (height above the bottom) ÷ (height of the can)
```

A point 15 units up a 24-unit-tall can: `V = 15/24 = 0.625`. (The "height
above the bottom" is — once more — a dot product: the shadow of your position
on the axis direction.)

So cylindrical mapping is: **one clock reading for U, one shadow for V.**

---

## 5. `!TEXMAP` method three: SPHERICAL — the globe

For ball-shaped surfaces the spec wraps the picture the way a map wraps a
globe. If you've ever heard "latitude and longitude," you already know this
one.

The file gives:

```
p1 = center of the sphere
p2 = the point on the sphere where the CENTER of the picture touches
p3 = a helper point that pins down which way is "sideways"
a  = how many degrees the picture spans left-to-right
b  = how many degrees it spans up-and-down
```

- **U comes from longitude**: how many degrees east or west of the picture's
  center you are, divided by `a`, offset from the middle:
  `U = 0.5 + longitude ÷ a`
- **V comes from latitude**: how many degrees north or south of the picture's
  center, divided by `b`: `V = 0.5 + latitude ÷ b` (plus the usual row-order
  flip).

Longitude is measured with the same clock-reading trick as the cylinder.
Latitude is measured with the shadow trick: how far the point sticks out above
the sphere's "equator plane," compared to its distance from the center — that
ratio pins the angle. (The code uses `asin`, the calculator button that turns
that ratio back into degrees.)

Worked example: picture spans `a = 180°, b = 90°`. A point 45° east and 15°
north of the picture's center:

```
U = 0.5 + 45/180 = 0.75
V = 0.5 + 15/90  = 0.667  (before the row flip)
```

**The pole problem.** On a real globe, all the longitude lines crash together
at the North Pole — "which longitude is the pole at?" has no answer. The math
has the same problem: at the pole, the clock reading is undefined (the point is
*on* the axis, so there is no "sideways"). Triangles that touch a pole would
get a garbage U and smear half the picture into a pinwheel. The importer
special-cases them: a pole corner just borrows the average U of its triangle's
other corners, which keeps the picture converging neatly, like orange
segments meeting at the stem.

---

## 6. `PE_TEX` flavor one: the answers are just written down

Stud.io's simplest mode does no projection math at all. Look at a normal
triangle line, then a Stud.io textured one:

```
3 16  x1 y1 z1  x2 y2 z2  x3 y3 z3                      ← normal: 3 corners
3 16  x1 y1 z1  x2 y2 z2  x3 y3 z3  u1 v1  u2 v2  u3 v3 ← textured: +6 numbers
```

Those six extra numbers are three ready-made `(U, V)` pairs — one per corner.
Part Designer did the projection math *once*, when the part author placed the
decal, and saved the answers into the file. The picture itself travels inside
the file too, as a block of base64 text (a way of writing binary data using
only letters and numbers) on a `PE_TEX_INFO` line.

For the importer this is the easy case: read six numbers, hand them to
Blender. No projectors, no shadows, no clocks.

---

## 7. `PE_TEX` flavor two: the stamp box

The interesting mode. The file line carries 16 numbers plus the picture:

```
0 PE_TEX_INFO  m1 … m12   minX minY   maxX maxY   <base64 picture>
```

The mental model: an invisible **rubber stamp** — a box, usually very thin,
like a stamp pad hovering just above the part's surface — that presses the
picture onto everything it touches.

### 7.1 Twelve numbers = a recorded set of instructions (a matrix)

The stamp starts life as a plain 1×1×1 cube sitting at the origin. The twelve
numbers are a **matrix** — which sounds scary but is just a *saved recipe*:

- three of the numbers say **where the cube's center was carried** to,
- the other nine say **where its three edges ended up pointing, and how long
  they were stretched** (e.g. "the edge that pointed east now points northeast
  and is 40 long").

"Applying the matrix to a point" = following the recipe. And every recipe can
be run **backwards** — that's called the *inverse* matrix. Backwards is what we
actually want, because the useful question is:

> "Never mind where the stamp went — where is this triangle corner, *as seen
> from inside the stamp*?"

Run every corner through the recipe backwards, and now all positions are
measured in cozy stamp-space, where the stamp is just a plain box straddling
the origin: it reaches half a unit each way (±0.5 wide, ±0.5 deep, ±0.5 tall —
scaled by however much the recipe stretched each edge). The picture shines
through the box from one fixed side (its "down" direction in stamp space).

### 7.2 Test one: is the face looking at the stamp?

Section 2.4's trick, verbatim: take the triangle's two edges (in stamp space),
cross product → facing direction, dot product against the stamp's shine
direction:

- **positive → the face is looking at the stamp** → it can receive the decal
- negative → it's facing away (an inside wall, the far side of the part) → skip

The code actually tests `dot ≥ 0.001` rather than `> 0`. Why not exactly zero?
Because computers store decimals with tiny rounding errors — a face that's
mathematically *exactly* sideways might compute as 0.0000003 or −0.0000003 at
random. The `0.001` is a small cushion against that fuzz.

*(A wrinkle: LDraw parts sometimes contain deliberately inside-out geometry —
a `BFC INVERTNEXT` line marks a piece as flipped, e.g. a cylinder used as a
hole. For those, the importer flips the computed facing before the test,
otherwise the decal would stick to the hollow underside of studs.)*

### 7.3 Test two: does the triangle actually touch the box?

Facing the stamp isn't enough — a face on the far end of the brick shouldn't
get stamped. So there's a touching test between each triangle and the box.

The idea behind it is lovely and needs no formulas: **try to slide a flat
sheet of cardboard between the triangle and the box.** If there is *any*
angle at which the sheet fits cleanly between them, they don't touch. If no
sheet fits anywhere, they must be overlapping. Mathematicians proved you don't
have to try every possible angle — for a triangle and a box, checking **13
specific sheet orientations** is enough (the box's 3 face directions, the
triangle's own plane, and 9 combinations of their edges). The code checks all
13; each check is a handful of dot products (shadows again — "does the
triangle's shadow overlap the box's shadow along this direction?").

This is why the stamp box is deliberately **thin**: a thin pad touches only
the surface it hovers over, and can't reach through the part and stamp the
inside of the opposite wall.

### 7.4 The paint spreads: flood fill

Here's the clever part. Decals often lap over gently curved surfaces — think
of a skirt or a curved slope where the printed area bends away from the stamp.
The bent-away triangles *fail* the touching test (the thin box doesn't reach
them), but they should still carry the decal.

So after stamping the directly-touched triangles, the decal **spreads like a
drop of food coloring**: from every stamped triangle to any neighbor sharing a
corner, and from those to *their* neighbors, and so on — with one rule:

> the color refuses to spread onto any triangle that faces **away** from the
> stamp (dot product negative).

That single rule is the firewall. The decal can chase a curve as far as it
keeps generally facing the stamp, but the moment the surface turns its back —
the inside of the part, the far wall — the spreading stops dead. A decal can't
leak through a torso to the inside, because it would have to cross back-facing
triangles to get there, and it won't.

If a part has *several* decals, they take turns in file order, and a triangle
claimed by an earlier decal is off-limits to later ones — first come, first
served.

### 7.5 Finally: the U and V

Every stamped triangle corner already has its stamp-space position (from
running the recipe backwards in 7.1). The last four plain numbers on the line
— `minX minY maxX maxY` — say which rectangle of stamp space corresponds to the
picture's 0%–100%. Then it's exactly the percentage math from planar mapping:

```
U = (corner's stamp-space x − minX) ÷ (maxX − minX)
```

**Worked example:** `minX = −20, maxX = 20`, and a corner sits at stamp-space
`x = 10`:

```
U = (10 − (−20)) ÷ (20 − (−20)) = 30 ÷ 40 = 0.75
```

V is the same computation along the box's other footprint direction (with a
sign flip for picture row order). Corners of flood-filled triangles that hang
past the picture's edge simply get U or V outside 0–1, and — same as
`!TEXMAP` — those areas show plain plastic color rather than repeating the
picture.

### 7.6 One extra: `PE_TEX_NEXT_SHEAR` in one paragraph

Occasionally a decal target is placed with a *shear* — a transform that tilts
a rectangle into a parallelogram, like pushing sideways on the top of a deck of
cards. Part Designer stores the stamp recipe for such parts in a specially
pre-tilted form and marks it with `0 PE_TEX_NEXT_SHEAR`, meaning: "this recipe
only becomes a proper right-angled box after it's recombined with the tilted
part placement." The importer's job is simply *not* to undo that tilt at the
wrong moment. It's bookkeeping about *when* to apply which recipe, not new
math.

---

## 8. The whole story on one page

| | `!TEXMAP` PLANAR | `!TEXMAP` CYLINDRICAL | `!TEXMAP` SPHERICAL | `PE_TEX` explicit | `PE_TEX` stamp box |
|---|---|---|---|---|---|
| Mental picture | slide projector | soup-can label | map on a globe | answers pre-written | rubber stamp |
| What the file gives | 3 corner points | axis, rim point, span `a` | center, touch point, spans `a, b` | 6 numbers per triangle | recipe (matrix) + picture rectangle |
| U comes from | shadow ÷ width | clock angle ÷ `a`, from 50% | longitude ÷ `a`, from 50% | already written | shadow ÷ width, in stamp space |
| V comes from | shadow ÷ height | height ÷ can height | latitude ÷ `b`, from 50% | already written | shadow ÷ height, in stamp space |
| Which faces | everything until `!TEXMAP END` | same | same | triangles that carry UVs | facing + touching + spreading |
| Off the picture's edge | plain plastic color | seam wraps for 360° labels | poles pinch neatly | n/a | plain plastic color |

Strip away the vocabulary, and the two specs are close cousins. Both end at
the same finish line — a `(U, V)` percentage pair per corner — and both lean on
the same three moves: **subtract points to get arrows, dot products to measure
shadows and check facing, divide to get percentages.** Everything else is
stagecraft about where the projector sits.

---

## 9. Tiny glossary

| word | plain meaning |
|---|---|
| UV | a spot on a picture, written as two percentages (0–1) |
| vector | an arrow: a direction plus a distance |
| unit vector | an arrow shrunk to length 1 — a pure direction |
| dot product | multiply matching parts and add; measures "how far along a direction" (a shadow), and its +/− sign says same-way vs opposite-way |
| cross product | feed it two triangle edges, get the direction the triangle faces |
| normal | that facing direction |
| plane | an infinite flat sheet; distance to it is a dot product |
| matrix | a saved recipe of move/rotate/stretch; 12 meaningful numbers |
| inverse matrix | the same recipe run backwards |
| `atan2` | the "read the clock hand" function: forward + sideways in, angle out |
| `asin` | turns a ratio back into an angle (used for latitude) |
| seam | where a wrapped picture's left and right edges meet (the glue line) |
| flood fill | spreading to neighbors, step by step, under a rule |
| base64 | binary data (like a PNG) written out as ordinary text |

---

## 10. Where this lives in the add-on

- `texmap.py` — the three `!TEXMAP` projections: `__map_planar`,
  `__map_cylindrical`, `__map_spherical`, including the seam and pole fixes.
- `ldraw_meta.py` → `meta_texmap` — parses the `!TEXMAP` lines (the three
  points, spans, filenames).
- `ldraw_node.py` — parses `PE_TEX_PATH` / `PE_TEX_INFO` / `PE_TEX_NEXT_SHEAR`
  (the stamp recipe and picture).
- `pe_texmap.py` → `project_box_texmaps` — the stamp box: facing test,
  13-sheet touching test (`intersect`), flood fill, and the final percentage
  math.
- `geometry_data.py` — carries each face's vertices, transform, and
  inside-out flag to the projector.
