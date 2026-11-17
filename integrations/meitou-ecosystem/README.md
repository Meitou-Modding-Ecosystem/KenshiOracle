# Meitou-Modding-Ecosystem patch series

The [upstream series](../meitou/README.md) (patches 0001 to 0011) rebased onto
the Meitou-Modding-Ecosystem engine fork, plus patch 0012, which adds the
[scene-setup kits](../../docs/scene-setup.md#kits-setup_set_loadout-and-setup_set_stats-012)
and [state 0.6 equipment](../../docs/state-coverage.md#additive-extension-06)
(adapter **0.14.0**, capability `scene_setup_kits`).

Apply the twelve patches in order to
[Meitou-Modding-Ecosystem/MeitouClient](https://github.com/Meitou-Modding-Ecosystem/MeitouClient)
branch `fork` at `2c7c85f98c92bfd0ffb031f3e851e6244a641279`; the result is
the engine branch `claude/project-thread-tu44tl` at `1c311371`.
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
- Not yet run in the game.

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

The license terms are those of the upstream series ([LICENSE](LICENSE),
[LICENSE-EXCEPTION.md](LICENSE-EXCEPTION.md)).
