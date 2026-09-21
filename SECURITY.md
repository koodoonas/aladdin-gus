# Security

## Binary provenance

`ALADGUS.COM` is built entirely from `src/aladgus.s`. A clean rebuild with GNU
binutils must reproduce the committed binary byte for byte:

```sh
make clean all
git diff --exit-code -- ALADGUS.COM
```

The release contains no original or modified game executable and no game
assets. `ALADGUS.COM` validates the user's `ALADDIN.EXE` before writing and
verifies the completed patch afterward.

`python3 tools/audit_repo.py` enforces the release allowlist, rejects known
game-file names and formats, checks executable signatures, and verifies the
committed DOS utility checksum. Maintainers can add `--original PATH` for an
additional comparison against their legally obtained supported executable.

## Reporting a problem

Do not attach or commit copyrighted game files to an issue. Report the file's
size and cryptographic hash, the exact `ULTRASND` value, DOS version, hardware,
and the complete error message instead.
