# Exchange-rate ladder (MeitouClient)

How many Dust bandits is one Squin guard worth? The ladder spawns N guards against M bandits in open ground,
lets the AI fight, and finds the bandit count where the guards win half the time. That count divided by N is
the exchange rate; measured at several squad sizes it shows how strength grows with numbers.

[xr.py](xr.py) has three commands: `pin` (engine profile entry for the arena save), `make` (scenarios) and
`analyse` (win rates). It needs the [Meitou-Modding-Ecosystem patch series](../../integrations/meitou-ecosystem/README.md)
in the engine (adapter 0.14.0 or later).

## The two sides

Single-type squads from core data (gamedata.base, Newwworld.mod, Dialogue.mod, rebirth.mod; **Verified** with an
FCS reader). A squad plan lists the leader first, then each `squad` entry in order, and the scene setup keeps
the first `count` members, so these give one character type:

| Side | Character | Faction | Template | Per spawn |
| --- | --- | --- | --- | --- |
| bandits | Dust bandit `510-gamedata.base` | Dust Bandits `200-gamedata.base` | Bandit raid small `1130-gamedata.base` (leader Dust bandit, then Dust bandit x9-10) | 10 |
| guards | Hundred Guardian `11623-Dialogue (10).mod` | Shek Kingdom `11624-Dialogue (10).mod` | Shek fortress `51320-rebirth.mod` (leader Hundred Guardian, then x5) | 6 |

Squin's town guard (`Shek Town Guard`) and gate guard (`Shek Gate Guards`) templates are both made of
Hundred Guardians. Larger sides use a second spawn (up to 20 bandits and 12 guards). Both factions are set to
-60 towards each other and 0 towards the player; no orders are given, so the AI engages on sight.

## Setup on Windows

1. **Engine.** In a MeitouClient clone of Meitou-Modding-Ecosystem/MeitouClient:
   `git fetch origin claude/project-thread-tu44tl`, `git checkout FETCH_HEAD`, `dotnet build -c Release`.
2. **KenshiOracle.** Clone Meitou-Modding-Ecosystem/KenshiOracle next to it, then
   `python -m venv .venv` and `& .\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
3. **Config.** Copy `config.example.json` to `config.json` (only `meitou_config` and `engine_profile` matter
   here) and `config.meitou.example.json` to `config.meitou.json`. In the latter, point `executable`,
   `working_directory`, `game_install`, `log` and `dump_directory` at your build and install (the exe is under
   `bin/Release/net11.0/`), and set `"state_schema": "0.6"` and `"startup_save": "oracle-arena"`.
4. **Arena save.** In MeitouClient (not under the watchdog), start a one-character game, walk to flat open
   ground at least 1500 units from any town, Dust Bandits or Shek, stop, and save as `oracle-arena`. Leave code
   mods such as Rivalry Core out of the mod list: their parties would join the fight.
5. **Pin.** Start the supervisor in its own terminal:
   `& .\.venv\Scripts\python.exe -m launcher.meitou_watchdog --config config.meitou.json`.
   Once the save has loaded, in a second terminal:
   `& .\.venv\Scripts\python.exe tools\exchange-rate\xr.py pin --config config.json`.
   It loads the save, reads the player's position before and after the one-second settle, and writes the
   entry into `runtime/engine-profile.json` (re-run it whenever the save changes).
6. **Scenarios.** `& .\.venv\Scripts\python.exe tools\exchange-rate\xr.py make` writes
   `scenarios/exchange-rate/xr-bMM-gNN.json`. The default ladder is 1 guard against 1-4 bandits, 3 against
   3-9 and 6 against 6-15, 10 repetitions each at speed 3; `--ladder "3:4,6,8" --repeat 5` changes it.
7. **Run.**
   ```powershell
   Get-ChildItem scenarios\exchange-rate\*.json | ForEach-Object {
     & .\.venv\Scripts\python.exe -m launcher run-scenario $_.FullName --target meitou --config config.json --prepare
   }
   ```
   Each repetition is 240 game seconds plus the load; a stopped run needs
   `python -m launcher restore-scenario --target meitou --config config.json` before the next.
8. **Analyse.** `& .\.venv\Scripts\python.exe tools\exchange-rate\xr.py analyse runs` prints per rung the
   guard wins, bandit wins and undecided runs (both sides still standing at 240 s), and per guard count the
   even-match bandit count, the bandits-per-guard ratio and its square (the individual strength ratio if the
   fight follows Lanchester's square law).

## Reading the result

A side is down when none of its members is `alive` (unconscious and dead both count as down). An undecided run
counts half a win for each side. If the ratio stays about constant across squad sizes, a linear point cost fits;
if it grows with size, strength is closer to the square law and points should be priced per squad size.
