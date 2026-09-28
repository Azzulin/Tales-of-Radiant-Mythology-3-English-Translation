# Tales of the World: Radiant Mythology 3 — English Fan Translation

Fan translation (Japanese → English) of *Tales of the World: Radiant Mythology 3* for the PSP
(`NPJH50353`). Work in progress.

## Testing

Test builds are published as patches on the [Releases](../../releases) page. **No ISO is ever
distributed here.** You need your own dump of the original Japanese game.

Verify your dump before patching:

| File | MD5 |
|---|---|
| Original ISO (`NPJH50353`) | `5D63D1652B851E005D27FE42DB7D6241` |

Apply the patch with [xdelta](https://github.com/jmacd/xdelta-gpl/releases) (or a GUI such as
Delta Patcher) and play on PPSSPP or a real PSP.

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

- `RM3/ferramentas/`: Python 3 (stdlib only) tools that parse and rebuild the game's text formats.
- `RM3/dados/`: extracted string tables and catalogs.
- `RM3/lotes*/`: translation batches.

Game files (ISO, EBOOT, extracted binaries) are intentionally **not** in this repository.

## Disclaimer

This is an unofficial, non-commercial fan project and is not affiliated with Bandai Namco.
*Tales of the World: Radiant Mythology 3* is © Bandai Namco Entertainment. Please support the
official releases.
