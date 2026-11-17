"""Fork extensions for fights: aggressive spawns and the per-repetition combat log."""
import json

import pytest

from oracle_runner import ScenarioError
from test_oracle_runner import report_for, run_setup, setup_fixture, setup_scenario


def fight_scenario():
    value = setup_scenario()
    value['setup']['spawns'][0]['aggro'] = True
    value['setup']['combat_log'] = True
    return value


def test_aggressive_spawns_are_requested_and_the_combat_log_lands_in_the_repetition_folder(tmp_path):
    fake, cfg, _ = setup_fixture(tmp_path)
    fake.capabilities += ['scene_setup_aggro', 'combat_log']
    result = run_setup(fake, cfg, fight_scenario())
    assert result['status'] == 'completed' and result['restored'] is True
    spawn = next(row['params'] for row in fake.requests if row['command'] == 'setup_spawn_squad')
    assert spawn['aggro'] is True
    execution = report_for(cfg)['executions'][0]
    assert execution['combat_log']['file'] == 'combat-log.jsonl' and execution['combat_log']['hits'] == 1
    folder = next(path.parent for path in tmp_path.rglob('execution.json'))
    assert json.loads((folder / 'combat-log.jsonl').read_text(encoding='utf-8'))['kind'] == 'hit'
    assert not list(fake.output_directory.glob('combat-log-*.jsonl'))


@pytest.mark.parametrize('capability', ['scene_setup_aggro', 'combat_log'])
def test_a_fight_scenario_needs_both_capabilities_before_anything_changes(tmp_path, capability):
    fake, cfg, _ = setup_fixture(tmp_path)
    fake.capabilities.append(capability)
    with pytest.raises(ScenarioError, match='Probe lacks capability'):
        run_setup(fake, cfg, fight_scenario())
    assert 'setup_spawn_squad' not in fake.calls
