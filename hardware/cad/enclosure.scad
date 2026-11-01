// Focus Buddy enclosure: OpenSCAD, fully parametric.
//
// Export each part:  openscad -D 'part="front"' -o front.stl enclosure.scad
// parts: "front" (front shell), "back" (back cover), "caps" (3 button caps),
//        "stand" (15-degree desk cradle), "assembly" (exploded preview, don't print)
//
// Frame: X right, Y up (seen from the front), Z = depth, 0 at the front face,
// growing toward the back. The front shell prints front-face down, no supports.

include <pcb_positions.scad>

part = "assembly";

/* [Display window: measure your module!] */
// Visible window. The Waveshare 2.9" active area is 66.9 x 29.1 mm; we show a bit of black border.
win_w = 70;
win_h = 31.5;
// Offset of the window from the module-board centre. Waveshare V2 glass is not
// centred on its PCB: measure from the board edge to the active area and adjust.
win_offset = [0, 0];

/* [Case] */
wall = 2.4;
front_t = 2.0;
gap = 1.0;              // clearance PCB edge to inner wall
shell_d = 28;           // front face to back rim
cover_t = 2.0;
corner_r = 6;
pcb_t = 1.6;
pcb_z = front_t + 12;   // PCB front face; leaves room for the display + its connector
boss_d = 7;
pilot_d = 2.5;          // M3 self-tapping into plastic (or 4.0 for M3 heat-set inserts)
screw_d = 3.4;
head_d = 6.2;

/* [Buttons] */
btn_hole_d = 7.6;
cap_stem_d = 7.0;
cap_flange_d = 10.5;
cap_flange_t = 2.0;
sw_height = 9.5;        // 6x6 tactile switch, overall height (H9.5)
cap_protrude = 1.5;

/* [USB-C] */
// XIAO on standard male headers: 2.5 mm plastic + 1 mm XIAO PCB + half the 3.2 mm receptacle
usb_z = pcb_z + pcb_t + 2.5 + 1.0 + 1.6;
usb_hole = [13.0, 7.5];

$fn = 48;
in_w = pcb_w + 2 * gap;
in_h = pcb_h + 2 * gap;
out_w = in_w + 2 * wall;
out_h = in_h + 2 * wall;
eps = 0.01;

module rrect(w, h, r, z) {
  linear_extrude(z) offset(r) offset(-r) square([w, h], center = true);
}

// ----------------------------------------------------------------- front shell
module corner_brackets() {
  mw = display_module[0] + 0.6;
  mh = display_module[1] + 0.6;
  t = 1.2; leg = 9; hgt = 3;
  translate([pcb_display_center[0], pcb_display_center[1], front_t - eps])
    for (sx = [-1, 1], sy = [-1, 1]) {
      // horizontal leg
      translate([sx > 0 ? mw / 2 - leg + t : -mw / 2 - t, sy > 0 ? mh / 2 : -mh / 2 - t, 0])
        cube([leg, t, hgt]);
      // vertical leg
      translate([sx > 0 ? mw / 2 : -mw / 2 - t, sy > 0 ? mh / 2 - leg + t : -mh / 2 - t, 0])
        cube([t, leg, hgt]);
    }
}

module front_shell() {
  difference() {
    union() {
      difference() {
        rrect(out_w, out_h, corner_r, shell_d);
        translate([0, 0, front_t]) rrect(in_w, in_h, corner_r - wall, shell_d);
      }
      // PCB bosses
      for (h = pcb_holes) translate([h[0], h[1], front_t - eps]) cylinder(d = boss_d, h = pcb_z - front_t + eps);
      corner_brackets();
    }
    // display window, chamfered on the outside
    translate([pcb_display_center[0] + win_offset[0], pcb_display_center[1] + win_offset[1], -eps])
      hull() {
        linear_extrude(eps) offset(1.2) square([win_w, win_h], center = true);
        translate([0, 0, 1.2]) linear_extrude(front_t) square([win_w, win_h], center = true);
      }
    // button holes
    for (s = pcb_switches) translate([s[0], s[1], -eps]) cylinder(d = btn_hole_d, h = front_t + 2);
    // pilot holes (blind, they do not show on the front)
    for (h = pcb_holes) translate([h[0], h[1], 1.0]) cylinder(d = pilot_d, h = pcb_z);
    // USB-C on the right wall
    translate([out_w / 2 - wall - 1, pcb_xiao_center[1], usb_z]) rotate([0, 90, 0])
      linear_extrude(wall + 2) offset(2) offset(-2) square([usb_hole[1], usb_hole[0]], center = true);
    // label under the buttons
    translate([0, -out_h / 2 + 3.6, -eps]) linear_extrude(0.6)
      mirror([1, 0, 0]) text("focus buddy", size = 3.2, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
  }
}

// ----------------------------------------------------------------- back cover
module back_cover() {
  difference() {
    union() {
      translate([0, 0, shell_d]) rrect(out_w, out_h, corner_r, cover_t);
      // alignment lip that drops into the shell
      translate([0, 0, shell_d - 2]) difference() {
        rrect(in_w - 0.6, in_h - 0.6, corner_r - wall, 2 + eps);
        translate([0, 0, -1]) rrect(in_w - 3.0, in_h - 3.0, corner_r - wall - 1, 4);
      }
      // pillars that clamp the PCB against the front bosses
      for (h = pcb_holes) translate([h[0], h[1], pcb_z + pcb_t]) cylinder(d = boss_d, h = shell_d - pcb_z - pcb_t + eps);
    }
    for (h = pcb_holes) {
      translate([h[0], h[1], pcb_z]) cylinder(d = screw_d, h = shell_d + 10);
      translate([h[0], h[1], shell_d + cover_t - 3]) cylinder(d = head_d, h = 4);
    }
    // lip notch where the USB hole is
    translate([out_w / 2 - wall - 3, pcb_xiao_center[1] - usb_hole[0] / 2 - 1, shell_d - 3]) cube([4, usb_hole[0] + 2, 3]);
    // debossed label on the outside
    translate([0, -8, shell_d + cover_t - 0.6]) linear_extrude(1)
      text("FOCUS BUDDY", size = 6, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    translate([0, -17, shell_d + cover_t - 0.6]) linear_extrude(1)
      text("rev A  -  keep calm and focus", size = 3.2, halign = "center", valign = "center", font = "Liberation Sans");
  }
}

// ----------------------------------------------------------------- button cap
// printed flange-down. Flange sits behind the front wall, the stem pokes through.
cap_stem_len = (pcb_z - sw_height - cap_flange_t) + cap_protrude;
module button_cap() {
  cylinder(d = cap_flange_d, h = cap_flange_t);
  translate([0, 0, cap_flange_t - eps]) hull() {
    cylinder(d = cap_stem_d, h = cap_stem_len - 0.6);
    cylinder(d = cap_stem_d - 1.2, h = cap_stem_len);
  }
}

module caps() { for (i = [-1:1]) translate([i * 14, 0, 0]) button_cap(); }

// ----------------------------------------------------------------- stand
tilt = 15;
module device_box(cl = 0) {
  // whole closed device, bottom-front edge at the origin, front facing -Y, leaning back by `tilt`
  rotate([-tilt, 0, 0]) translate([-out_w / 2 - cl, -cl, -cl]) cube([out_w + 2 * cl, shell_d + cover_t + 2 * cl, out_h + 2 * cl]);
}
module stand() {
  d = shell_d + cover_t;
  floor_z = d * sin(tilt) + 3;
  lip = 7;
  difference() {
    hull() {
      translate([-35, 0, 0]) cube([70, lip + d * cos(tilt) + 10, 2]);
      translate([-35, 0, 0]) cube([70, 4, floor_z + 6]);
      translate([-35, lip + d * cos(tilt) - 2, 0]) cube([70, 12, floor_z + 10]);
    }
    translate([0, lip, floor_z]) device_box(0.4);
  }
}

// ----------------------------------------------------------------- previews
module pcb_preview() {
  color("darkgreen") translate([0, 0, pcb_z]) difference() {
    rrect(pcb_w, pcb_h, 3, pcb_t);
    for (h = pcb_holes) translate([h[0], h[1], -1]) cylinder(d = 3.2, h = 4);
    translate([pcb_cable_slot[0][0], pcb_cable_slot[0][1], -1])
      cube([pcb_cable_slot[1][0] - pcb_cable_slot[0][0], pcb_cable_slot[1][1] - pcb_cable_slot[0][1], 4]);
  }
  // switches
  for (s = pcb_switches) translate([s[0], s[1], 0]) {
    color("black") translate([-3, -3, pcb_z - 3.5]) cube([6, 6, 3.5]);
    color("dimgray") translate([0, 0, pcb_z - sw_height]) cylinder(d = 3.5, h = sw_height - 3.5);
  }
  // XIAO
  color("royalblue") translate([pcb_xiao_center[0] - 10.5, pcb_xiao_center[1] - 8.75, pcb_z + pcb_t + 2.5]) cube([21, 17.5, 1]);
  color("silver") translate([pcb_xiao_center[0] + 7.5, pcb_xiao_center[1] - 4.5, pcb_z + pcb_t + 3.5]) cube([7.5, 9, 3.2]);
  // display module
  color("ivory") translate([pcb_display_center[0], pcb_display_center[1], front_t]) translate([-79 / 2, -36.7 / 2, 0]) cube([79, 36.7, 1]);
  color("darkslategray") translate([pcb_display_center[0], pcb_display_center[1], front_t + 1]) translate([-display_module[0] / 2, -display_module[1] / 2, 0]) cube([display_module[0], display_module[1], 1.2]);
  // buzzer
  color("black") translate([-12, 17, pcb_z + pcb_t]) cylinder(d = 12, h = 9.5);
}

module assembly() {
  color("whitesmoke") front_shell();
  translate([0, 0, 25]) pcb_preview();
  color("lightgray") translate([0, 0, 55]) back_cover();
  for (s = pcb_switches) color("tomato") translate([s[0], s[1], pcb_z - sw_height - 14]) mirror([0, 0, 1]) button_cap();
}

if (part == "front") front_shell();
else if (part == "back") rotate([180, 0, 0]) translate([0, 0, -shell_d - cover_t]) back_cover();
else if (part == "caps") caps();
else if (part == "stand") rotate([0, -90, 0]) translate([35, 0, 0]) stand();
else if (part == "a_back") translate([0, 0, 55]) back_cover();
else if (part == "a_pcb") translate([0, 0, 25]) pcb_preview();
else if (part == "a_caps") for (s = pcb_switches) translate([s[0], s[1], pcb_z - sw_height - 14]) mirror([0, 0, 1]) button_cap();
else assembly();
