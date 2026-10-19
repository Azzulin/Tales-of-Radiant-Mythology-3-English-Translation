# Tutorial: make your own translation of Radiant Mythology 3

This guide is for anyone who wants to change the text of *Tales of the World: Radiant Mythology 3*
(PSP, `NPJH50353`). That could mean fixing a line of the English patch you don't like, rewriting a
character's voice, or translating the whole game into another language. At the end you will have
your own patched ISO and an `.xdelta` patch you can share.

If you only want to **play** the English patch, you don't need any of this. See
[Part A](#part-a--just-apply-the-patch).

Everything here runs on Windows, Linux and macOS. On Windows, type `py` where this guide says
`python3`.

---

## Part A: just apply the patch

1. Get your own dump of the Japanese game. Its MD5 must be
   `5D63D1652B851E005D27FE42DB7D6241` (1,807,089,664 bytes). If it differs, the patch will refuse
   to apply.
2. Download **`RM3-en35-patch-kit.zip`** from the [Releases](https://github.com/Azzulin/Tales-of-Radiant-Mythology-3-English-Translation/releases) page and unzip it.
3. Apply it:
   - **Windows, easiest:** drag your original `.iso` onto `apply-patch.bat`. It checks the MD5 of
     your ISO, then writes `RM3-en35.iso` in the kit folder. xdelta3 is included in the kit.
   - **Linux / macOS:** install xdelta3 (`sudo apt install xdelta3` / `brew install xdelta`), then
     `./apply-patch.sh /path/to/original.iso`.
   - **GUI:** [Delta Patcher](https://github.com/marco-calautti/DeltaPatcher/releases). Original
     file = your Japanese ISO, patch = the `.xdelta`, then *Apply patch*.
   - **Command line:** [xdelta3](https://github.com/jmacd/xdelta-gpl/releases)
     ```
     xdelta3 -d -s "Tales_of_the_World_Radiant_Mythology_3_JPN.iso" RM3-en35.xdelta RM3-en35.iso
     ```
4. Check the MD5 of the result against the one listed in the release notes.
5. Play on **PPSSPP** or a PSP/PS Vita with **custom firmware**. The patched game has a decrypted
   `EBOOT.BIN`, so it does not run on official firmware.

Before you play, don't use the in-game **Data Install**. It copies an untranslated package to the
Memory Stick, and the game then shows Japanese again. If you already did it, delete
`PSP/SAVEDATA/NPJH50353DAT`.

---

## Part B: build it yourself

### B1. What you need

| | Why |
|---|---|
| The original ISO (MD5 above) | Every build starts from it. It is only ever **read**, never written to. |
| Python **3.10 or newer** | All the tools use only the standard library: no `pip install`. |
| Git | To clone this repository. |
| [PPSSPP](https://www.ppsspp.org/) | To dump the decrypted `EBOOT.BIN` (step B3). |
| [xdelta3](https://github.com/jmacd/xdelta-gpl/releases) | To make and test patches (step B8). |
| ~6 GB of free disk | The build writes intermediate ISOs of 1.8 GB each and deletes them as it goes. |

### B2. Clone the repository

```
git clone -c core.longpaths=true https://github.com/Azzulin/Tales-of-Radiant-Mythology-3-English-Translation.git rm3
cd "rm3/PROJETO CLAUDE RM 3/RM3"
```

`core.longpaths` matters on Windows: some paths are long, and without it the clone fails with
*Filename too long*. Clone into a short folder (`C:\rm3`, for example).

**Every command below is run from inside `PROJETO CLAUDE RM 3/RM3/`.** The folder name has
spaces, so keep the quotes.

### B3. Dump the decrypted EBOOT (once)

The game executable (`EBOOT.BIN`) is encrypted on the disc. The menus, items, battle text and much
of the UI live inside it, so the tools need a decrypted copy. It cannot be included in this
repository, but PPSSPP can make it for you:

1. In PPSSPP: **Settings → Tools → Developer tools** → turn on
   **"Dump decrypted EBOOT.BIN on game boot"**.
2. Boot the **original Japanese** ISO once, until the title screen.
3. Find the new file of ~5.86 MB in PPSSPP's memstick folder (usually `PSP/SYSTEM/DUMP/`).
4. Copy it to `PROJETO CLAUDE RM 3/RM3/eboot/EBOOT_dec_LIMPO.bin` (create the `eboot` folder).
5. Check it:

| Check | Expected |
|---|---|
| Size | 5,863,040 bytes |
| First 4 bytes | `7F 45 4C 46` (`\x7fELF`). If you see `~PSP`, it is the encrypted file. |
| SHA-256 | `59ada394a8e25894a1d44c1a62236c715e9f5ee4bea02513fc4f9e58ea94fb2a` |

Turn the dump option off again afterwards.

### B4. Reproduce the official build first

Before you change anything, rebuild the official English patch. If your output matches
byte for byte, your setup is right, and any difference after that comes from your edits alone.

**1. Build the EBOOT** from the clean dump and the 12 EBOOT text tables:

```
python3 ferramentas/eboot_build2.py eboot/EBOOT_dec_LIMPO.bin eboot/EBOOT_dec_meu.bin \
   dados/lote_criacao.csv dados/lote2_ui.csv dados/lote3_guia.csv dados/sis_auditoria.csv \
   dados/elenco_nomebox_auditoria.csv dados/sis03_auditoria.csv dados/sis04_auditoria.csv \
   dados/item_equip_ponteiros_limpo.csv dados/p68_lote.csv dados/p68_vazias.csv \
   dados/item_equip_extras.csv dados/sis05_lote.csv --transborda --aplicar
```

(On Windows `cmd`/PowerShell, put it all on one line instead of using `\`.)

Expected SHA-256 of `eboot/EBOOT_dec_meu.bin`:
`e498e880a921f4345799a9c9ccb3eaa17fade59b99be45f1c0d1db3a42e56064`

**2. Build the ISO.** One command runs all 18 steps in the right order (dialogue, quest board,
names, synopsis, guide, EBOOT...):

```
python3 ferramentas/iso_receita.py "C:/path/to/original.iso" "C:/path/to/my-build.iso" --eboot eboot/EBOOT_dec_meu.bin
```

Without `--aplicar` this is a **dry run**: it only lists the steps. Add `--aplicar` to build. It
takes about 4 minutes and prints `ok` per step. If any step fails, it stops and tells you which.
The full log goes to `my-build.iso.log`.

Expected result for the current sources: MD5 `1E45CE39C2C8F60DC026AD619EA1DB30`, the same as the
`en35` release. The ISO is 64 KB larger than the original. That is expected.

The official build also prints a few lines that look alarming but are known and expected:

- `AVISO: N traducoes aplicadas mas so M conferidas na releitura` on the synopsis, chapter,
  profile and guide steps (the re-read check can't match every line in those formats);
- `*** 2 ALERTAS ***` about `v2069 sinopse` color codes (`0x13`/`0x14` 285 → 138). Part of the
  synopsis lost its name coloring in translation. It is cosmetic and tracked as a known issue.

If your build prints *other* alerts, look at them before you ship.

### B5. Where the text lives

All translation files are UTF-8, tab-separated (`.tsv`) or comma-separated (`.csv`). The safest
way to edit them is a code editor (VS Code, Notepad++). A spreadsheet can work, but it may treat
`"` as a field delimiter, drop invisible characters or change the line endings, so if you use one,
run the validator (B7) afterwards and compare with `git diff`. **Only edit the `traducao` column** (Portuguese for "translation"). The other columns (`id`,
`original`, offsets, sizes) are how the tools find the text in the game files.

| What you see in the game | File(s), under `RM3/` | Notes |
|---|---|---|
| Main story dialogue | `lotes/MEV-*_retorno.tsv` | 5,057 lines |
| Character skits | `lotes/CEV-*_retorno.tsv` | 12,778 lines |
| Quest events | `lotes/QEV-*_retorno.tsv` | 3,829 lines |
| Guild NPCs, towns, side events | `lotes/NEV-*`, `TEV-*`, `SEV-*_retorno.tsv` | |
| Quest board / request texts | `lotes/TXZ-*_retorno.tsv` | **byte limit** per line: column `orcamento_bytes` |
| Loose scene lines, field options | `lotes/CAMPO-01_retorno.tsv`, `lotes_p68/CAMPO-02_retorno.tsv`, `lotes_p68/CAMPO-03_retorno.tsv` | |
| Skit titles | `lotes_bancos/SKITBDI-*_retorno.tsv` | |
| Synopsis (story so far) | `dados/sinopse_com_cor.tsv` | has color codes, see B6 |
| Synopsis screen chapter list | `lotes_bancos/CAPITULO-*_retorno.tsv` | drawn in a 26-column, double-width font |
| Character profiles | `lotes_bancos/PERFIL-ORG_retorno.tsv`, `PERFIL-TOW3_retorno.tsv` | |
| Character full names | `dados/ficha_nomes.csv` | |
| Guidebook (Library) | `lotes_bancos/GUIA-01_retorno.tsv` | |
| Judas's incantation | `lotes_bancos/ZQE-JUDAS_retorno.tsv` | |
| Menus, items, equipment, arts, battle text, system messages | the 12 `dados/*.csv` files listed in B4 | `(verbatim)` = keep the original bytes |
| A few fixed-size EBOOT strings (Yes/No, Cancel...) | `dados/eboot_local.tsv` | must fit the original slot |

The `lotes/SIS-*`, `lotes/ITEM-*` and `lotes_p68/*` batches are what translators received and
returned for the EBOOT. Their results were then merged into the `dados/*.csv` tables, and **the
build reads only those tables**. To change a menu or an item name, edit the `dados/*.csv` file.

Each `X_retorno.tsv` has a twin `X.tsv` with the same lines and an empty `traducao` column. That is
the clean starting point if you translate a batch from scratch.

Use `grep` (or your editor's "find in files") on the Japanese or English text you saw in the game
to find the line.

### B6. The rules your text must follow

The game was made for Japanese. These rules come from what actually broke during the project,
and the validators enforce most of them:

1. **ASCII only.** The game stores text as EUC-JP (dialogue) or Shift-JIS (quest board), and the
   tools encode your text the same way. Neither has accented Latin letters. Use straight quotes
   `"` `'`, `-` and `...`, not curly quotes, en/em dashes or the `…` character. **Accents (é, ç,
   ñ, ã, ü...) are not supported today**; see B9.
2. **The dialogue box is 3 lines × 42 characters.** No line longer than 42, no more than 3 lines.
3. **Keep the same number of line breaks** (`\n`) as the Japanese. Don't add any: if it doesn't
   fit, shorten it.
4. **Don't touch the markers.** They are not text; the game replaces them at run time:

| In the file | What it is | Rule |
|---|---|---|
| `○○` | the player's name | keep exactly as many as the original |
| `▲▲` / `▼▼` | item names in a trade | same |
| `%s`, `%d`, `% E`... | numbers/names filled in by the game | same ones, **in the same order** |
| `＜数＞`, `＜モンスター名＞`, `＜ダンジョン名＞` | quest placeholders | keep them in Japanese, inside your sentence |
| `\t` | tab | keep it |
| invisible bytes `0x13` + 3 color bytes … `0x14` (synopsis only) | a name drawn in color | keep them around the same name |

The synopsis file (`dados/sinopse_com_cor.tsv`) holds those color bytes as raw invisible control
characters. **Edit it in a code editor that shows control characters** (VS Code, Notepad++), not
in a spreadsheet, which may silently drop them.

5. **Same Japanese line, same translation.** If a line appears twice, translate it the same way
   both times. The cross-batch validator checks this.
6. **Names and terms:** the English patch uses the official *Tales* series names (Apple Gel,
   Luminasia, Star Crystal, Descender...). Character names are in `dados/elenco_falantes.csv`
   (Japanese name → English name). For terms, search the existing `_retorno.tsv` files for the
   Japanese word to see how it was translated before.
7. **Menus are measured in pixels, not characters.** The game font is proportional. A label wider
   than its column overlaps the next one. To measure, use
   `ferramentas/pgf_largura.py <jpn0.pgf> "Your text"` (PPSSPP includes the font at
   `assets/flash0/font/jpn0.pgf`).

### B7. Validate before you build

For each dialogue batch you changed:

```
python3 ferramentas/valida_retorno.py lotes/MEV-03.tsv lotes/MEV-03_retorno.tsv dados/elenco_falantes.csv
```

For non-dialogue batches (system text, no 3×42 box), add `--sem-largura`.

The validator runs 12 checks (same ids, original column untouched, nothing empty, ASCII, line
breaks, 42 columns, 3 lines, no leftover Japanese, name spelling, same-source-same-translation,
markers, printf order). **One failure rejects the whole batch.** Fix it and run it again.

Then check consistency across **all** batches together:

```
python3 ferramentas/valida_lotes.py lotes dados/elenco_falantes.csv
```

This catches the same sentence translated two different ways in two different chapters, and a
name whose spelling drifts. The current English sources still have some old warnings here (about
250 divergent lines). New ones are the ones to look at.

### B8. Build, test, share

1. **If you edited any `dados/*.csv` EBOOT table**, rebuild the EBOOT (B4, step 1) under a **new
   name** (`EBOOT_dec_meu2.bin`). Always build from `EBOOT_dec_LIMPO.bin`, never from a previous
   build, so errors can't pile up unseen. The builder checks five guards before writing (every
   pointer matches, text areas don't overlap, everything fits...) and refuses if one fails.
2. **Build the ISO** with `iso_receita.py` (B4, step 2), pointing `--eboot` at your EBOOT. Always
   use the full recipe: running a single builder alone silently reverts every other part of the
   game to Japanese.
3. **Test in PPSSPP.** At minimum: boot, create a character, one battle and back to the map,
   accept a quest, open the Synopsis, and the scenes you changed. These are the places where past
   builds crashed.
4. **Make your patch.** The script in `patch/` does steps 4 and 5 in one go (it creates the
   patch, applies it to the original again, and compares the MD5s):
   ```
   patch/make-patch.bat original.iso my-build.iso my-translation.xdelta     (Windows)
   ./patch/make-patch.sh original.iso my-build.iso my-translation.xdelta    (Linux/macOS)
   ```
   On Windows, put `xdelta3.exe` in the `patch/` folder first (or anywhere on your `PATH`). By
   hand, it is:
   ```
   xdelta3 -e -9 -S djw -B 1073741824 -s original.iso my-build.iso my-translation.xdelta
   ```
   `-B 1073741824` (a 1 GB source window) matters: the build shifts data inside the 990 MB game
   container, and xdelta can only reuse data it can still "see" in the original. With this
   option the official patch is ~3 MB.
5. **Check that the patch works** before you share it:
   ```
   xdelta3 -d -s original.iso my-translation.xdelta check.iso
   ```
   `check.iso` must have the same MD5 as `my-build.iso`.
6. Share only the `.xdelta`, with the MD5 of the original and of the patched ISO. **Never share
   the ISO itself.** To give players the same double-click experience, ship your `.xdelta` next
   to `patch/apply-patch.bat`, `patch/apply-patch.sh` and `xdelta3.exe`. The scripts work with any
   `.xdelta` in their folder and name the output after it (`my-translation.iso`).

### B9. Translating into another language

The whole pipeline works the same for any target language: replace the English in the `traducao`
columns with your language, validate, build. Two things to know first:

- **Accents are the open problem.** The game draws text with the PSP system font, which does have
  accented glyphs. But the text goes through Japanese encodings (EUC-JP and Shift-JIS) that have
  no codes for them, and nobody has tested yet whether the game can be made to show them. The
  tools reject non-ASCII on purpose. The simplest route is writing without accents. Making accents
  work would be a research project (finding how the game converts text to font glyphs). If you
  try it, please open an issue with what you find.
- **Length.** Byte size is no longer a limit for dialogue: the build grows the game container
  wherever a scene needs more room. The real limits are the **screen** ones: 3×42 in the dialogue
  box, pixel width in menus, and the byte budget of the quest board (`TXZ`) lines.

Start with one batch (`MEV-00a` is the opening of the game), build, and look at it in the game
before translating thousands of lines.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Filename too long` when cloning | `git clone -c core.longpaths=true ...` into a short folder |
| `python` opens the Microsoft Store (Windows) | use `py` |
| `RECUSADO: EBOOT ... nao existe` | `--eboot` is relative to `RM3/`; check the path and name |
| `RECUSADO: ... ja existe` | the output ISO already exists: delete it or choose another name |
| Recipe step `FALHOU: o passo pulou N item(ns)` | a line didn't fit (usually a `TXZ` line over `orcamento_bytes`); see the `.log` |
| `RECUSADO: N chaves do motor de texto traduzidas` | you translated a `＜…＞` placeholder key in an EBOOT table; set it back to `(verbatim)` |
| `UnicodeEncodeError` / `fora do ASCII` | a non-ASCII character (curly quote, accent, `…`) in your text |
| Patched game shows Japanese everywhere | Data Install was used; delete `PSP/SAVEDATA/NPJH50353DAT` |
| Patch is much bigger than a few MB | create it again with `-B 1073741824` |

The tool messages and the internal notes are in Portuguese (the maintainer's language). The tool
names follow it too: *lote* = batch, *retorno* = returned batch, *dados* = data,
*ferramentas* = tools, *aplicar* = apply, *recusado* = refused, *cabe* = fits.
