'use strict';
/*
 * Скриптовый противник: идёт к ближайшему врагу и атакует.
 * Нужен как baseline-соперник и для дымового теста (движущаяся цель).
 */
const mineflayer = require('mineflayer');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i !== -1 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}

const username = arg('name', 'Dummy');
const host = arg('host', '127.0.0.1');
const port = parseInt(arg('port', '25565'), 10);
const version = arg('version', '1.8.9');
const still = arg('still', '0') === '1';

const bot = mineflayer.createBot({ host, port, username, version });

function dist(a, b) {
  const dx = a.x - b.x, dz = a.z - b.z;
  return Math.sqrt(dx * dx + dz * dz);
}

function nearestEnemy() {
  let best = null, bestD = Infinity;
  for (const id in bot.entities) {
    const e = bot.entities[id];
    if (!e || e.id === bot.entity.id || !e.position) continue;
    const d = dist(e.position, bot.entity.position);
    if (d < bestD) { bestD = d; best = e; }
  }
  return { entity: best, dist: bestD };
}

bot.once('spawn', () => {
  process.stdout.write(JSON.stringify({ type: 'ready', name: username }) + '\n');
  bot.setQuickBarSlot(0); // меч
  setInterval(tick, 100);
});

bot.on('death', () => {
  setTimeout(() => { try { bot._client.write('client_command', { payload: 0 }); } catch (e) {} }, 150);
});

// минимальный stdin-протокол: телепорт и остановка
const readline = require('readline');
const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on('line', (line) => {
  line = line.trim();
  if (!line) return;
  let msg;
  try { msg = JSON.parse(line); } catch (e) { return; }
  if (msg.type === 'teleport') {
    try { bot.teleport(msg.x, msg.y, msg.z); } catch (e) {}
  } else if (msg.type === 'stop') {
    process.exit(0);
  }
});

function tick() {
  if (still) return;  // неподвижный манекен (для демо/тестов)
  const { entity, dist: d } = nearestEnemy();
  if (!entity) {
    bot.setControlState('forward', false);
    return;
  }
  const dx = entity.position.x - bot.entity.position.x;
  const dz = entity.position.z - bot.entity.position.z;
  bot.look(Math.atan2(-dx, -dz), 0, true); // yaw: mineflayer -> atan2(-dx, -dz)
  bot.setControlState('forward', d > 2.5); // останавливаемся вблизи, чтобы не толкаться
  bot.setControlState('sprint', d > 2.5);
  if (d < 3.0) {
    try { bot.attack(entity); } catch (e) {}
  }
  bot.setControlState('jump', d < 2.0);
}
