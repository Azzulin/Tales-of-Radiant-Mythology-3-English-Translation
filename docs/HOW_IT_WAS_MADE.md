# How this translation was made and validated

This page describes how the English patch for *Tales of the World: Radiant Mythology 3* (PSP,
`NPJH50353`) was produced, and what checks a line of text passes before it reaches a release. To
rebuild the patch or make your own, see the [tutorial](TUTORIAL.md).

## Who did what

The project was run by one maintainer ([@Azzulin](https://github.com/Azzulin)), working with AI
tools, and tested by players:

| Role | Who | What |
|---|---|---|
| Direction, decisions, play testing | the maintainer | vocabulary (e.g. `グミ` = *Gel*, the official series name), tone, which compromises to accept, testing every build in game |
| Reverse engineering, tools, audits, builds | Claude (Anthropic), as a coding agent | file formats, the Python tools in this repository, validation, measurement, every ISO build |
| Bulk translation drafts | an external AI translation agent (Google Gemini) | the text of the translation batches, following written rules and name/term indexes |
| Bug reports | testers | crashes, Japanese left on screen, overflowing text, bad lines ([issues](https://github.com/Azzulin/Tales-of-Radiant-Mythology-3-English-Translation/issues)) |

So this is an **AI-assisted translation**, directed and reviewed by a person. No line was
accepted on trust: each one had to pass the checks below. The quality checks on the
translation itself are described in [step 6](#6-quality-review-of-the-translation).

## 1. Reverse engineering, proven by round-trip

Almost all of the game's 1.8 GB lives in one container, `namco.bdi` (990 MB, 7,344 entries,
106,321 files once nested archives are opened). Its index was undocumented. The project mapped it
and every text format inside it, each with its own parser:

| Format | What it holds | Encoding |
|---|---|---|
| `.scr` (FaceChat, gzip) | all dialogue scenes | EUC-JP |
| `.txz` | quest board messages | Shift-JIS |
| PTRTAB | character names and profiles | EUC-JP |
| OLDATA | synopsis and chapter list | EUC-JP |
| CAMPOFIXO | skit titles | EUC-JP |
| GUIA | the in-game guidebook | EUC-JP |
| `EBOOT.BIN` (ELF) | menus, items, arts, battle and system text: 95 pointer tables | EUC-JP |

Before any text was extracted from a format, its parser had to pass a **byte-perfect round-trip**:
parse the original file, rebuild it without changes, and get the same bytes back. FaceChat, for
example, passed on 2,398 of 2,398 scenes. A format that didn't round-trip didn't get a writer.

Every finding (offsets, limits, traps) was written down with how it was verified. The internal log
has 96 entries.

## 2. Extraction into translation batches

The tools pulled every line out of the game into batches of tab-separated files. Each line carries
its id, its scene, its **speaker** (decoded from the scene's command stream), its control codes and
the Japanese original:

| Batch series | Content | Lines |
|---|---|---:|
| `MEV` | main story | 5,057 |
| `CEV` | character skits | 12,778 |
| `QEV` | quest events | 3,829 |
| `NEV` / `TEV` / `SEV` / map | guild NPCs, towns, side events | ~2,700 |
| `TXZ` | quest board | |
| `SIS`, `ITEM`, `P68`... | EBOOT: menus, items, equipment, arts, battle, system | ~15,800 pointers |
| synopsis, chapters, skit titles, profiles, names, guide | the smaller text banks | ~3,500 |

Each batch went out with a briefing and the same rule set: the dialogue box is 3 lines × 42
characters, keep the same number of line breaks, ASCII only, don't touch the markers (`○○` is the
player's name, `%s`/`%d` are filled in by the game), and use the agreed names and terms. The
first batch (`MEV-00a`, the opening) was translated and reviewed alone first, because it fixes the
core world vocabulary (World Tree, Luminasia, Mana, Star Crystal, Descender) for everything after.

## 3. Mechanical validation of every returned batch

`valida_retorno.py` checks each returned batch against the one that was sent. **A single failure
rejects the whole batch:**

| # | Check |
|---|---|
| E1 | same number of lines, same ids, same order |
| E2 | the Japanese column is byte-identical (nobody edited the source) |
| E3 | no empty translation |
| E4 | printable ASCII only (no curly quotes, dashes or `…`) |
| E5 | same number of line breaks, tabs and format codes as the source |
| E6 | no line over 42 characters (dialogue) |
| E7 | no more than 3 lines per box (dialogue) |
| E8 | no Japanese left in the translation |
| E9 | every character name uses the adopted English spelling |
| E10 | the same source line always gets the same translation |
| E11 | run-time markers (`○○`, `▲▲`, `▼▼`) kept, same count |
| E12 | printf codes (`%s`, `%d`...) kept, **in the same order**, none invented |

E12 exists because of a real bug: in 9 quests `%s` and `%d` had been swapped, which shows the
wrong value or worse.

Then `valida_lotes.py` checks **all batches together**: the same sentence translated two ways in
two chapters, a name whose spelling drifts (`Grandmaster` / `Grand Master`). A mistake repeated
consistently inside one batch passes the first validator but not this one.

## 4. Build guards

Writing text back into the game is where things break, so every builder refuses rather than
guesses:

- **Dry run by default.** Nothing is written without an explicit `--aplicar`. The original ISO is
  only ever opened read-only, and the tools refuse to write to it.
- **The EBOOT is always rebuilt from the clean decrypted dump** plus every approved table, never
  from a previous build, so an error can't carry over unseen. Before writing, five guards: every
  pointer points where the table says, no outside pointer lands inside a rewritten text area,
  areas don't overlap, everything fits, and the ELF structure checks out. A further guard refuses
  to translate the text engine's own placeholder keys (`＜数＞`...). Translating them once made
  every quest show raw placeholders.
- **No silent skips.** A scene or string that doesn't fit is a build failure, not a warning.
- **One recipe for the whole ISO.** Each part of the game is written by a different tool, and
  running only one of them on the original silently reverts the others to Japanese. That happened
  once. Since then, `iso_receita.py` runs all 18 steps in order, each on the previous one's output,
  and stops at the first failure.
- **Control-byte inventory.** After the build, `frentes_bytes_controle.py` compares the control
  bytes of each text format between the original and the new ISO. Each format has its own
  line-break convention. Applying the dialogue one to the quest board once crashed the game when
  accepting a quest. This check would have caught it.

## 5. Making room instead of cutting text

The Japanese text often uses fewer bytes than its English translation. Early builds cut the
English to fit. That cost meaning, so the project removed the byte limits instead:

- **`namco.bdi` grows where needed.** The game finds the container through the disc's directory
  record, so entries can be enlarged. The build measures each scene first and grows only the
  entries that need it. Growing every entry once crashed the Synopsis screen, so the rule is now
  "only what's needed". The final ISO is 64 KB larger than the original.
- **The EBOOT got a new memory segment.** Strings that don't fit their original area go into a
  second loadable segment placed right after the program's memory. It holds 26 KB, including all
  326 art descriptions. It was tested in the heaviest battles before being accepted.

The limits that remain are the screen ones: the 3×42 dialogue box, the pixel width of menu
columns (measured with the PSP system font, `pgf_largura.py`), and the quest board line budgets.

## 6. Quality review of the translation

The mechanical checks can't tell a good line from a bad one. In one case a whole batch of
placeholder text passed them. So the translation was also read:

- A sampled review: about 420 lines across the main story, skits and quests/NPCs, each read with
  the line before and after, scored 1–5 by three independent reviewers on a written rubric.
  Averages: main story 4.40, skits 4.28, quests/NPCs 4.24. Lines with a real error of meaning:
  0–1.7% per area.
- The conclusion was a targeted revision, not a retranslation. A mechanical pass fixed terms and
  honorifics across the game (`en34`), and the 55 weakest lines from the samples were rewritten
  (`en35`).
- Character names and recurring items follow the official *Tales* series spelling.

## 7. Testing in game, and the bugs it found

Every build was played by the maintainer, and testers report through issues. Testing found
problems that no check on the files could have found. Each one became a new guard or tool:

| Symptom in game | Cause | Fix |
|---|---|---|
| Crash returning from battle | the compressor wrote several deflate blocks; the game reads only one | single-block compression |
| Crash returning from battle (a second cause) | 130 resource file names, including the class models, had been moved inside the EBOOT | "keep" now means "don't move" |
| Crash accepting a quest | quest board line breaks written in the dialogue format | per-format encoding + control-byte check |
| Synopsis crash / garbage | a chapter pointer at 0; the screen draws only double-width characters; a fixed table in the EBOOT | three separate fixes, confirmed in game |
| Files cut short | a padding field in the container index was copied, not recomputed | exact sizes recomputed every build |
| Raw `＜…＞` in quests | the placeholder key table had been translated | keys locked by a build guard |
| Text overlapping in menus | proportional font wider than the Japanese columns | pixel audit; abbreviations approved case by case |

## 8. Reproducible builds

The patch is reproducible from this repository. On a fresh clone, with only the original ISO and
a PPSSPP dump of its `EBOOT.BIN`:

- the EBOOT rebuilt from the 12 tables is **byte-identical** to the one in the release
  (SHA-256 `e498e880…`);
- the full recipe produces an ISO **byte-identical** to the `en35` release
  (MD5 `1E45CE39C2C8F60DC026AD619EA1DB30`), in about 4 minutes;
- the published `.xdelta`, applied to the original, gives the same MD5.

These were checked on 19/10/2026, when the `en35` patch was published.

## Known limitations

- The `EBOOT.BIN` is decrypted, so the patched game runs on PPSSPP and on PSP/Vita with custom
  firmware, not on official firmware.
- Left in Japanese by choice: the staff roll, debug prompts, a few glyphs that are symbols, and
  the game title in the system menu.
- Part of the synopsis lost its colored names (cosmetic).
- Some long menu labels still touch the next column. Each abbreviation is decided case by case.
- Accented letters are not supported (the game's Japanese encodings have no codes for them).
- Don't use the in-game Data Install with the patch.
