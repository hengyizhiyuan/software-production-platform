// Recovery integration: connect the retained generated modules without regenerating them.
import './game/plants.js';
import './game/zombies.js';
import './assets/assetManifest.js';
import { createGameState } from './game/state.js';
import { createSunSystem } from './game/sun.js';
import { LEVEL, createLevelProgress, advanceWaves, getCurrentWaveNumber, isLevelCleared } from './game/level.js';
import { createRenderer, gridToPixel } from './render/renderer.js';

const plants = globalThis.PVZ.plants;
const Zombies = globalThis.PvZ.Zombies;
const canvas = document.getElementById('game-canvas');
const renderer = createRenderer(canvas);
const layout = renderer.layout;
const overlay = document.getElementById('overlay');
const button = document.getElementById('overlay-button');
const seedBar = document.getElementById('seed-bar');
let state, board, seeds, sunSystem, zombieSystem, progress;
let running = false, last = 0;

function reset() {
  state = createGameState({ totalWaves: LEVEL.waves.length });
  board = plants.createBoard(5, 9);
  seeds = plants.createSeedBank();
  state.plants = board.plants;
  state.seeds = seeds;
  state.selectedPlantType = null;
  progress = createLevelProgress();
  sunSystem = createSunSystem(state, { skyArea: {
    minX: layout.gridX + 25, maxX: layout.gridX + layout.gridWidth - 25,
    topY: layout.gridY, landingMinY: layout.gridY + 35,
    landingMaxY: layout.gridY + layout.gridHeight - 35,
  }});
  zombieSystem = Zombies.createZombieSystem({
    laneCount: 5, spawnX: layout.gridX + layout.gridWidth + 20, houseX: layout.gridX - 20,
    findTarget: zombie => board.plants.find(p => p.alive && p.row === zombie.lane
      && zombie.x >= p.x - 10 && zombie.x <= p.x + 36),
    damageTarget: (plant, amount) => plants.damagePlant(board, plant, amount),
    onHouseReached: () => finish('lost'),
  });
  state.zombies = [];
  seedBar.replaceChildren();
  for (const packet of seeds) {
    const el = document.createElement('button');
    el.type = 'button'; el.className = 'seed-packet'; el.dataset.type = packet.type;
    el.textContent = packet.name + ' · ' + packet.cost;
    el.addEventListener('click', () => { state.selectedPlantType = packet.type; updateHud(); });
    seedBar.append(el);
  }
  updateHud();
  renderer.render(state);
}
function updateHud() {
  document.getElementById('sun-value').textContent = Math.floor(state.sun);
  document.getElementById('wave-value').textContent = getCurrentWaveNumber(progress);
  document.getElementById('wave-total').textContent = LEVEL.waves.length;
  document.getElementById('status-indicator').textContent = running ? 'Playing' : state.status === 'playing' ? 'Ready' : state.status;
  [...seedBar.children].forEach((el, i) => {
    const p = seeds[i];
    el.dataset.state = p.remaining > 0 ? 'cooling' : state.sun < p.cost ? 'unaffordable' : 'ready';
    el.setAttribute('aria-pressed', String(state.selectedPlantType === p.type));
  });
}
function finish(status) {
  running = false; state.status = status;
  overlay.hidden = false;
  document.getElementById('overlay-title').textContent = status === 'won' ? 'Level cleared!' : 'The zombies reached the house';
  document.getElementById('overlay-message').textContent = 'Play again to try a different planting strategy.';
  button.textContent = 'Play Again';
}
button.addEventListener('click', () => {
  reset(); running = true; overlay.hidden = true; last = performance.now(); updateHud();
});
canvas.addEventListener('click', event => {
  if (!running) return;
  const rect = canvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) * canvas.width / rect.width;
  const y = (event.clientY - rect.top) * canvas.height / rect.height;
  if (sunSystem.collectAt(x, y)) { updateHud(); return; }
  const packet = renderer.hitTestSeedPacket(x, y, state);
  if (packet) { state.selectedPlantType = packet.type; updateHud(); return; }
  const cell = renderer.hitTestGrid(x, y);
  if (!cell || !state.selectedPlantType) return;
  const result = plants.placePlant(board, seeds, state.selectedPlantType, cell.row, cell.col, state.sun, state.elapsed);
  if (result.ok) {
    state.sun -= result.cost;
    const position = gridToPixel(layout, cell.row, cell.col);
    Object.assign(result.plant, position);
    state.selectedPlantType = null;
  }
  updateHud();
});
function tick(dt) {
  state.elapsed += dt;
  const waves = advanceWaves(progress, dt);
  progress = waves.progress;
  for (const spawn of waves.spawns) zombieSystem.spawn({ type: spawn.type, lane: spawn.row });
  sunSystem.update(dt);
  plants.tickSeedBank(seeds, dt);
  plants.update(dt, board, {
    spawnSun: ({plant, amount}) => sunSystem.spawnPlantSun(plant, { value: amount }),
    findTarget: plant => zombieSystem.getZombiesInLane(plant.row).find(z => z.x > plant.x),
    fireProjectile: shot => {
      const point = gridToPixel(layout, shot.row, shot.col);
      state.projectiles.push({...shot, x: point.x + 20, y: point.y, speed: 230});
    },
    explode: ({row, col, damage, radius}) => {
      const point = gridToPixel(layout, row, col);
      for (const z of zombieSystem.getZombies()) if (Math.abs(z.lane-row) <= radius && Math.abs(z.x-point.x) <= radius*layout.cellWidth) zombieSystem.damage(z, damage);
    },
  });
  for (const shot of state.projectiles) {
    shot.x += shot.speed * dt;
    const target = zombieSystem.getZombiesInLane(shot.row).find(z => Math.abs(z.x-shot.x) < 20);
    if (target) {
      zombieSystem.damage(target, shot.damage);
      if (shot.slows) target.speed = Math.min(target.speed, 8);
      shot.hit = true;
    }
  }
  state.projectiles = state.projectiles.filter(p => !p.hit && p.x < canvas.width + 30);
  zombieSystem.update(dt);
  state.zombies = zombieSystem.getZombies().map(z => ({...z, row: z.lane, y: gridToPixel(layout, z.lane, 0).y}));
  state.plants = board.plants;
  if (running && isLevelCleared(progress, zombieSystem.getZombieCount())) finish('won');
  updateHud();
}
function frame(now) {
  if (running) tick(Math.min((now-last)/1000, 0.05));
  last = now;
  renderer.render(state);
  requestAnimationFrame(frame);
}
reset();
requestAnimationFrame(frame);
