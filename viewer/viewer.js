// Brickwise viewer: renders a validated build spec as an explorable brick model.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

// Keep in sync with brickwise/schema.py.
const PALETTE = {
  'red': '#c91a09', 'blue': '#0055bf', 'yellow': '#f2cd37', 'green': '#237841',
  'dark-green': '#184632', 'orange': '#fe8a18', 'white': '#f4f4f4', 'light-grey': '#a0a5a9',
  'dark-grey': '#6c6e68', 'black': '#1b2a34', 'tan': '#e4cd9e', 'azure': '#36aebf',
};
const SHAPE_HEIGHT = { brick: 3, slope: 3, plate: 1, tile: 1 };

const PLATE = 0.4;           // plate height, in stud units
const STUD_R = 0.3;
const STUD_H = 0.18;
const GAP = 0.03;            // visible seam between neighbouring bricks
const SLOPE_LIP = 0.25;
const TWEEN_MS = 600;
const FADED = 0.18;
const CLICK_SLOP = 5;        // px of pointer travel still counted as a click

const $ = (id) => document.getElementById(id);
const spec = JSON.parse($('brick-spec').textContent);
const groupIndex = new Map(spec.groups.map((g, i) => [g.id, i]));
const groupOf = (id) => spec.groups[groupIndex.get(id)];

// ---------- chrome ----------
$('title').textContent = spec.title;
$('mode').textContent = spec.mode === 'themed' ? 'Themed model' : 'Stack';
$('metaphor').textContent = spec.metaphor;
document.title = spec.title;
{
  const url = document.querySelector('meta[name="brick-source"]')?.content;
  if (url) {
    const link = $('source-link');
    link.href = url;
    link.title = 'Source code and install instructions';
    link.hidden = false;
  }
}
(() => {
  const legend = $('legend');
  for (const g of spec.groups) {
    const row = document.createElement('div');
    row.className = 'row';
    const sw = document.createElement('span');
    sw.className = 'sw';
    sw.style.background = PALETTE[g.color];
    const name = document.createElement('span');
    name.textContent = g.title;
    row.append(sw, name);
    legend.append(row);
  }
  const note = document.createElement('div');
  note.className = 'note';
  note.textContent = 'Bigger brick = more complex concept.';
  legend.append(note);
})();

// ---------- renderer, scene, camera ----------
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas: $('scene'), antialias: true });
} catch (err) {
  $('load-error-msg').textContent = 'WebGL is not available in this browser.';
  $('load-error').hidden = false;
  throw err;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
scene.background = new THREE.Color(cssVar('--scene-bg') || '#ece8de');

// Model extent in studs / plates.
const minX = Math.min(...spec.pieces.map((p) => p.x));
const maxX = Math.max(...spec.pieces.map((p) => p.x + p.w));
const minZ = Math.min(...spec.pieces.map((p) => p.z));
const maxZ = Math.max(...spec.pieces.map((p) => p.z + p.d));
const topY = Math.max(...spec.pieces.map((p) => (p.level + SHAPE_HEIGHT[p.shape]) * PLATE));
const cx = (minX + maxX) / 2;
const cz = (minZ + maxZ) / 2;
const radius = Math.max(3, Math.hypot(maxX - minX, maxZ - minZ, topY) / 2);

const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 2000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.8;
controls.target.set(0, topY * 0.4, 0);
const homeTarget = controls.target.clone();
camera.position.set(radius * 2.1, radius * 1.7, radius * 2.6);
const baseDistance = camera.position.distanceTo(controls.target);
controls.maxDistance = baseDistance * 5;
controls.minDistance = radius * 0.6;
controls.addEventListener('start', () => { controls.autoRotate = false; });

scene.add(new THREE.HemisphereLight(0xffffff, 0x8d8779, 1.7));
const sun = new THREE.DirectionalLight(0xffffff, 2.4);
sun.position.set(radius * 1.5, radius * 3, radius * 1.1);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
const shadowSpan = radius * 4 + 10;
Object.assign(sun.shadow.camera, {
  left: -shadowSpan, right: shadowSpan, top: shadowSpan, bottom: -shadowSpan,
  near: 0.5, far: radius * 12 + 40,
});
sun.shadow.bias = -0.0005;
scene.add(sun);

// ---------- geometry ----------
const studGeo = new THREE.CylinderGeometry(STUD_R, STUD_R, STUD_H, 20);

function baseplate() {
  const x0 = minX - 2, x1 = maxX + 2, z0 = minZ - 2, z1 = maxZ + 2;
  const w = x1 - x0, d = z1 - z0;
  const mat = new THREE.MeshStandardMaterial({ color: PALETTE['light-grey'], roughness: 0.55 });
  const plate = new THREE.Mesh(new THREE.BoxGeometry(w, 0.2, d), mat);
  plate.position.set((x0 + x1) / 2 - cx, -0.1, (z0 + z1) / 2 - cz);
  plate.receiveShadow = true;
  scene.add(plate);
  const studs = new THREE.InstancedMesh(studGeo, mat, w * d);
  const m = new THREE.Matrix4();
  let i = 0;
  for (let x = x0; x < x1; x++) {
    for (let z = z0; z < z1; z++) {
      m.setPosition(x + 0.5 - cx, STUD_H / 2, z + 0.5 - cz);
      studs.setMatrixAt(i++, m);
    }
  }
  studs.receiveShadow = true;
  scene.add(studs);
}

// Slope profile in the (z, y) plane, extruded along x; it falls toward +z.
function slopeGeometry(w, d, h) {
  const z0 = GAP / 2, z1 = d - GAP / 2;
  const back = d > 1 ? 1 : z0;
  const pts = [[z0, 0], [z1, 0], [z1, SLOPE_LIP], [back, h], [z0, h]];
  // Shape u = -z so that rotating +90° about Y maps (u, v, t) -> (x=t, y=v, z=z).
  const shape = new THREE.Shape(pts.map(([z, y]) => new THREE.Vector2(-z, y)));
  const geo = new THREE.ExtrudeGeometry(shape, { depth: w - GAP, bevelEnabled: false });
  geo.rotateY(Math.PI / 2);
  geo.translate(GAP / 2, 0, 0);
  geo.computeVertexNormals();
  return geo;
}

const pieces = [];   // THREE.Group per piece, userData holds state
const pickables = [];

function makePiece(p) {
  const h = SHAPE_HEIGHT[p.shape] * PLATE;
  const color = PALETTE[p.color || groupOf(p.group).color];
  const material = new THREE.MeshStandardMaterial({ color, roughness: 0.3, metalness: 0 });
  const root = new THREE.Group();

  let body, edges;
  if (p.shape === 'slope') {
    body = new THREE.Mesh(slopeGeometry(p.w, p.d, h), material);
    edges = new THREE.EdgesGeometry(body.geometry, 20);
  } else {
    body = new THREE.Mesh(new RoundedBoxGeometry(p.w - GAP, h, p.d - GAP, 2, 0.05), material);
    body.position.set(p.w / 2, h / 2, p.d / 2);
    edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(p.w - GAP, h, p.d - GAP));
  }
  body.castShadow = body.receiveShadow = true;
  root.add(body);

  const outline = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xffffff }));
  outline.position.copy(body.position);
  outline.scale.setScalar(1.01);
  outline.visible = false;
  root.add(outline);

  if (p.shape !== 'tile') {
    const rows = p.shape === 'slope' ? (p.d > 1 ? 1 : 0) : p.d;
    for (let i = 0; i < p.w; i++) {
      for (let j = 0; j < rows; j++) {
        const stud = new THREE.Mesh(studGeo, material);
        stud.position.set(i + 0.5, h + STUD_H / 2, j + 0.5);
        stud.castShadow = true;
        root.add(stud);
      }
    }
  }

  const home = new THREE.Vector3(p.x - cx, p.level * PLATE, p.z - cz);
  root.position.copy(home);
  root.userData = {
    piece: p,
    home,
    height: h,
    centre: home.clone().add(new THREE.Vector3(p.w / 2, h / 2, p.d / 2)),
    material,
    outline,
    offset: new THREE.Vector3(),
    from: new THREE.Vector3(),
    to: new THREE.Vector3(),
    opacityFrom: 1,
    opacityTo: 1,
  };
  root.traverse((o) => { if (o.isMesh) { o.userData.pieceRoot = root; pickables.push(o); } });
  scene.add(root);
  pieces.push(root);
}

baseplate();
spec.pieces.forEach(makePiece);

// ---------- explode ----------
const mean = (vs) => vs.reduce((a, v) => a.add(v), new THREE.Vector3()).divideScalar(vs.length);
const modelCentre = mean(pieces.map((r) => r.userData.centre.clone()));
const groupCentre = new Map(spec.groups.map((g) => [
  g.id, mean(pieces.filter((r) => r.userData.piece.group === g.id).map((r) => r.userData.centre.clone())),
]));
const groupTop = new Map(spec.groups.map((g) => [
  g.id, Math.max(...pieces.filter((r) => r.userData.piece.group === g.id)
    .map((r) => r.userData.home.y + r.userData.height)),
]));

// Where a group sits when the model is exploded (state 2).
// Lift each group in proportion to its height, spread it outward in proportion to its
// horizontal position, then push apart any group boxes that still overlap.
function groupBox(id) {
  const box = new THREE.Box3();
  for (const r of pieces.filter((r) => r.userData.piece.group === id)) {
    const { home, piece, height } = r.userData;
    box.expandByPoint(home);
    box.expandByPoint(home.clone().add(new THREE.Vector3(piece.w, height, piece.d)));
  }
  return box;
}

const groupOffset = (() => {
  const PAD = 2;
  const boxes = spec.groups.map((g) => groupBox(g.id));
  const offsets = spec.groups.map((g, i) => {
    const c = groupCentre.get(g.id);
    const off = new THREE.Vector3(c.x - modelCentre.x, 0, c.z - modelCentre.z);
    off.y = boxes[i].min.y * 1.5 + 1.5;
    return off;
  });
  const moved = (i) => boxes[i].clone().translate(offsets[i]).expandByScalar(PAD / 2);
  for (let iter = 0; iter < 80; iter++) {
    let clean = true;
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const a = moved(i), b = moved(j);
        if (!a.intersectsBox(b)) continue;
        clean = false;
        const ca = a.getCenter(new THREE.Vector3()), cb = b.getCenter(new THREE.Vector3());
        const penX = Math.min(a.max.x, b.max.x) - Math.max(a.min.x, b.min.x);
        const penZ = Math.min(a.max.z, b.max.z) - Math.max(a.min.z, b.min.z);
        const axis = penX <= penZ ? 'x' : 'z';
        let sign = Math.sign(cb[axis] - ca[axis]);
        if (sign === 0) sign = (i + j) % 2 ? 1 : -1;
        const push = (Math.min(penX, penZ) / 2) + 0.01;
        offsets[i][axis] -= sign * push;
        offsets[j][axis] += sign * push;
      }
    }
    if (clean) break;
  }
  return new Map(spec.groups.map((g, i) => [g.id, offsets[i]]));
})();

// Bounding sphere of the exploded layout, used to frame the camera in state 2.
const explodedSphere = (() => {
  const box = new THREE.Box3();
  for (const g of spec.groups) box.union(groupBox(g.id).translate(groupOffset.get(g.id)));
  return box.getBoundingSphere(new THREE.Sphere());
})();

// Camera distance at which a sphere of radius r fills the view, whichever of the
// vertical or horizontal field of view is narrower.
function fitDistance(r) {
  const v = THREE.MathUtils.degToRad(camera.fov) / 2;
  const h = Math.atan(Math.tan(v) * camera.aspect);
  return (r / Math.sin(Math.min(v, h))) * 1.1;
}
controls.maxDistance = Math.max(controls.maxDistance, fitDistance(explodedSphere.radius) * 2.5);

let state = 1;
let selectedGroup = null;
let tweenStart = 0;

function targetFor(root) {
  const { piece, centre } = root.userData;
  if (state === 1) return new THREE.Vector3();
  const off = groupOffset.get(piece.group).clone();
  if (state === 3 && piece.group === selectedGroup) {
    const gc = groupCentre.get(piece.group);
    off.x += (centre.x - gc.x) * 1.4;
    off.z += (centre.z - gc.z) * 1.4;
    off.y += (centre.y - gc.y) * 3 + 1.5;
  }
  return off;
}

function setState(next, group = null) {
  state = next;
  selectedGroup = next === 3 ? group : null;
  tweenStart = performance.now();
  for (const root of pieces) {
    const u = root.userData;
    u.from.copy(u.offset);
    u.to.copy(targetFor(root));
    u.opacityFrom = u.material.opacity;
    u.opacityTo = state === 3 && u.piece.group !== selectedGroup ? FADED : 1;
  }
  const dist = camera.position.distanceTo(controls.target);
  if (next === 1) {
    focusTo = homeTarget.clone();
  } else if (next === 2) {
    focusTo = explodedSphere.center.clone();
    zoomTo = Math.max(dist, fitDistance(explodedSphere.radius));
  } else {
    focusTo = groupCentre.get(group).clone().add(groupOffset.get(group));
  }
  closePopup();
  renderControls();
  const h = hovered;  // label text depends on the state; rebuild it
  setHover(null);
  if (h) setHover(h);
}

let zoomTo = null;
let focusTo = null;
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

function stepTweens(now) {
  const e = ease(Math.min(1, (now - tweenStart) / TWEEN_MS));
  for (const root of pieces) {
    const u = root.userData;
    u.offset.lerpVectors(u.from, u.to, e);
    root.position.copy(u.home).add(u.offset);
    const op = u.opacityFrom + (u.opacityTo - u.opacityFrom) * e;
    u.material.opacity = op;
    const transparent = op < 0.999;
    if (u.material.transparent !== transparent) {
      u.material.transparent = transparent;
      u.material.needsUpdate = true;  // switches the shader program
    }
    u.material.depthWrite = op > 0.5;
  }
  if (focusTo !== null) {
    // Move camera and target together so the view pans rather than swings.
    const step = focusTo.clone().sub(controls.target).multiplyScalar(0.08);
    controls.target.add(step);
    camera.position.add(step);
    if (step.length() < 0.002) focusTo = null;
  }
  if (zoomTo !== null) {
    const dir = camera.position.clone().sub(controls.target);
    const d = dir.length();
    const nd = d + (zoomTo - d) * 0.08;
    camera.position.copy(controls.target).add(dir.setLength(nd));
    if (Math.abs(zoomTo - nd) < 0.05) zoomTo = null;
  }
}

// ---------- controls UI ----------
function renderControls() {
  const main = $('btn-main'), back = $('btn-back'), hint = $('hint');
  if (state === 1) { main.textContent = 'Explode'; back.hidden = true; hint.textContent = ''; }
  if (state === 2) { main.textContent = 'Reassemble'; back.hidden = true; hint.textContent = 'Click a group to take it apart'; }
  if (state === 3) {
    main.textContent = 'Reassemble'; back.hidden = false;
    hint.textContent = groupOf(selectedGroup).title;
  }
}
$('btn-main').addEventListener('click', () => setState(state === 1 ? 2 : 1));
$('btn-back').addEventListener('click', () => setState(2));
window.addEventListener('keydown', (ev) => {
  if (ev.key === 'e' || ev.key === 'E') setState(state === 1 ? 2 : 1);
  if (ev.key === 'Escape') {
    if (!$('popup').hidden) closePopup();
    else if (state === 3) setState(2);
  }
});

// ---------- picking, hover, popup ----------
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let pointerInside = false;
let hovered = null;
let popupPiece = null;

function pick(clientX, clientY) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(pickables, false)[0];
  return hit ? hit.object.userData.pieceRoot : null;
}

function toScreen(v) {
  const p = v.clone().project(camera);
  return { x: (p.x + 1) / 2 * window.innerWidth, y: (1 - p.y) / 2 * window.innerHeight, behind: p.z > 1 };
}

function anchorOf(root) {
  const { piece, height } = root.userData;
  return toScreen(root.position.clone().add(new THREE.Vector3(piece.w / 2, height, piece.d / 2)));
}

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function setHover(root) {
  if (hovered === root) return;
  if (hovered) hovered.userData.outline.visible = false;
  hovered = root;
  const label = $('hover-label');
  if (!root) {
    label.hidden = true;
    $('leader').toggleAttribute('hidden', true);
    renderer.domElement.style.cursor = '';
    return;
  }
  root.userData.outline.visible = true;
  renderer.domElement.style.cursor = 'pointer';
  const p = root.userData.piece;
  label.replaceChildren();
  if (!(state === 3 && p.group === selectedGroup)) {
    const grp = document.createElement('span');
    grp.className = 'grp';
    grp.textContent = `${groupOf(p.group).title} › `;
    label.append(grp);
  }
  label.append(document.createTextNode(p.title));
  label.hidden = false;
  $('leader').toggleAttribute('hidden', false);
}

function placeHoverLabel() {
  if (!hovered) return;
  const a = anchorOf(hovered);
  $('hover-label').style.visibility = a.behind ? 'hidden' : '';
  $('leader').style.visibility = a.behind ? 'hidden' : '';
  if (a.behind) return;
  const centre = toScreen(modelCentre.clone());
  const label = $('hover-label');
  const w = label.offsetWidth, h = label.offsetHeight;
  const right = a.x >= centre.x;
  const lx = clamp(right ? a.x + 120 : a.x - 120 - w, 8, window.innerWidth - w - 8);
  const ly = clamp(a.y - 70 - h / 2, 8, window.innerHeight - h - 8);
  label.style.transform = `translate(${lx}px, ${ly}px)`;
  const ex = right ? lx : lx + w;
  const svg = $('leader');
  const line = svg.querySelector('line');
  line.setAttribute('x1', a.x); line.setAttribute('y1', a.y);
  line.setAttribute('x2', ex); line.setAttribute('y2', ly + h / 2);
  const dot = svg.querySelector('circle');
  dot.setAttribute('cx', a.x); dot.setAttribute('cy', a.y);
}

function openPopup(root) {
  const p = root.userData.piece;
  const pop = $('popup');
  pop.querySelector('h2').textContent = p.title;
  pop.querySelector('.dots').textContent = '●'.repeat(p.complexity) + '○'.repeat(5 - p.complexity);
  pop.querySelector('.dots').title = `Complexity ${p.complexity} of 5`;
  pop.querySelector('.grp').textContent = groupOf(p.group).title;
  pop.querySelector('.lead').textContent = p.description;
  pop.querySelector('.details').textContent = p.details;
  pop.querySelector('.example p').textContent = p.example || '';
  pop.querySelector('.example').hidden = !p.example;
  pop.scrollTop = 0;
  pop.hidden = false;
  popupPiece = root;
  placePopup();
}

function closePopup() {
  $('popup').hidden = true;
  popupPiece = null;
}

function placePopup() {
  if (!popupPiece) return;
  const a = anchorOf(popupPiece);
  if (a.behind) { closePopup(); return; }
  const pop = $('popup');
  const w = pop.offsetWidth, h = pop.offsetHeight;
  const right = a.x < window.innerWidth / 2;
  const x = clamp(right ? a.x + 24 : a.x - 24 - w, 8, window.innerWidth - w - 8);
  const y = clamp(a.y - h / 2, 8, window.innerHeight - h - 8);
  pop.style.transform = `translate(${x}px, ${y}px)`;
}

$('popup').querySelector('.close').addEventListener('click', closePopup);

let lastMove = null;
let down = null;
const canvas = renderer.domElement;
canvas.addEventListener('pointermove', (ev) => { lastMove = ev; pointerInside = true; });
canvas.addEventListener('pointerleave', () => { pointerInside = false; setHover(null); });
canvas.addEventListener('pointerdown', (ev) => { down = { x: ev.clientX, y: ev.clientY }; });
canvas.addEventListener('pointerup', (ev) => {
  if (!down || Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > CLICK_SLOP) { down = null; return; }
  down = null;
  handleClick(pick(ev.clientX, ev.clientY));
});

function handleClick(root) {
  if (!root) { closePopup(); return; }
  const group = root.userData.piece.group;
  if (state === 2 || (state === 3 && group !== selectedGroup)) { setState(3, group); return; }
  openPopup(root);
}

// ---------- group labels ----------
const groupLabels = new Map(spec.groups.map((g) => {
  const el = document.createElement('div');
  el.className = 'group-label';
  el.textContent = g.title;
  el.style.borderLeft = `4px solid ${PALETTE[g.color]}`;
  el.hidden = true;
  $('group-labels').append(el);
  return [g.id, el];
}));

function placeGroupLabels() {
  for (const g of spec.groups) {
    const el = groupLabels.get(g.id);
    const show = state > 1 && performance.now() - tweenStart > TWEEN_MS * 0.6;
    el.hidden = !show;
    if (!show) continue;
    const c = groupCentre.get(g.id);
    const off = groupOffset.get(g.id).clone();
    const extraLift = state === 3 && g.id === selectedGroup ? 3.5 : 0;
    const s = toScreen(new THREE.Vector3(c.x, groupTop.get(g.id) + 0.8 + extraLift, c.z).add(off));
    if (s.behind) { el.hidden = true; continue; }
    el.style.transform = `translate(${s.x}px, ${s.y}px) translate(-50%, -100%)`;
    el.style.opacity = state === 3 && g.id !== selectedGroup ? 0.45 : 1;
  }
}

// ---------- loop ----------
function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// First view: back the camera off until the whole model fits the screen's real shape
// (a portrait phone needs roughly twice the distance of a desktop window).
{
  const dir = camera.position.clone().sub(controls.target);
  dir.setLength(Math.max(dir.length(), fitDistance(radius)));
  camera.position.copy(controls.target).add(dir);
}

function frame(now) {
  stepTweens(now);
  controls.update();
  if (pointerInside && lastMove) setHover(pick(lastMove.clientX, lastMove.clientY));
  placeHoverLabel();
  placePopup();
  placeGroupLabels();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
renderControls();
requestAnimationFrame(frame);

// Hook for automated smoke tests.
window.__brickwise = {
  get state() { return state; },
  get selectedGroup() { return selectedGroup; },
  setState,
  pieceIds: spec.pieces.map((p) => p.id),
  screenPos(id) {
    const root = pieces.find((r) => r.userData.piece.id === id);
    const a = anchorOf(root);
    // Aim slightly below the top face centre so the ray hits the body.
    return { x: a.x, y: a.y + 4 };
  },
  positionsFinite() {
    return pieces.every((r) => ['x', 'y', 'z'].every((k) => Number.isFinite(r.position[k])));
  },
};
window.__brickwiseReady = true;
