"""The exchange-rate ladder tool: generated scenarios validate, large sides split, and the even match interpolates."""
from copy import deepcopy
import json
import importlib.util
from pathlib import Path

from oracle_schema import validate_scenario


_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'exchange-rate' / 'xr.py'
_SPEC = importlib.util.spec_from_file_location('xr', _PATH)
xr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(xr)


def test_every_default_rung_validates_and_spawns_exactly_the_requested_counts():
    for guards, counts in xr.DEFAULT_LADDER.items():
        for bandits in counts:
            value = xr.scenario(xr.ARENA_SAVE, [0, 0], guards, bandits, 10, 2)
            validate_scenario(deepcopy(value))
            spawned = {}
            for spawn in value['setup']['spawns']:
                side = spawn['alias'].split('-')[0]
                assert spawn['count'] <= xr.SIDES[side]['per_spawn']
                assert spawn['expected_templates'] == {xr.SIDES[side]['character']: spawn['count']}
                spawned[side] = spawned.get(side, 0) + spawn['count']
            assert spawned == dict(bandits=bandits, guards=guards)


def test_even_match_interpolates_the_half_crossing_and_reports_unbracketed_ladders():
    assert xr.even_match([(3, 1.0), (5, .7), (7, .3), (9, 0.0)]) == 6
    assert xr.even_match([(3, 1.0), (5, .9)]) is None


def test_member_aliases_map_to_their_side():
    assert xr.side_of('bandits-b/510-gamedata.base/3') == 'bandits'
    assert xr.side_of('guards-a/11623-Dialogue (10).mod/1') == 'guards'
    assert xr.side_of('guards-a') is None and xr.side_of('player') is None


def test_fights_are_aggressive_logged_and_checkpointed_once_a_simulated_minute():
    value = xr.scenario(xr.ARENA_SAVE, [0, 0], 3, 5, 10, 2)
    assert all(spawn['aggro'] is True for spawn in value['setup']['spawns'])
    assert value['setup']['combat_log'] is True
    assert [point['at'] for point in value['checkpoints']] == [0, 1980, 3960, 5940]
    assert value['actions'][-1]['at'] == 5940
    assert [point['at'] for point in xr.scenario(xr.ARENA_SAVE, [0, 0], 1, 1, 1, 2, 90)['checkpoints']] == [0, 1980, 2970]


def test_the_combat_log_decides_when_a_whole_side_is_down_and_wakes_count_back(tmp_path):
    log = tmp_path / 'combat-log.jsonl'
    rows = [dict(kind='hit', seconds=100, character=None), dict(kind='down', seconds=133, character='b1'),
            dict(kind='woke', seconds=166, character='b1'), dict(kind='down', seconds=199, character='b2'),
            dict(kind='dead', seconds=232, character='b1')]
    log.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
    members = dict(b1='bandits', b2='bandits', g1='guards')
    assert xr.log_decided_at(log, members, 100) == 4
    assert xr.log_counts(log)['down'] == 2
    assert xr.log_decided_at(tmp_path / 'missing.jsonl', members, 100) is None
