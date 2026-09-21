ALADDIN NATIVE GUS PATCH 1.1
============================

This package enables the native GF1-compatible Gravis UltraSound music and
sound-effects path already present in the DOS release of Aladdin.

No game executable or game assets are included. You must supply a legally
obtained installation containing the supported ALADDIN.EXE.


SUPPORTED GAME BUILD
--------------------

ALADDIN.EXE size:    156,024 bytes
SHA-256:             80f7a593af970baf983e7e05c09ba09151b06701f7cda2946e314d29fe270302
CRC-32:              F05135F0

The installer refuses unsupported executables.


PACKAGE FILES
-------------

ALADGUS.COM    DOS patch installer and GUS configurator
INSTALL.BAT    Backs up, patches, and configures the game
CONFIG.BAT     Regenerates SOUND.CFG after changing GUS resources
RESTORE.BAT    Restores the backed-up original files
README.TXT     Installation and usage instructions
LICENSE        License for the original patch and tooling
SHA256SUMS.TXT Checksums for this package


REQUIREMENTS
------------

- A GF1-compatible Gravis UltraSound setup initialized before starting.
- A valid ULTRASND environment variable.
- At least 1 MB XMS and 1 MB EMS, as required by the original game.
- Approximately 570 KB free conventional memory is recommended.


INSTALLATION
------------

1. Initialize the sound card normally.

2. Confirm that ULTRASND contains your actual card resources. Its standard
   format is:

     SET ULTRASND=port,dma1,dma2,irq1,irq2

   Example using shared DMA and IRQ resources:

     SET ULTRASND=240,7,7,7,7

3. Copy every file from this package into the installed Aladdin directory.

4. From that directory, run:

     INSTALL

INSTALL.BAT preserves the original ALADDIN.EXE as ALAD_ORG.EXE. If an existing
SOUND.CFG is present, it is preserved as SND_ORG.CFG. Keep these backup files.

Do not run the game's SETSND utility after installation. It has no GUS option
and will replace the generated SOUND.CFG.


CHANGING GUS RESOURCES
----------------------

After changing and reinitializing the card resources, update ULTRASND and run:

  CONFIG

CONFIG.BAT regenerates SOUND.CFG without modifying ALADDIN.EXE again. Shared
or separate primary and secondary DMA/IRQ values are supported.

Accepted values:

- Base port: hexadecimal 100 through 3F0, ending in zero
- DMA: 0 through 7, excluding channel 4
- IRQ: 2 through 15


RESTORING THE ORIGINAL GAME
---------------------------

Run:

  RESTORE

The backup files are retained after restoration.


VERSION 1.0 UPGRADE
-------------------

If patch 1.0 is already installed, replace its patch-package files with these
1.1 files and run INSTALL again. The utility recognizes the earlier patched
executable and creates the resource-aware SOUND.CFG.


PROJECT
-------

Source code, technical details, and issue tracking:
https://github.com/koodoonas/aladdin-gus

This independent compatibility patch is not affiliated with or endorsed by
the game's rights holders.
