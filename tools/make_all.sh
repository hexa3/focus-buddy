#!/usr/bin/env bash
# Rebuild every hardware output from tools/netlist.py.
# Needs docker. Runs at low priority with capped CPU/RAM so the machine stays usable.
#
#   tools/make_all.sh          -> PCB, schematic, DRC/ERC, Gerbers, STLs, renders, BOM
set -euo pipefail
cd "$(dirname "$0")/.."
LIM=(--cpus 1 --memory 2g)
KI=(nice -n 19 docker run --rm "${LIM[@]}" -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/w" -w /w kicad/kicad:9.0)
SCAD=(nice -n 19 docker run --rm "${LIM[@]}" -u "$(id -u):$(id -g)" -v "$PWD/hardware/cad:/w" -w /w openscad/openscad:2021.01)
PCB=hardware/pcb
OUT=hardware/fab
mkdir -p "$OUT/gerbers"

echo "== PCB: place"
"${KI[@]}" python3 tools/build_pcb.py place $PCB | grep -E "saved|rotation"
echo "== PCB: route (tools/route_pcb.py)"
"${KI[@]}" python3 tools/route_pcb.py $PCB/focus-buddy.kicad_pcb | grep -E "attempt|tracks"
echo "== PCB: ground pour"
"${KI[@]}" python3 tools/build_pcb.py finish $PCB | grep -E "finished"
echo "== schematic"
"${KI[@]}" python3 tools/build_schematic.py $PCB | grep wrote
"${KI[@]}" kicad-cli sch erc -o $PCB/erc.rpt $PCB/focus-buddy.kicad_sch | grep -o "Found.*" || true
"${KI[@]}" kicad-cli sch export pdf -o $OUT/focus-buddy-schematic.pdf $PCB/focus-buddy.kicad_sch >/dev/null
echo "== DRC (+ schematic parity)"
"${KI[@]}" kicad-cli pcb drc --schematic-parity -o $PCB/drc.rpt $PCB/focus-buddy.kicad_pcb | grep -E "Found" || true

echo "== fabrication files"
rm -f $OUT/gerbers/*
"${KI[@]}" kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask --use-drill-file-origin -o $OUT/gerbers/ $PCB/focus-buddy.kicad_pcb >/dev/null
"${KI[@]}" kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 \
  -o $OUT/gerbers/ $PCB/focus-buddy.kicad_pcb >/dev/null
(cd $OUT/gerbers && rm -f ../focus-buddy-gerbers.zip && zip -q ../focus-buddy-gerbers.zip ./*)
"${KI[@]}" kicad-cli pcb export pos --format csv --units mm -o $OUT/focus-buddy-positions.csv $PCB/focus-buddy.kicad_pcb >/dev/null
"${KI[@]}" kicad-cli pcb export step --subst-models --force -o $OUT/focus-buddy-pcb.step $PCB/focus-buddy.kicad_pcb >/dev/null 2>&1 || echo "(STEP export skipped)"
for side in top bottom; do
  "${KI[@]}" kicad-cli pcb render --side $side --width 1600 --height 1000 --quality basic --background opaque \
    -o $OUT/pcb-render-$side.png $PCB/focus-buddy.kicad_pcb >/dev/null 2>&1 || echo "(render $side skipped)"
done
python3 tools/gen_bom.py >/dev/null && cp hardware/BOM.csv $OUT/

echo "== enclosure STLs"
python3 tools/gen_cad_params.py >/dev/null
mkdir -p hardware/cad/stl
for p in front back caps stand; do
  "${SCAD[@]}" openscad -D "part=\"$p\"" -o stl/focus-buddy-$p.stl enclosure.scad 2>&1 | grep -iE "error" || true
done
ls -la $OUT $OUT/gerbers hardware/cad/stl
