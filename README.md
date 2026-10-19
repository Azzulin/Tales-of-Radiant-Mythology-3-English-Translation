# Tales of the World: Radiant Mythology 3 — English Fan Translation

Fan translation (Japanese → English) of *Tales of the World: Radiant Mythology 3* for the PSP
(`NPJH50353`). Work in progress: all dialogue, menus, items and system text are translated; the
current test build is **`en35`**.

- **Play it:** download the patch from [Releases](../../releases) and follow the steps below.
- **Change it or translate it into another language:** [docs/TUTORIAL.md](docs/TUTORIAL.md).
  Every tool is here, and a fresh clone rebuilds the release byte for byte.
- **How it was made and validated:** [docs/HOW_IT_WAS_MADE.md](docs/HOW_IT_WAS_MADE.md).

## Playing / testing

Builds are published as `.xdelta` patches on the [Releases](../../releases) page. **No ISO is
ever distributed here.** You need your own dump of the original Japanese game.

Verify your dump before patching:

| File | MD5 |
|---|---|
| Original ISO (`NPJH50353`) | `5D63D1652B851E005D27FE42DB7D6241` |
| Patched with `RM3-en35.xdelta` | `1E45CE39C2C8F60DC026AD619EA1DB30` |

Apply the patch with [xdelta](https://github.com/jmacd/xdelta-gpl/releases) or a GUI such as
[Delta Patcher](https://github.com/marco-calautti/DeltaPatcher/releases):

```
xdelta3 -d -s "original.iso" RM3-en35.xdelta RM3-en35.iso
```

Play on **PPSSPP** or a PSP/PS Vita with **custom firmware**. The patched `EBOOT.BIN` is
decrypted, so it does not run on official firmware. The patched ISO is 64 KB larger than the
original. This is expected.

### Before you play

- **Do not use the in-game Data Install** (installing game data to the Memory Stick). The
  installed copy comes from an encrypted, untranslated package on the disc, so the game would show
  Japanese text even with the patch applied. If you already installed it, delete
  `PSP/SAVEDATA/NPJH50353DAT` from your Memory Stick (PPSSPP: `memstick/PSP/SAVEDATA/`).
- **Infinite loading on PPSSPP** is an emulator issue: turn off the shader cache.

## Reporting problems

Open an issue: **[New issue](../../issues/new/choose)**. Pick the template that fits:

- **Text error**: typo, wrong name, bad grammar, mistranslation, off tone.
- **Text overflow / garbled**: text cut off, running out of its box, or broken characters.
- **Untranslated text**: Japanese still showing.
- **Crash / freeze / bug**: the game hangs, crashes, or behaves differently from the original.

Every report should include:

1. **Build**: the patch version you are testing (e.g. `en20`).
2. **Where**: chapter, town/dungeon, NPC or menu, and what you were doing.
3. **A screenshot** (PPSSPP: F12 or *Game settings → Screenshot*). This is the most useful part.

Before opening a new issue, search the existing ones. If your problem is already reported, add a 👍
or a comment instead of a duplicate.

## Repository layout

Everything for this game lives in `PROJETO CLAUDE RM 3/`:

- `RM3/ferramentas/`: Python 3 (stdlib only) tools that parse and rebuild the game's text formats.
  `iso_receita.py` builds the whole patched ISO in one command.
- `RM3/dados/`: extracted string tables, catalogs, and the EBOOT text tables.
- `RM3/lotes*/`: translation batches (`*.tsv` = sent to the translator, `*_retorno.tsv` =
  translated and validated).
- `docs/`: the [tutorial](docs/TUTORIAL.md) and the [process write-up](docs/HOW_IT_WAS_MADE.md).

Game files (ISO, EBOOT, extracted binaries) are intentionally **not** in this repository. Tool
output and internal notes are in Portuguese, the maintainer's language.

## Disclaimer

This is an unofficial, non-commercial fan project and is not affiliated with Bandai Namco.
*Tales of the World: Radiant Mythology 3* is © Bandai Namco Entertainment. Please support the
official releases.
