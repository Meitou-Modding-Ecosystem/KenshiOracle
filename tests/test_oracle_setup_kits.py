"""Scene-setup kits (setup_set_loadout, setup_set_stats) and the additive state 0.6 equipment."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from oracle_runner import ScenarioError
from oracle_schema import OracleSchemaError, validate_scenario, validate_state
from oracle_setup import loadout_missing
from test_oracle_runner import (MEMBER_ALIASES, _reply, _set, guard_for, report_for, run_setup, setup_fixture,
                                setup_scenario)
from test_oracle_schema_05 import state_05


ROOT = Path(__file__).resolve().parents[1] / 'schema'
KATANA = dict(item_id='fixture-katana', maker_id='fixture-maker', model_id='fixture-model', level=60)
SHIRT = dict(item_id='fixture-shirt', quality=40)


def kit_scenario():
    value = setup_scenario()
    value['setup']['kits'] = [
        dict(alias=MEMBER_ALIASES[0], loadout=deepcopy([KATANA, SHIRT]), stats=dict(katanas=55, toughness=30.5)),
        dict(alias=MEMBER_ALIASES[1], stats=dict(dodge=10)),
    ]
    return value


def kit_fixture(tmp_path):
    fake, cfg, saved = setup_fixture(tmp_path)
    fake.capabilities.append('scene_setup_kits')
    return fake, cfg, saved


def test_kits_run_after_the_settle_dump_and_before_the_heal_and_are_recorded(tmp_path):
    fake, cfg, _ = kit_fixture(tmp_path)
    result = run_setup(fake, cfg, kit_scenario())
    assert result['status'] == 'completed' and result['restored'] is True
    receipt = report_for(cfg)['executions'][0]['setup']
    assert receipt['verdict'] == 'passed'
    work = [row['request']['command'] for row in receipt['steps']
            if row['request']['command'] in ('dump_state', 'setup_set_loadout', 'setup_set_stats', 'setup_heal')]
    assert work[:5] == ['dump_state', 'setup_set_loadout', 'setup_set_stats', 'setup_set_stats', 'setup_heal']
    kit_steps = {row['step'] for row in receipt['steps'] if row['request']['command'].startswith('setup_set_')
                 and row['request']['command'] != 'setup_set_relation'}
    assert kit_steps == {'S3k'}
    first, second = receipt['kits']
    assert first['alias'] == MEMBER_ALIASES[0] and first['id'] == receipt['alias_map'][MEMBER_ALIASES[0]]
    assert [row['item_id'] for row in first['equipment']] == ['fixture-katana', 'fixture-shirt']
    assert (first['stats']['katanas'], first['stats']['toughness']) == (55, 30.5)
    assert second['equipment'] is None and second['stats'] == {'dodge': 10}


def test_a_kit_scenario_needs_the_kits_capability_before_anything_changes(tmp_path):
    fake, cfg, _ = setup_fixture(tmp_path)
    with pytest.raises(ScenarioError, match='scene_setup_kits'):
        run_setup(fake, cfg, kit_scenario())
    assert not any(command.startswith('setup_set') or command == 'setup_spawn_squad' for command in fake.calls)


def _unworn(result):
    result['after'] = result['after'][1:]


def _regraded(result):
    result['after'][0]['level'] = 15


@pytest.mark.parametrize('hook,match', [
    (_reply('setup_set_loadout', _unworn), 'not worn as requested: fixture-katana'),
    (_reply('setup_set_loadout', _regraded), r'fixture-katana \(grade differs\)'),
    (_reply('setup_set_loadout', _set('saved', True)), 'saved:false'),
    (_reply('setup_set_stats', lambda result: result['after'].__setitem__('katanas', 54)), 'katanas reads 54'),
    (_reply('setup_set_stats', _set('character_id', 'char:other')), 'echoed character_id'),
])
def test_kit_read_back_failures_fail_s3k_and_restore(tmp_path, hook, match):
    fake, cfg, _ = kit_fixture(tmp_path)
    command, change = hook
    fake.hooks[command] = change
    with pytest.raises(ScenarioError, match=match) as caught:
        run_setup(fake, cfg, kit_scenario())
    assert 'Scene setup S3k failed' in str(caught.value)
    report = report_for(cfg)
    assert report['executions'][0]['setup']['failure']['step'] == 'S3k'
    assert 'setup_heal' not in fake.calls and 'issue_order' not in fake.calls
    assert guard_for(cfg)['restore_required'] is False


def test_loadout_matching_takes_one_worn_row_per_request_and_checks_requested_grades():
    worn = [dict(item_id='a', level=10, maker_id='m', model_id=None), dict(item_id='b', level=0)]
    assert loadout_missing([dict(item_id='b'), dict(item_id='a', level=10, maker_id='m')], worn) is None
    assert loadout_missing([dict(item_id='a'), dict(item_id='a')], worn) == 'a'
    assert loadout_missing([dict(item_id='a', model_id='x')], worn) == 'a (grade differs)'


@pytest.mark.parametrize('change,match', [
    (lambda kits: kits.append(dict(alias='raiders/fixture-member/4', stats=dict(dodge=1))), 'unknown member alias'),
    (lambda kits: kits.append(dict(alias='player', stats=dict(dodge=1))), 'unknown member alias'),
    (lambda kits: kits.append(deepcopy(kits[1])), 'duplicate kit'),
    (lambda kits: kits[1]['stats'].update(weapons=5), 'weapons'),
    (lambda kits: kits[1]['stats'].update(dodge=101), '101'),
    (lambda kits: kits[0]['loadout'][0].update(level=3.0), 'must be an integer'),
    (lambda kits: kits.append(dict(alias=MEMBER_ALIASES[2])), 'does not have enough properties'),
])
def test_kit_scenarios_are_validated(change, match):
    value = kit_scenario()
    validate_scenario(deepcopy(value))
    change(value['setup']['kits'])
    with pytest.raises(OracleSchemaError, match=match):
        validate_scenario(value)


def add_06(value):
    value['schema_version'] = '0.6'
    for row in value['characters']:
        row.update(equipment=None)
    return value


def test_schema_06_only_adds_equipment_to_05():
    old = json.loads((ROOT / 'state-0.5.schema.json').read_text(encoding='utf-8'))
    new = json.loads((ROOT / 'state-0.6.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(new)
    assert new['$id'] == 'urn:kenshi-oracle:state:0.6' and new['properties']['schema_version']['const'] == '0.6'
    old_character, new_character = old['$defs']['character'], new['$defs']['character']
    assert new_character['required'] == old_character['required'] + ['equipment']
    assert set(new_character['properties']) - set(old_character['properties']) == {'equipment'}
    assert set(new['$defs']) - set(old['$defs']) == {'equipment_item'}


def test_state_06_requires_equipment_and_accepts_worn_rows():
    value = add_06(state_05())
    value['characters'][0]['equipment'] = [dict(section='hip', item_id='fixture-katana', quantity=1, quality=0,
                                                level=60, maker_id='fixture-maker', model_id='fixture-model')]
    value['characters'][1]['equipment'] = []
    assert validate_state(value)['schema_version'] == '0.6'
    missing = add_06(state_05())
    del missing['characters'][0]['equipment']
    with pytest.raises(OracleSchemaError):
        validate_state(missing)
    unversioned = state_05()
    unversioned['characters'][0]['equipment'] = None
    with pytest.raises(OracleSchemaError):
        validate_state(unversioned)
