# Source provenance

This repository distributes an independently written compatibility patch,
installer, configurator, tests, and documentation. It does not distribute the
original or modified game executable, game data, music, graphics, or source
code belonging to the game or its bundled libraries.

The patch's replacement instructions and DOS utility were written for this
project. Executable offsets, structure layouts, device identifiers, entry-point
addresses, file sizes, and hashes are functional compatibility facts needed to
locate and validate the user's own supported executable. The patch operates on
that user-supplied file locally.

`ALADGUS.COM` is a convenience build of `src/aladgus.s`; it is not extracted
from the game. A clean `make` rebuild must reproduce it byte for byte. The
repository audit rejects known game filenames and formats, verifies the DOS
utility checksum, and can optionally check for copied binary blocks against a
legally obtained original executable:

```sh
make clean all
python3 tools/audit_repo.py
python3 tools/audit_repo.py --original /path/to/ALADDIN.EXE
python3 -m unittest discover -s tests -v
```

The optional comparison rejects identical high-information sequences of 32 or
more bytes. Short instruction and data coincidences are expected in 16-bit x86
software and are not treated as copied binary sections.

The game name and hardware product names are used only to identify
compatibility. This project is independent and is not affiliated with or
endorsed by the game's rights holders.
