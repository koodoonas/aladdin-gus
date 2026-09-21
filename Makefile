AS ?= as
LD ?= ld

.PHONY: all audit clean

all: ALADGUS.COM

audit: ALADGUS.COM
	python3 tools/audit_repo.py

build/aladgus.o: src/aladgus.s
	mkdir -p build
	$(AS) --32 -o $@ $<

ALADGUS.COM: build/aladgus.o
	$(LD) -m elf_i386 --oformat binary -Ttext 0x100 -e _start -o $@ $<

clean:
	rm -f ALADGUS.COM build/aladgus.o
