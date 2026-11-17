# Meitou-Modding-Ecosystem patch series

The [upstream series](../meitou/README.md) (patches 0001 to 0011) rebased onto
the Meitou-Modding-Ecosystem engine fork, plus patch 0012, which adds the
[scene-setup kits](../../docs/scene-setup.md#kits-setup_set_loadout-and-setup_set_stats-012)
and [state 0.6 equipment](../../docs/state-coverage.md#additive-extension-06)
(adapter **0.14.0**, capability `scene_setup_kits`), and patch 0013, which loads named saves from MeitouClient's
own save folder first (adapter **0.14.1**), and patch 0014, which adds
[aggressive spawns and the combat log](../../docs/scene-setup.md#fights-aggro-and-combat_log-0150) (adapter **0.15.0**).

Apply the fourteen patches in order to
[Meitou-Modding-Ecosystem/MeitouClient](https://github.com/Meitou-Modding-Ecosystem/MeitouClient)
branch `fork` at `2c7c85f98c92bfd0ffb031f3e851e6244a641279`; the result is
the engine branch `claude/project-thread-tu44tl` at `0afcf3ae`.
[series.json](series.json) records each patch's source commit, SHA-256 and
size.

```powershell
git -C <engine> checkout --detach 2c7c85f98c92bfd0ffb031f3e851e6244a641279
git -C <engine> am <this directory>\00*.patch
```

## Rebase onto the fork

- **Verified** on 2026-11-17: patches 0001 to 0011 conflict in three places on
  that base (a camera input average, the first tick after a load, the follow
  camera); after resolving them by hand, keeping both sides' behaviour, all
  eleven apply.
- **Verified** on 2026-11-17 (.NET SDK 10.0.115 with
  `-p:MeitouTargetFramework=net10.0`, Linux): with patch 0012 the solution
  builds with 0 warnings, the 189 oracle tests pass, and the quick suite has
  1006 passes, 0 failures and 7 skips.
- **Verified** on 2026-11-17 (same toolchain): with patch 0013 the solution builds and the quick suite has
  1009 passes, 0 failures and 8 skips.
- **Verified** on 2026-11-17 (same toolchain): with patch 0014 the solution builds with 0 warnings and the quick
  suite has 1009 passes, 0 failures and 8 skips.
- **Observed** on 2026-11-17 (Windows, adapter 0.14.0): the exchange-rate `pin` loaded a save, ran the
  settle and wrote its profile entry.

## Patch 0012

- `setup_set_loadout`: the F10 strip, then the F10 give with Equip per item,
  inside the paused setup bracket; the character's fighter is rebuilt from the
  new kit (`CharacterAssembly.RefreshEquipment`).
- `setup_set_stats`: the F10 set stats per stat (the stored value).
- State 0.6: `equipment` rows per character; 0.1 to 0.5 output unchanged.
- Ping: adapter version 0.14.0, `supported_schema_versions` up to `0.6`
  (default `0.6`), capabilities `scene_setup` and `scene_setup_kits`.
- Four focused tests: paused set stats, strip keeping prosthetic limbs and the
  equipment rows, the `stats` parameter rules and the loadout read-back rule.

## Patch 0013

- `load_save` looks for `<name>\quick.save` under `%LOCALAPPDATA%\Meitou\save` first, then under the
  original's save folder (or the parent of a `--load` folder); ping reports both as `save_roots`, in that
  order. `save_root` keeps its old value.
- The runner reads a save's identities from the first `save_roots` entry that holds it, and falls back to
  `save_root` when the adapter has no `save_roots`.

## Patch 0014

- `setup_spawn_squad` takes `aggro`: the squad gets the attack-enemies goal (`Squad.DebugAggro`).
- `combat_log` start/stop (`OracleCombatLog`): one JSON line per resolved hit and per down, wake, death and
  severed limb, read from `World.CombatHitFeed` between ticks. Refused when a code mod already reads that feed.
- Ping: adapter version 0.15.0, capabilities add `scene_setup_aggro` and `combat_log`.

The license terms are those of the upstream series ([LICENSE](LICENSE),
[LICENSE-EXCEPTION.md](LICENSE-EXCEPTION.md)).
