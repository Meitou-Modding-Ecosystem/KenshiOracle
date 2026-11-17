"""Exchange-rate ladder: how many bandits one guard is worth, measured on MeitouClient.

Three commands, run from the KenshiOracle root with the project venv:

  pin      load the arena save, read the player's position before and after the
           one-second settle, and write the engine profile entry the scene setup needs
  make     write one scenario per (guards, bandits) rung of the ladder
  analyse  read the run reports and print win rates and the even-match ratio

See tools/exchange-rate/README.md for the full procedure.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'mcp-server'))

ARENA_SAVE = 'oracle-arena'
PLAYER_FACTION = '204-gamedata.base'
SETTLE_CALENDAR_SECONDS = 33

# One character type per side (core data, checked with the FCS reader against gamedata.base, Newwworld.mod,
# Dialogue.mod and rebirth.mod): a squad plan lists the leader first, then each squad entry in order, and the
# scene setup keeps the first `count` members.
SIDES = {
    'bandits': dict(
        label='Dust bandit', character='510-gamedata.base', faction='200-gamedata.base',
        # "Bandit raid small": leader Dust bandit, then Dust bandit x9-10, then bowmen.
        template='1130-gamedata.base', per_spawn=10, z=-20),
    'guards': dict(
        label='Hundred Guardian (Shek town and gate guard, Squin)', character='11623-Dialogue (10).mod',
        faction='11624-Dialogue (10).mod',
        # "Shek fortress": leader Hundred Guardian, then Hundred Guardian x5.
        template='51320-rebirth.mod', per_spawn=6, z=20),
}
DEFAULT_LADDER = {1: [1, 2, 3, 4], 3: [3, 5, 7, 9], 6: [6, 9, 12, 15]}
FIGHT_X = 150
CHECKPOINTS = [0, 10, 20, 30, 45, 60, 90, 120, 150, 180, 240]


# ---- pin -----------------------------------------------------------------------------------------------------

def target_cfg(path):
    from oracle_targets import target_config
    from probe import config
    cfg = config(path)
    cfg.setdefault('target', 'original')
    return target_config(cfg, 'meitou')


def player_row(state):
    rows = [row for row in state['characters'] if row.get('faction_id') == PLAYER_FACTION]
    if len(rows) != 1:
        raise SystemExit(f'the arena save needs exactly one character in {PLAYER_FACTION}, found {len(rows)}')
    return rows[0]


async def read_pins(cfg, save):
    from oracle_origins import read_saved_origins
    from oracle_runner import OracleSession
    session = OracleSession(cfg)
    ping = await session.ping()
    await session.load(save, lock_edge=False, seed=int(cfg.get('base_seed', 0)))
    before, _ = await session.dump()
    await session.call('set_game_speed', speed=1, preserve_pause=True)
    start = (await session.call('get_clock'))['elapsed_seconds']
    await session.until(start + SETTLE_CALENDAR_SECONDS)
    after, _ = await session.dump()
    manifest = await asyncio.to_thread(read_saved_origins, session.source_root(ping, save), save)
    return player_row(before)['position'], player_row(after)['position'], manifest['fingerprint']


def write_entry(profile_path, entry):
    from oracle_engine_profile import PROFILE_FORMAT, validate_profile
    path = Path(profile_path)
    profile = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(
        profile_format=PROFILE_FORMAT, entries=[])
    key = ('target', 'save', 'source_fingerprint', 'seed')
    profile['entries'] = [row for row in profile['entries'] if any(row[k] != entry[k] for k in key)] + [entry]
    validate_profile(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')


def pin(args):
    cfg = target_cfg(args.config)
    if cfg.get('startup_save'):
        raise SystemExit('set "startup_save": null in the Meitou config: the supervisor would load the save again mid-pin')
    before, after, fingerprint = asyncio.run(read_pins(cfg, args.save))
    moved = math.dist((before[0], before[2]), (after[0], after[2]))
    if moved > 0.0005:
        raise SystemExit(f'the player moved {moved:.4f} units during the settle; save with them standing still')
    entry = dict(target='meitou', save=args.save, source_fingerprint=fingerprint, seed=None,
                 player=dict(xz=[round(before[0], 3), round(before[2], 3)], y_before_settle=round(before[1], 3),
                             y_after_settle=round(after[1], 3), decimals=3),
                 evidence='tools/exchange-rate/xr.py pin')
    write_entry(cfg['engine_profile'], entry)
    print(json.dumps(entry, indent=2))


# ---- make ----------------------------------------------------------------------------------------------------

def arena_center(profile_path, save):
    from oracle_engine_profile import load_profile
    rows = [row for row in load_profile(profile_path)['entries'] if row['target'] == 'meitou' and row['save'] == save]
    if not rows:
        raise SystemExit(f'no meitou entry for {save} in {profile_path}; run the pin command first')
    return rows[-1]['player']['xz']


def spawns(side, count):
    facts = SIDES[side]
    rows = []
    for index, start in enumerate(range(0, count, facts['per_spawn'])):
        size = min(facts['per_spawn'], count - start)
        rows.append(dict(alias=f'{side}-{"ab"[index]}', squad_template=facts['template'], count=size,
                         faction_id=facts['faction'], at=dict(offset_from_player=[FIGHT_X + 25 * index, facts['z']]),
                         expected_templates={facts['character']: size}))
    return rows


def scenario(save, center, guards, bandits, repeat, speed):
    bandit, guard = SIDES['bandits'], SIDES['guards']
    return {
        'schema_version': 'scenario-0.2',
        'name': f'xr-b{bandits:02d}-g{guards:02d}',
        'description': (f'Exchange-rate ladder: {bandits} {bandit["label"]} ({bandit["faction"]}) against {guards} '
                        f'{guard["label"]} ({guard["faction"]}), {FIGHT_X} units from the player in {save}. '
                        'The two factions are set to -60 both ways and to 0 towards the player; no orders are given, '
                        'so the AI engages on sight. tools/exchange-rate/xr.py analyse reads the outcome.'),
        'save': save, 'speed': speed, 'repeat': repeat,
        'setup': {
            'preflight': {'scene_center': center, 'scene_radius': 1500, 'squad_size_multiplier': 1,
                          'player_faction_id': PLAYER_FACTION,
                          'expect_absent_factions_in_scene': [bandit['faction'], guard['faction']]},
            'moves': [],
            'spawns': spawns('bandits', bandits) + spawns('guards', guards),
            'settle': {'sim_seconds': 1},
            'heal': 'all_scene_characters',
            'relations': [
                {'a': bandit['faction'], 'b': guard['faction'], 'a_to_b': -60, 'b_to_a': -60},
                {'a': bandit['faction'], 'b': PLAYER_FACTION, 'a_to_b': 0, 'b_to_a': 0},
                {'a': guard['faction'], 'b': PLAYER_FACTION, 'a_to_b': 0, 'b_to_a': 0},
            ],
        },
        'actions': [{'at': CHECKPOINTS[-1], 'command': 'pause', 'params': {'paused': True}}],
        'checkpoints': [{'at': at, 'name': f't{at:03d}'} for at in CHECKPOINTS],
    }


def ladder(text):
    if not text:
        return DEFAULT_LADDER
    result = {}
    for rung in text.split(';'):
        guards, bandits = rung.split(':')
        result[int(guards)] = [int(value) for value in bandits.split(',')]
    return result


def make(args):
    from oracle_schema import validate_scenario
    center = arena_center(args.profile, args.save)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for guards, counts in ladder(args.ladder).items():
        for bandits in counts:
            value = scenario(args.save, center, guards, bandits, args.repeat, args.speed)
            validate_scenario(json.loads(json.dumps(value)))
            path = out / (value['name'] + '.json')
            path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
            print(path)


# ---- analyse -------------------------------------------------------------------------------------------------

def side_of(alias):
    head = alias.split('/')[0]
    return head.split('-')[0] if '/' in alias else None


def standing(state, members):
    """Members of each side neither unconscious nor dead (a character missing from the dump counts as down)."""
    rows = {row['id']: row.get('state') for row in state['characters']}
    counts = defaultdict(int)
    for identity, side in members.items():
        counts[side] += rows.get(identity) == 'alive'
    return counts


def outcome(report_dir, execution):
    alias_map = (execution.get('setup') or {}).get('alias_map') or {}
    members = {identity: side_of(alias) for alias, identity in alias_map.items() if side_of(alias) in SIDES}
    sizes = defaultdict(int)
    for side in members.values():
        sizes[side] += 1
    decided_at, last = None, None
    for capture in execution['checkpoints']:
        path = report_dir / str(execution['execution']) / (capture['name'] + '.json')
        last = standing(json.loads(path.read_text(encoding='utf-8')), members)
        if decided_at is None and min(last['bandits'], last['guards']) == 0:
            decided_at = capture['requested_at']
    winner = ('guards' if last['bandits'] == 0 and last['guards'] > 0 else
              'bandits' if last['guards'] == 0 and last['bandits'] > 0 else None)
    return dict(guards=sizes['guards'], bandits=sizes['bandits'], winner=winner, decided_at=decided_at,
                standing_guards=last['guards'], standing_bandits=last['bandits'])


def outcomes(paths):
    rows = []
    for base in map(Path, paths):
        for report_path in ([base] if base.is_file() else base.rglob('report.json')):
            report = json.loads(report_path.read_text(encoding='utf-8'))
            if not str(report.get('scenario', {}).get('name', report_path.parent.parent.name)).startswith('xr-'):
                continue
            rows += [outcome(report_path.parent, row) for row in report.get('executions', [])
                     if row.get('status') == 'completed']
    return rows


def even_match(points):
    """Bandit count where the guards' win share crosses one half (linear between rungs), or None when not bracketed."""
    points = sorted(points)
    for (b0, p0), (b1, p1) in zip(points, points[1:]):
        if p0 >= .5 >= p1 and p0 != p1:
            return b0 + (p0 - .5) * (b1 - b0) / (p0 - p1)
        if p0 == .5:
            return b0
    return points[-1][0] if points and points[-1][1] == .5 else None


def analyse(args):
    rungs = defaultdict(list)
    for row in outcomes(args.paths):
        rungs[(row['guards'], row['bandits'])].append(row)
    if not rungs:
        raise SystemExit('no completed xr- executions found')
    print('guards bandits  runs  guard wins  bandit wins  undecided  guard share  mean decided at  mean standing g/b')
    shares = defaultdict(list)
    for (guards, bandits), rows in sorted(rungs.items()):
        wins = sum(row['winner'] == 'guards' for row in rows)
        losses = sum(row['winner'] == 'bandits' for row in rows)
        share = (wins + .5 * (len(rows) - wins - losses)) / len(rows)
        shares[guards].append((bandits, share))
        times = [row['decided_at'] for row in rows if row['decided_at'] is not None]
        mean_time = f'{sum(times) / len(times):.0f}s' if times else '-'
        stand = (f'{sum(r["standing_guards"] for r in rows) / len(rows):.1f}/'
                 f'{sum(r["standing_bandits"] for r in rows) / len(rows):.1f}')
        print(f'{guards:6d} {bandits:7d} {len(rows):5d} {wins:11d} {losses:12d} {len(rows) - wins - losses:10d} '
              f'{share:12.2f} {mean_time:>16} {stand:>18}')
    print('\nEven match (undecided runs count half):')
    for guards, points in sorted(shares.items()):
        value = even_match(points)
        if value is None:
            print(f'  {guards} guards: not bracketed; extend the ladder past {max(b for b, _ in points)} bandits'
                  if all(p > .5 for _, p in points) else f'  {guards} guards: not bracketed; add smaller rungs')
            continue
        ratio = value / guards
        print(f'  {guards} guards ~ {value:.1f} bandits: {ratio:.2f} bandits per guard '
              f'(square-law individual strength ratio {ratio * ratio:.1f})')


def parser():
    result = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = result.add_subparsers(dest='command', required=True)
    command = commands.add_parser('pin', help='write the arena save engine profile entry (game running)')
    command.add_argument('--config', default='config.json')
    command.add_argument('--save', default=ARENA_SAVE)
    command.set_defaults(run=pin)
    command = commands.add_parser('make', help='write the ladder scenarios')
    command.add_argument('--profile', default='runtime/engine-profile.json')
    command.add_argument('--save', default=ARENA_SAVE)
    command.add_argument('--ladder', help='"guards:bandits,bandits;..." e.g. "1:1,2,3,4;3:3,5,7,9" (default: '
                         + ';'.join(f'{g}:{",".join(map(str, b))}' for g, b in DEFAULT_LADDER.items()) + ')')
    command.add_argument('--repeat', type=int, default=10)
    command.add_argument('--speed', type=float, default=3)
    command.add_argument('--out', default='scenarios/exchange-rate')
    command.set_defaults(run=make)
    command = commands.add_parser('analyse', help='win rates and even-match ratio from run reports')
    command.add_argument('paths', nargs='*', default=['runs'], help='run folders or report.json files')
    command.set_defaults(run=analyse)
    return result


if __name__ == '__main__':
    arguments = parser().parse_args()
    arguments.run(arguments)
