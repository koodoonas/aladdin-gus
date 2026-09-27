# Aladdin DOS Native GUS Patch

An exact-build patch that enables the native DSMI Gravis UltraSound path
already present in the DOS release of *Aladdin*.

The repository is source-only: it contains no game executable, modified game
executable, music, graphics, or other assets from the original game. The user
must supply the supported `ALADDIN.EXE` from their own installation.

All distributed program code is original patch/tooling code under the MIT
License. See [`PROVENANCE.md`](PROVENANCE.md) for the repository-content audit
and reproducibility procedure.

## Features

- Native GF1-compatible music and sound effects.
- Reads the standard `ULTRASND=port,dma1,dma2,irq1,irq2` environment variable.
- Supports shared or separate primary/secondary DMA and IRQ values.
- DOS-native installer and configurator; Python is not required on the target.
- Exact-build validation before modifying the executable.
- Automatic backups and a reversible restore script.
- Host-side Python reference patcher for auditing and reproducible builds.
- Does not add or remove the original game's EMS requirement.

## Supported game build

Only this executable is supported:

| File | Size | SHA-256 | CRC-32 |
| --- | ---: | --- | --- |
| `ALADDIN.EXE` | 156,024 bytes | `80f7a593af970baf983e7e05c09ba09151b06701f7cda2946e314d29fe270302` | `F05135F0` |

The DOS utility refuses files with a different size or CRC-32. The Python
reference patcher validates the stronger SHA-256 identity.

Version 1.1 produces an executable with SHA-256
`ca806cde85fa701fbb744698570b07aa55ac36685f818ac8f38151bd4d1c6c39`.

## DOS installation

Copy these files into the installed game directory:

- `ALADGUS.COM`
- `INSTALL.BAT`
- `CONFIG.BAT`
- `RESTORE.BAT`

Initialize the card normally and make sure `ULTRASND` is present. For example:

```bat
SET ULTRASND=240,7,7,7,7
```

Then run:

```bat
INSTALL
```

`INSTALL.BAT`:

1. Saves `ALADDIN.EXE` as `ALAD_ORG.EXE` if that backup does not exist.
2. Saves `SOUND.CFG` as `SND_ORG.CFG` if possible.
3. Validates and patches the user's own executable in place.
4. Builds a new 54-byte `SOUND.CFG` from the current `ULTRASND` value.

Do not run the game's `SETSND` utility after installation because it has no GUS
selection and will replace `SOUND.CFG`.

If version 1.0 is already installed, copy the 1.1 files into the game directory
and run `INSTALL` again. The utility recognizes the earlier patched executable
and adds the new `ULTRASND`-driven configuration without requiring restoration
first.

## Changing GUS resources

The configuration is not fixed to one setup. Change `ULTRASND`, initialize the
card with those resources, and run `CONFIG.BAT`:

```bat
SET ULTRASND=250,5,6,11,12
CONFIG
```

The fields follow the standard order:

| Field | Meaning |
| --- | --- |
| `port` | Hexadecimal base address |
| `dma1` | Primary DMA channel |
| `dma2` | Secondary DMA channel |
| `irq1` | Primary IRQ |
| `irq2` | Secondary IRQ |

`CONFIG.BAT` only regenerates `SOUND.CFG`; it does not modify the executable.
The utility accepts base addresses from `100h` through `3F0h` ending in zero,
DMA channels 0-7 except 4, and IRQ values 2-15. Use values actually supported
by the installed GF1-compatible hardware.

## Restoring the game

Run:

```bat
RESTORE
```

The backup files are retained after restoration.

## Memory requirements

The original game requires at least 1 MB of XMS and 1 MB of EMS, including
when configured for no sound. The patch leaves that behavior unchanged. The
original documentation also recommends roughly 570 KB of free conventional
memory.

## Host-side reference patcher

Python 3 can produce the same patched executable without using the DOS tool:

```sh
python3 tools/patch_aladdin_gus.py \
  ALADDIN.EXE ALADDIN.GUS \
  --sound-cfg SOUND.CFG \
  --ultrasnd 240,7,7,7,7
```

If `--ultrasnd` is omitted, the patcher reads the host's `ULTRASND`
environment variable.

## Building the DOS utility

The prebuilt `ALADGUS.COM` is generated entirely from `src/aladgus.s` using GNU
binutils:

```sh
make
```

The utility uses 386 instructions for CRC-32 validation, matching the game's
minimum CPU class.

## Technical summary

The executable contains DSMI's GF1 driver, GUS sample-memory manager, and
`CDI_GUS` device table, but sound-card ID 10 skips their initialization. The
patch connects that dormant route, initializes the GF1 sample heap, registers
the GUS CDI device, starts the GUS voice/timer, and adds safe shutdown handling.

No file size is changed. A 157-byte dispatcher is placed in an unused part of
the bundled DAC driver and eight MZ relocation entries are added.

## Verification

Version 1.1 has been checked with:

- Repository allowlist, file-signature, and binary-provenance audit.
- Static MZ size, relocation, and disassembly validation.
- Byte-identical output from the DOS and Python patchers.
- DOSBox Staging 0.83.0 with multiple `ULTRASND` layouts.
- Instrumented execution through GF1 initialization, sample-memory setup,
  voice start, sample download, and sample playback dispatch.
- Successful installation, reconfiguration, invalid-value rejection, and
  restoration under DOS.
- Confirmed playback on genuine hardware at `ULTRASND=240,7,7,7,7`.
- Confirmed playback on a 486-class 133 MHz system with a GUS PnP.

Other resource layouts are generated according to the standard `ULTRASND`
mapping but cannot all be physically tested.

## Other GUS Patches

[Gravis Ultrasound Game Patches](https://github.com/koodoonas/gus-game-patches-and-fixes)

## AI usage disclosure

These patches have been heavily assisted by AI and, in some cases, developed almost entirely with its help.

I remain ambivalent about AI and its human and environmental costs. But since it’s already here, I might as well use it for something fun until it consumes us all.

## License and game ownership

The original patch code and tooling in this repository are released under the
MIT License. The license does not apply to *Aladdin*, DSMI, or any third-party
software. Users must provide a legally obtained copy of the supported game.

This project is an independent compatibility patch and is not affiliated with
or endorsed by the game's rights holders.
