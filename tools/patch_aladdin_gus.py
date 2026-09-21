#!/usr/bin/env python3
"""Patch the supported DOS Aladdin executable to enable its linked GUS driver.

This is intentionally an exact-build patcher.  It refuses inputs other than the
known executable supplied with this project, then:

* initializes the native GF1 driver and GUS sample heap for sound-card ID 10;
* registers CDI_GUS, starts the GUS voice/timer, and closes it safely; and
* places a tiny 16-bit real-mode dispatch stub in an unused part of the bundled
  DAC driver and adds the required MZ relocation records.

No external assembler is required; the injected instructions are deliberately
small and encoded below with label fixups and relocation bookkeeping.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
from pathlib import Path


SUPPORTED_SHA256 = "80f7a593af970baf983e7e05c09ba09151b06701f7cda2946e314d29fe270302"
SUPPORTED_SIZE = 156_024

# Link-time segments and entry points in the supported executable.
GAME_AUDIO_SEG = 0x19D7
GUS_SEG = 0x21D9
GUS_START_VOICE = 0x04C0
GUS_INIT = 0x0536
GUS_CLOSE = 0x06FE
GUS_USE_TIMER = 0x147C
GUS_HEAP_SEG = 0x233B
GUS_HEAP_INIT = 0x0117
GUS_HEAP_CLOSE = 0x0219
CDI_SEG = 0x238F
CDI_INIT = 0x0000
CDI_REGISTER = 0x0024
MCP_SEG = 0x1CF2
MCP_START_VOICE = 0x26EA
STUB_SEG = 0x1FBE
STUB_OFFSET = 0x0100

# DGROUP addresses in this exact build.
SOUND_CARD = 0x2076
AUDIO_INIT_FLAGS = 0x1C6E
CDI_GUS = 0x14A5


def u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def p16(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", data, offset, value & 0xFFFF)


class StubBuilder:
    """Minimal encoder for the small 8086/386-real-mode dispatch stubs."""

    def __init__(self) -> None:
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.rel8_fixups: list[tuple[int, str]] = []
        self.abs16_fixups: list[tuple[int, str]] = []
        self.far_call_segment_words: list[int] = []

    @property
    def pos(self) -> int:
        return len(self.code)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = self.pos

    def emit(self, *values: int) -> None:
        self.code.extend(v & 0xFF for v in values)

    def emit_u16(self, value: int) -> None:
        self.code.extend(struct.pack("<H", value & 0xFFFF))

    def branch8(self, opcode: int, label: str) -> None:
        self.emit(opcode, 0)
        self.rel8_fixups.append((self.pos - 1, label))

    def far_call(self, segment: int, offset: int) -> None:
        self.emit(0x9A)
        self.emit_u16(offset)
        self.far_call_segment_words.append(self.pos)
        self.emit_u16(segment)

    def cs_byte_store(self, label: str, value: int) -> None:
        # mov byte ptr cs:[label], imm8
        self.emit(0x2E, 0xC6, 0x06)
        self.abs16_fixups.append((self.pos, label))
        self.emit_u16(0)
        self.emit(value)

    def cs_byte_compare_zero(self, label: str) -> None:
        # cmp byte ptr cs:[label], 0
        self.emit(0x2E, 0x80, 0x3E)
        self.abs16_fixups.append((self.pos, label))
        self.emit_u16(0)
        self.emit(0)

    def finish(self, base_offset: int = 0) -> bytes:
        for disp_pos, name in self.rel8_fixups:
            target = self.labels[name]
            displacement = target - (disp_pos + 1)
            if not -128 <= displacement <= 127:
                raise ValueError(f"short branch to {name} is out of range")
            self.code[disp_pos] = displacement & 0xFF
        for word_pos, name in self.abs16_fixups:
            p16(self.code, word_pos, base_offset + self.labels[name])
        return bytes(self.code)


def build_stub() -> tuple[bytes, dict[str, int], list[int]]:
    b = StubBuilder()

    # Called from the reclaimed ID_DAC switch case.  ID 10 gets the dormant
    # native GUS path; ID 7 receives the exact assignments that occupied the
    # reclaimed bytes before the patch.
    b.label("init_dispatch")
    b.emit(0x80, 0x3E)
    b.emit_u16(SOUND_CARD)
    b.emit(0x0A)                         # cmp byte [SoundCard.ID], ID_GUS
    b.branch8(0x75, "init_id_dac")       # jne
    b.cs_byte_store("timer_started", 0)
    b.emit(0x1E)                         # push ds
    b.emit(0x68)
    b.emit_u16(SOUND_CARD)               # push offset SoundCard
    b.far_call(GUS_SEG, GUS_INIT)
    b.emit(0x83, 0xC4, 0x04)             # add sp,4
    b.far_call(GUS_HEAP_SEG, GUS_HEAP_INIT)
    b.far_call(CDI_SEG, CDI_INIT)
    # cdiRegister(&CDI_GUS, 0L, 31L), cdecl/right-to-left.
    b.emit(0x6A, 0x00, 0x6A, 0x1F, 0x6A, 0x00, 0x6A, 0x00, 0x1E, 0x68)
    b.emit_u16(CDI_GUS)
    b.far_call(CDI_SEG, CDI_REGISTER)
    b.emit(0x83, 0xC4, 0x0C)             # add sp,12
    b.emit(0x83, 0x0E)
    b.emit_u16(AUDIO_INIT_FLAGS)
    b.emit(0x02)                         # or word [flags], GUS_INITED
    b.emit(0xB8, 0x01, 0x00, 0xCB)       # mov ax,1 / retf

    b.label("init_id_dac")
    b.emit(0xC7, 0x06, 0xC2, 0x1C, 0xBE, 0x1F)  # SDI_DAC segment
    b.emit(0xC7, 0x06, 0xC0, 0x1C, 0x5E, 0x04)  # SDI_DAC offset
    b.emit(0x33, 0xC0, 0xCB)             # xor ax,ax / retf

    b.label("start_dispatch")
    b.emit(0x80, 0x3E)
    b.emit_u16(SOUND_CARD)
    b.emit(0x0A)
    b.branch8(0x75, "start_mcp")
    b.far_call(GUS_SEG, GUS_START_VOICE)
    b.cs_byte_store("timer_started", 1)
    b.emit(0xCB)
    b.label("start_mcp")
    b.far_call(MCP_SEG, MCP_START_VOICE)
    b.emit(0xCB)

    b.label("shutdown_dispatch")
    # gusClose() assumes the hardware timer was started.  If AMP failed before
    # start_dispatch, suppress only the timer-vector restore while still
    # resetting the GF1 and freeing the DMA buffer.
    b.cs_byte_compare_zero("timer_started")
    b.branch8(0x75, "shutdown_timer_started")
    b.emit(0xC6, 0x06)
    b.emit_u16(GUS_USE_TIMER)
    b.emit(0x00)                         # mov byte [useGUStimer],0
    b.label("shutdown_timer_started")
    b.far_call(GUS_SEG, GUS_CLOSE)
    b.far_call(GUS_HEAP_SEG, GUS_HEAP_CLOSE)
    b.cs_byte_store("timer_started", 0)
    b.emit(0xCB)

    b.label("timer_started")
    b.emit(0)
    b.label("marker")
    b.code.extend(b"ALADDIN GUS PATCH 1.1\0")

    return b.finish(STUB_OFFSET), dict(b.labels), list(b.far_call_segment_words)


def patch_at(data: bytearray, offset: int, replacement: bytes) -> None:
    """Write patch-owned bytes after whole-file exact-build validation."""
    data[offset:offset + len(replacement)] = replacement


def load_relocations(data: bytes | bytearray) -> tuple[int, list[tuple[int, int]]]:
    count = u16(data, 0x06)
    table = u16(data, 0x18)
    relocs = [struct.unpack_from("<HH", data, table + index * 4)
              for index in range(count)]
    return table, relocs


def parse_ultrasnd(value: str) -> tuple[int, int, int, int, int]:
    """Parse ULTRASND=port,dma1,dma2,irq1,irq2."""
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 5:
        raise ValueError("ULTRASND must be port,dma1,dma2,irq1,irq2")
    try:
        port = int(parts[0], 16)
        dma1, dma2, irq1, irq2 = (int(part, 10) for part in parts[1:])
    except ValueError as exc:
        raise ValueError("invalid number in ULTRASND") from exc
    if not 0x100 <= port <= 0x3F0 or port & 0x0F:
        raise ValueError("ULTRASND port must be a hexadecimal address ending in 0")
    if any(channel < 0 or channel > 7 or channel == 4
           for channel in (dma1, dma2)):
        raise ValueError("ULTRASND DMA channels must be 0-7, excluding 4")
    if any(irq < 2 or irq > 15 for irq in (irq1, irq2)):
        raise ValueError("ULTRASND IRQ values must be 2-15")
    return port, dma1, dma2, irq1, irq2


def build_sound_cfg(ultrasnd: str) -> bytes:
    """Return the game's packed 54-byte SOUNDCARD structure."""
    port, dma1, dma2, irq1, irq2 = parse_ultrasnd(ultrasnd)
    cfg = bytearray(54)
    cfg[0] = 10                          # ID_GUS
    struct.pack_into("<H", cfg, 1, 0x0100)
    name = b"Gravis Ultrasound"
    cfg[3:3 + len(name)] = name
    struct.pack_into("<H", cfg, 0x23, port)
    cfg[0x25] = irq1                    # primary IRQ
    cfg[0x26] = dma1                    # primary DMA
    struct.pack_into("<H", cfg, 0x27, 19_293)
    struct.pack_into("<H", cfg, 0x29, 44_100)
    cfg[0x2B] = 1                       # stereo
    cfg[0x2C] = 1                       # mixer present
    cfg[0x2D] = 1                       # 8-bit source samples
    cfg[0x2E] = dma2                    # secondary DMA
    cfg[0x2F] = irq2                    # secondary IRQ
    cfg[0x30] = 1                       # DMA sample uploads
    cfg[0x31] = 1                       # use the GF1 hardware timer
    return bytes(cfg)


def patch_executable(source: Path, destination: Path) -> dict[str, int | str]:
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if len(original) != SUPPORTED_SIZE or digest != SUPPORTED_SHA256:
        raise ValueError(
            "unsupported ALADDIN.EXE build: "
            f"size={len(original)}, sha256={digest}; expected "
            f"size={SUPPORTED_SIZE}, sha256={SUPPORTED_SHA256}"
        )
    if original[:2] != b"MZ":
        raise ValueError("input is not an MZ executable")

    data = bytearray(original)
    header_size = u16(data, 0x08) * 16
    declared_pages = u16(data, 0x04)
    last_page = u16(data, 0x02)
    declared_size = (declared_pages - 1) * 512 + (last_page or 512)
    if header_size != 0x800 or declared_size != len(data):
        raise ValueError("unexpected MZ layout")

    stub, labels, stub_far_segment_words = build_stub()
    stub_file_offset = header_size + STUB_SEG * 16 + STUB_OFFSET
    stub_end = stub_file_offset + len(stub)
    if stub_end > len(data):
        raise ValueError("dispatch stub does not fit in the executable image")

    # This exact range is part of the bundled ID_DAC driver and is never used
    # by the installed GUS configuration.  It is inside the initialized load
    # image, unlike the post-image BSS/stack gap (which startup clears).
    relocation_table, relocs = load_relocations(data)
    cave_start = STUB_SEG * 16 + STUB_OFFSET
    cave_end = cave_start + len(stub)
    cave_relocs = [
        (offset, segment) for offset, segment in relocs
        if cave_start <= segment * 16 + offset < cave_end
    ]
    if cave_relocs:
        raise ValueError(f"dispatch cave contains relocations: {cave_relocs}")

    # ID_GUS used to jump over initialization.  Send it to the reclaimed ID_DAC
    # switch case, which now calls init_dispatch and then skips the MCP path.
    patch_at(
        data,
        header_size + GAME_AUDIO_SEG * 16 + 0x02EF,
        bytes.fromhex("E9 BA 00"),
    )

    trampoline = bytearray()
    trampoline.extend(b"\x9A")
    trampoline.extend(struct.pack(
        "<HH", STUB_OFFSET + labels["init_dispatch"], STUB_SEG
    ))
    trampoline.extend(bytes.fromhex("0B C0 74 05 E9 A5 01 90 90"))
    patch_at(
        data,
        header_size + GAME_AUDIO_SEG * 16 + 0x03AC,
        bytes(trampoline),
    )

    # Both paths now call a dispatcher; it selects gusStartVoice or the original
    # mcpStartVoice at runtime.
    patch_at(
        data,
        header_size + GAME_AUDIO_SEG * 16 + 0x058E,
        bytes.fromhex("EB 00"),
    )
    start_call = b"\x9A" + struct.pack(
        "<HH", STUB_OFFSET + labels["start_dispatch"], STUB_SEG
    )
    patch_at(
        data,
        header_size + GAME_AUDIO_SEG * 16 + 0x0590,
        start_call,
    )

    # The existing GUS cleanup flag now reaches the safe wrapper, which also
    # closes the GUS DRAM heap.
    shutdown_call = b"\x9A" + struct.pack(
        "<HH", STUB_OFFSET + labels["shutdown_dispatch"], STUB_SEG
    )
    patch_at(
        data,
        header_size + GAME_AUDIO_SEG * 16 + 0x0786,
        shutdown_call,
    )

    data[stub_file_offset:stub_end] = stub

    # Replace the relocation for the reclaimed SDI_DAC segment immediate with
    # one for the new far call, then add relocations for every far call in the
    # dispatch stub.  Existing start/cleanup call sites retain their records.
    reclaimed_reloc = (0x03B0, GAME_AUDIO_SEG)
    if relocs.count(reclaimed_reloc) != 1:
        raise ValueError("expected exactly one relocation in reclaimed switch case")
    relocs[relocs.index(reclaimed_reloc)] = (0x03AF, GAME_AUDIO_SEG)
    relocs.extend(
        (STUB_OFFSET + word_offset, STUB_SEG)
        for word_offset in stub_far_segment_words
    )

    relocation_end = relocation_table + len(relocs) * 4
    if relocation_end > header_size:
        raise ValueError("MZ relocation table no longer fits in the header")
    p16(data, 0x06, len(relocs))
    for index, (offset, segment) in enumerate(relocs):
        struct.pack_into("<HH", data, relocation_table + index * 4, offset, segment)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return {
        "input_sha256": digest,
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "output_size": len(data),
        "stub_file_offset": stub_file_offset,
        "stub_segment": STUB_SEG,
        "stub_offset": STUB_OFFSET,
        "relocations": len(relocs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="unmodified supported ALADDIN.EXE")
    parser.add_argument("destination", type=Path, help="path for patched executable")
    parser.add_argument(
        "--sound-cfg",
        type=Path,
        help="also write a GUS SOUND.CFG",
    )
    parser.add_argument(
        "--ultrasnd",
        help=("GUS resources as port,dma1,dma2,irq1,irq2; "
              "defaults to the ULTRASND environment variable"),
    )
    args = parser.parse_args()
    details = patch_executable(args.source, args.destination)
    if args.sound_cfg is not None:
        ultrasnd = args.ultrasnd or os.environ.get("ULTRASND")
        if not ultrasnd:
            parser.error("--sound-cfg requires --ultrasnd or ULTRASND")
        sound_cfg = build_sound_cfg(ultrasnd)
        args.sound_cfg.parent.mkdir(parents=True, exist_ok=True)
        args.sound_cfg.write_bytes(sound_cfg)
        details["ultrasnd"] = ultrasnd
        details["sound_cfg_sha256"] = hashlib.sha256(sound_cfg).hexdigest()
    for key, value in details.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
