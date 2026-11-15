'use strict';
/*
 * Агент на Mineflayer (1.8.9), символьное наблюдение + сигналы награды.
 *
 * stdin JSON:
 *   {"type":"step","action":{...}}  -> применить действие, через ~50мс вернуть obs+reward
 *   {"type":"reset"}                -> сбросить флаги эпизода (selfDead и счётчики)
 *   {"type":"ping"} / {"type":"stop"}
 *
 * stdout JSON:
 *   {"type":"ready", ...}
 *   {"type":"obs","obs":{...},"reward":{hits_landed,damage_taken,enemy_dead,dist,self_hp},"done":bool}
 *
 * Флаги: --autoaim 1  — каждый шаг смотреть на ближайшего врага (упрощает обучение атаки).
 */
const mineflayer = require('mineflayer');
const Vec3 = require('vec3');
const readline = require('readline');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i !== -1 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}

const username = arg('name', 'Bot' + Math.floor(Math.random() * 10000));
const host = arg('host', '127.0.0.1');
const port = parseInt(arg('port', '25565'), 10);
const version = arg('version', '1.8.9');
const autoaim = arg('autoaim', '0') === '1';

const bot = mineflayer.createBot({ host, port, username, version });
// placeBlock вешает временные blockUpdate-листенеры; убираем лимит, чтобы не спамить warning
try { bot.setMaxListeners(0); } catch (e) {}
try { bot.world.setMaxListeners(0); } catch (e) {}

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

let ready = false;
let selfDead = false;
let hitsLanded = 0;
let enemyDeaths = 0;
let attackAttempts = 0;

bot.once('spawn', () => {
  ready = true;
  out({ type: 'ready', name: username });
  if (autoaim) {
    // прицел выносим в отдельный таймер (как у dummy), чтобы не конфликтовать
    // с setControlState('forward') в одном тике.
    setInterval(aimAtEnemy, 100);
  }
});

bot.on('entityHurt', (entity) => {
  // срабатывает по "entity_status" (status=2). Для чужих сущностей = наш удар по врагу.
  if (entity && entity !== bot.entity) hitsLanded += 1;
});

bot.on('entityDead', (entity) => {
  if (entity && entity !== bot.entity) enemyDeaths += 1;
});

bot.on('death', () => {
  selfDead = true;
  out({ type: 'event', event: 'death' });
  setTimeout(() => { try { bot._client.write('client_command', { payload: 0 }); } catch (e) {} }, 150);
});

bot.on('kicked', (reason) => out({ type: 'kicked', reason: String(reason) }));
bot.on('end', (reason) => out({ type: 'end', reason: String(reason) }));
bot.on('error', (err) => process.stderr.write('[error] ' + err.message + '\n'));

function dist(a, b) {
  // 2D: арена плоская, а Y сущности соперника глючит при близком контакте в 1.8.9
  const dx = a.x - b.x, dz = a.z - b.z;
  return Math.sqrt(dx * dx + dz * dz);
}

function fin(v) {
  return Number.isFinite(v) ? +v.toFixed(2) : 0;
}

function nearestEnemy() {
  let best = null, bestD = Infinity;
  for (const id in bot.entities) {
    const e = bot.entities[id];
    if (!e || e.id === bot.entity.id || !e.position) continue;
    if (!Number.isFinite(e.position.x) || !Number.isFinite(e.position.z)) continue;
    const d = dist(e.position, bot.entity.position);
    if (Number.isFinite(d) && d < bestD) { bestD = d; best = e; }
  }
  return { entity: best, dist: bestD };
}

function inventoryCounts() {
  let wool = 0, cobweb = 0, sword = false;
  for (const item of bot.inventory.items()) {
    const n = item.name;
    if (n === 'wool' || n === 'white_wool') wool += item.count;
    else if (n === 'web' || n === 'cobweb') cobweb += item.count;
    else if (n === 'diamond_sword') sword = true;
  }
  return { wool, cobweb, sword };
}

function buildObs() {
  const self = bot.entity;
  const { entity: enemy, dist: d } = nearestEnemy();
  return {
    self: {
      x: fin(self.position.x),
      y: fin(self.position.y),
      z: fin(self.position.z),
      yaw: fin(self.yaw),
      pitch: fin(self.pitch),
      health: bot.health,
      food: bot.food,
      onGround: !!self.onGround,
      slot: bot.quickBarSlot,
    },
    enemy: enemy ? {
      exists: true,
      dx: +(enemy.position.x - self.position.x).toFixed(2),
      dy: +(enemy.position.y - self.position.y).toFixed(2),
      dz: +(enemy.position.z - self.position.z).toFixed(2),
      dist: +d.toFixed(2),
    } : { exists: false },
    inventory: inventoryCounts(),
    blocks: scanBlocks(),
  };
}

function aimAtEnemy() {
  const { entity } = nearestEnemy();
  if (entity) {
    const dx = entity.position.x - bot.entity.position.x;
    const dz = entity.position.z - bot.entity.position.z;
    bot.look(Math.atan2(-dx, -dz), 0, true);
  }
}

function placeBlockForward() {
  // поставить блок перед собой (на пол, в направлении взгляда/авто-прицела)
  // ставим только если в руке реально ставимый блок (шерсть/паутина), а не меч
  try {
    const held = bot.heldItem && bot.heldItem.name;
    if (held !== 'wool' && held !== 'white_wool' && held !== 'web' && held !== 'cobweb') return;
    const yaw = bot.entity.yaw;
    const dirX = -Math.sin(yaw);
    const dirZ = -Math.cos(yaw);
    const tx = Math.floor(bot.entity.position.x + dirX);
    const tz = Math.floor(bot.entity.position.z + dirZ);
    const ty = Math.floor(bot.entity.position.y); // уровень ног
    const ref = bot.blockAt(new Vec3(tx, ty - 1, tz)); // блок пола под «впереди»
    if (ref && ref.name !== 'air' && ref.name !== 'cave_air' && ref.name !== 'void_air') {
      bot.placeBlock(ref, new Vec3(0, 1, 0)).catch(() => {});
    }
  } catch (e) {}
}

function scanBlocks() {
  // шерсть/паутина на полу арены (10x10, y=64) — для миникарты
  const blocks = [];
  try {
    for (let x = 0; x < 10; x++) {
      for (let z = 0; z < 10; z++) {
        const b = bot.blockAt(new Vec3(x, 64, z));
        if (b && (b.name === 'cobweb' || b.name === 'web' || b.name.includes('wool'))) {
          blocks.push([x, z, b.name]);
        }
      }
    }
  } catch (e) {}
  return blocks;
}

function applyAction(a) {
  a = a || {};
  // прицел: если autoaim выключен — абсолютный yaw/pitch из действия
  if (!autoaim && typeof a.yaw === 'number' && typeof a.pitch === 'number') {
    bot.look(a.yaw, a.pitch, true);
  }
  bot.setControlState('forward', !!a.forward);
  bot.setControlState('back', !!a.back);
  bot.setControlState('left', !!a.left);
  bot.setControlState('right', !!a.right);
  bot.setControlState('jump', !!a.jump);
  bot.setControlState('sprint', !!a.sprint);
  bot.setControlState('sneak', !!a.sneak);
  if (typeof a.slot === 'number') {
    bot.setQuickBarSlot(Math.max(0, Math.min(8, Math.floor(a.slot))));
  }
  if (a.attack) {
    const { entity } = nearestEnemy();
    if (entity && dist(entity.position, bot.entity.position) < 4.0) {
      attackAttempts += 1;
      try { bot.attack(entity); } catch (e) { process.stderr.write('[attack error] ' + e.message + '\n'); }
    }
  }
  if (a.use) {
    placeBlockForward();
  }
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on('line', (line) => {
  line = line.trim();
  if (!line) return;
  let msg;
  try { msg = JSON.parse(line); } catch (e) { return; }

  if (msg.type === 'ping') { out({ type: 'pong' }); return; }
  if (msg.type === 'stop') { process.exit(0); }
  if (msg.type === 'reset') {
    selfDead = false;
    hitsLanded = 0;
    enemyDeaths = 0;
    return;
  }
  if (msg.type === 'teleport') {
    try { bot.teleport(msg.x, msg.y, msg.z); } catch (e) { process.stderr.write('[tp error] ' + e.message + '\n'); }
    return;
  }
  if (msg.type === 'step') {
    if (!ready) { out({ type: 'obs', obs: null, reward: {}, done: false }); return; }
    hitsLanded = 0;
    enemyDeaths = 0;
    attackAttempts = 0;
    const hpBefore = bot.health;
    applyAction(msg.action);
    setTimeout(() => {
      const damageTaken = Math.max(0, hpBefore - bot.health);
      const { entity: enemy, dist: d } = nearestEnemy();
      out({
        type: 'obs',
        obs: buildObs(),
        reward: {
          hits_landed: hitsLanded,
          damage_taken: +(damageTaken.toFixed(2)),
          enemy_dead: enemyDeaths,
          attacks: attackAttempts,
          dist: enemy ? +d.toFixed(2) : null,
          self_hp: bot.health,
          fwd: bot.getControlState('forward'),
          sprint: bot.getControlState('sprint'),
          held: bot.heldItem ? bot.heldItem.name : null,
          slot: bot.quickBarSlot,
        },
        done: selfDead || bot.health <= 0,
      });
    }, 50);
  }
});
