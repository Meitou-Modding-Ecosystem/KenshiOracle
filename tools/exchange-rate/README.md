# Exchange-rate ladder (MeitouClient)

How many Dust bandits is one Squin guard worth? The ladder spawns N guards against M bandits in open ground,
lets them fight, and finds the bandit count where the guards win half the time. That count divided by N is
the exchange rate; measured at several squad sizes it shows how strength grows with numbers.

[xr.py](xr.py) has three commands: `pin` (engine profile entry for the arena save), `make` (scenarios) and
`analyse` (win rates). It needs the [Meitou-Modding-Ecosystem patch series](../../integrations/meitou-ecosystem/README.md)
in the engine (adapter 0.15.0 or later: aggressive spawns and the combat log).

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
-60 towards each other and 0 towards the player, and both squads spawn with the attack-enemies goal, so they
fight until one side is down. Each fight runs up to 180 simulated seconds (`make --fight-seconds` changes it).
The game pauses only for a state capture once a simulated minute; every hit, knockout, death and severed limb
goes to the repetition's `combat-log.jsonl`.

## Setup on Windows

These steps use three folders:

| Variable | Folder | Holds |
| --- | --- | --- |
| `$Repos` | the folder that holds your MeitouClient clone, e.g. `C:\Users\<you>\source\repos` | both clones |
| `$Engine` | `$Repos\MeitouClient` | the MeitouClient clone |
| `$Oracle` | `$Repos\KenshiOracle` | the KenshiOracle clone (step 2 creates it) |

Set them in each PowerShell terminal you open, changing the first line to your path:

```powershell
$Repos = "C:\Users\<you>\source\repos"
$Engine = "$Repos\MeitouClient"
$Oracle = "$Repos\KenshiOracle"
```

1. **Engine.** **Change to the MeitouClient clone:**
   ```powershell
   cd $Engine
   git fetch origin claude/project-thread-tu44tl
   git checkout FETCH_HEAD
   dotnet build -c Release
   ```
2. **KenshiOracle.** **Change to `$Repos`**, clone KenshiOracle there (it becomes `$Oracle`, a sibling of
   `$Engine`, not a folder inside it), then **change to `$Oracle`**:
   ```powershell
   cd $Repos
   git clone https://github.com/Meitou-Modding-Ecosystem/KenshiOracle
   cd $Oracle
   python -m venv .venv
   & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   Every later command runs in `$Oracle`.
3. **Config.**
   ```powershell
   Copy-Item config.example.json config.json
   Copy-Item config.meitou.example.json config.meitou.json
   ```
   In `config.meitou.json`, point `executable`, `working_directory`, `game_install`, `log` and `dump_directory`
   at your build and install (the exe is under `bin\Release\net11.0\`), and set `"state_schema": "0.6"` and
   `"startup_save": null`. Paths in it are relative to `config.meitou.json` itself. In `config.json`, set
   `"scenario_timeout": 3600`: it bounds all repetitions of one scenario, and ten 180-second fights at speed 2
   take about 25 minutes.
4. **Arena save.** In MeitouClient (not under the supervisor), start a one-character game, walk to flat open
   ground at least 1500 units from any town, Dust Bandits or Shek, stop, and save as `oracle-arena`. Leave code
   mods such as Rivalry Core out of the mod list: their parties would join the fight, and the combat log is
   refused while a code mod reads hits. With an engine build
   older than adapter 0.14.1, also copy the save to the original's save folder (re-copy it whenever you
   re-save):
   ```powershell
   Copy-Item -Recurse -Force "$env:LOCALAPPDATA\Meitou\save\oracle-arena" "$env:LOCALAPPDATA\kenshi\save\"
   ```
5. **Pin.** Start the supervisor and leave this terminal open:
   ```powershell
   & .\.venv\Scripts\python.exe -m launcher.meitou_watchdog --config config.meitou.json
   ```
   Once the main menu shows, **open a second terminal, set the three variables again, and change to
   `$Oracle`**:
   ```powershell
   cd $Oracle
   & .\.venv\Scripts\python.exe tools\exchange-rate\xr.py pin --config config.json
   ```
   It writes the save's entry into `runtime\engine-profile.json`. Re-run it whenever the save changes. Run
   the remaining steps in this second terminal.
6. **Scenarios.**
   ```powershell
   & .\.venv\Scripts\python.exe tools\exchange-rate\xr.py make
   ```
   It writes `scenarios\exchange-rate\xr-bMM-gNN.json`. The default ladder is 1 guard against 1-4 bandits, 3
   against 3-9 and 6 against 6-15, 10 repetitions each at speed 2 (MeitouClient accepts 1, 2 or 5); `--ladder "3:4,6,8" --repeat 5` changes it.
   Re-run `make` after updating KenshiOracle: older scenarios have neither aggressive spawns nor the log.
7. **Run**, with the supervisor still open:
   ```powershell
   Get-ChildItem scenarios\exchange-rate\*.json | ForEach-Object {
     & .\.venv\Scripts\python.exe -m launcher run-scenario $_.FullName --target meitou --config config.json --prepare
   }
   ```
   Each repetition is up to 180 simulated seconds (90 real seconds at speed 2, 36 at speed 5) plus the load.
   Each repetition folder under `runs\` holds `combat-log.jsonl`. After a stopped run, before the next:
   ```powershell
   & .\.venv\Scripts\python.exe -m launcher restore-scenario --target meitou --config config.json
   ```
8. **Analyse.**
   ```powershell
   & .\.venv\Scripts\python.exe tools\exchange-rate\xr.py analyse runs
   ```
   It prints per rung the guard wins, bandit wins and undecided runs (both sides still standing at the end), the
   mean time until one side was down (from the combat log), hits and deaths per run, and
   per guard count the even-match bandit count, the bandits-per-guard ratio and its square (the individual
   strength ratio if the fight follows Lanchester's square law).

## Reading the result

A side is down when none of its members is `alive` (unconscious and dead both count as down). An undecided run
counts half a win for each side. If the ratio stays about constant across squad sizes, a linear point cost fits;
if it grows with size, strength is closer to the square law and points should be priced per squad size.

Each win share is a coin-flip estimate: with 10 repetitions a rung's share is good to about ±0.15, so the
even match comes from where the shares cross one half across rungs, not from a single rung. Add repetitions
(`make --repeat 20`) to the rungs around the crossing to tighten it.

`combat-log.jsonl` has one JSON object per line; [scene-setup.md](../../docs/scene-setup.md#fights-aggro-and-combat_log-0150)
lists the keys. The shape of a hit line (values illustrative):

```json
{"kind":"hit","seconds":3612.4,"tick":1840,"source":"Melee","attacker":"<character id>","attacker_faction":"200-gamedata.base","weapons":[{"...": "item record"}],"victim":"<character id>","victim_faction":"11624-Dialogue (10).mod","part":"<body part>","damage":{"cut":14.2,"blunt":3.1,"pierce":0},"absorbed":{"cut":6.0,"blunt":1.0,"pierce":0},"victim_was_down":false}
```
