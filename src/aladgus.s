.intel_syntax noprefix
.code16

.section .text
.global _start

/*
 * ALADGUS.COM - source-only DOS installer/configurator for the exact
 * supported Aladdin executable.
 *
 * The program contains only patch-owned replacement bytes.  It validates the
 * user's executable by size and CRC-32, patches it in place, and constructs
 * SOUND.CFG from ULTRASND=port,dma1,dma2,irq1,irq2.
 */

_start:
    cld
    push cs
    pop ds
    push cs
    pop es

    mov byte ptr [config_only], 0
    call parse_command_line

    lea dx, [msg_banner]
    call print_dollar

    call read_ultrasnd
    jnc resources_ok
    lea dx, [msg_ultrasnd]
    call print_dollar
    jmp exit_error

resources_ok:
    cmp byte ptr [config_only], 0
    jne write_configuration
    call patch_game
    jc exit_error

write_configuration:
    call write_sound_cfg
    jnc install_ok
    lea dx, [msg_cfg_error]
    call print_dollar
    jmp exit_error

install_ok:
    lea dx, [msg_cfg_ok]
    call print_dollar
    mov ax, 0x4c00
    int 0x21

exit_error:
    mov ax, 0x4c01
    int 0x21


/* Set config_only for /C or -C. */
parse_command_line:
    xor cx, cx
    mov cl, byte ptr [0x80]
    mov si, 0x81
command_scan:
    jcxz command_done
    lodsb
    dec cx
    cmp al, '/'
    je command_option
    cmp al, '-'
    jne command_scan
command_option:
    jcxz command_done
    mov al, byte ptr [si]
    and al, 0xdf
    cmp al, 'C'
    jne command_scan
    mov byte ptr [config_only], 1
command_done:
    ret


/* Locate and parse ULTRASND in the inherited DOS environment. */
read_ultrasnd:
    push es
    push si
    push di
    push bx
    push cx
    push dx

    mov ax, word ptr [0x2c]
    or ax, ax
    jz ultrasnd_not_found
    mov es, ax
    xor di, di

environment_next:
    cmp byte ptr es:[di], 0
    jne environment_compare
    cmp byte ptr es:[di + 1], 0
    je ultrasnd_not_found
    inc di
    jmp environment_next

environment_compare:
    push di
    lea si, [env_name]
    mov cx, 9
environment_compare_byte:
    mov al, byte ptr [si]
    mov ah, byte ptr es:[di]
    cmp ah, 'a'
    jb environment_compare_ready
    cmp ah, 'z'
    ja environment_compare_ready
    sub ah, 32
environment_compare_ready:
    cmp al, ah
    jne environment_no_match
    inc si
    inc di
    loop environment_compare_byte
    add sp, 2
    jmp environment_parse

environment_no_match:
    pop di
environment_skip:
    cmp byte ptr es:[di], 0
    je environment_skipped
    inc di
    jmp environment_skip
environment_skipped:
    inc di
    jmp environment_next

environment_parse:
    call parse_hex_comma
    jc ultrasnd_invalid
    cmp ax, 0x0100
    jb ultrasnd_invalid
    cmp ax, 0x03f0
    ja ultrasnd_invalid
    test ax, 0x000f
    jnz ultrasnd_invalid
    mov word ptr [sound_cfg + 0x23], ax

    mov dl, ','
    call parse_decimal
    jc ultrasnd_invalid
    call validate_dma
    jc ultrasnd_invalid
    mov byte ptr [sound_cfg + 0x26], al

    mov dl, ','
    call parse_decimal
    jc ultrasnd_invalid
    call validate_dma
    jc ultrasnd_invalid
    mov byte ptr [sound_cfg + 0x2e], al

    mov dl, ','
    call parse_decimal
    jc ultrasnd_invalid
    call validate_irq
    jc ultrasnd_invalid
    mov byte ptr [sound_cfg + 0x25], al

    xor dl, dl
    call parse_decimal
    jc ultrasnd_invalid
    call validate_irq
    jc ultrasnd_invalid
    mov byte ptr [sound_cfg + 0x2f], al

    clc
    jmp ultrasnd_return

ultrasnd_not_found:
ultrasnd_invalid:
    stc
ultrasnd_return:
    pop dx
    pop cx
    pop bx
    pop di
    pop si
    pop es
    ret


/* Parse 1-4 hexadecimal digits followed by a comma from ES:DI. */
parse_hex_comma:
    push bx
    push cx
    xor ax, ax
    xor cx, cx
hex_loop:
    mov bl, byte ptr es:[di]
    cmp bl, ','
    je hex_done
    cmp bl, '0'
    jb hex_error
    cmp bl, '9'
    jbe hex_numeric
    and bl, 0xdf
    cmp bl, 'A'
    jb hex_error
    cmp bl, 'F'
    ja hex_error
    sub bl, 'A' - 10
    jmp hex_digit_ready
hex_numeric:
    sub bl, '0'
hex_digit_ready:
    cmp cx, 4
    jae hex_error
    shl ax, 1
    shl ax, 1
    shl ax, 1
    shl ax, 1
    xor bh, bh
    add ax, bx
    inc di
    inc cx
    jmp hex_loop
hex_done:
    or cx, cx
    jz hex_error
    inc di
    clc
    jmp hex_return
hex_error:
    stc
hex_return:
    pop cx
    pop bx
    ret


/* Parse decimal digits followed by delimiter DL from ES:DI. */
parse_decimal:
    push bx
    push cx
    push dx
    mov dh, dl
    xor ax, ax
    xor cx, cx
decimal_loop:
    mov bl, byte ptr es:[di]
    cmp bl, dh
    je decimal_done
    cmp bl, '0'
    jb decimal_error
    cmp bl, '9'
    ja decimal_error
    sub bl, '0'
    xor bh, bh
    push bx
    mov bx, ax
    shl ax, 1
    shl bx, 1
    shl bx, 1
    shl bx, 1
    add ax, bx
    pop bx
    add ax, bx
    cmp ax, 255
    ja decimal_error
    inc di
    inc cx
    jmp decimal_loop
decimal_done:
    or cx, cx
    jz decimal_error
    cmp dh, 0
    je decimal_success
    inc di
decimal_success:
    clc
    jmp decimal_return
decimal_error:
    stc
decimal_return:
    pop dx
    pop cx
    pop bx
    ret

validate_dma:
    cmp ax, 7
    ja resource_invalid
    cmp ax, 4
    je resource_invalid
    clc
    ret

validate_irq:
    cmp ax, 2
    jb resource_invalid
    cmp ax, 15
    ja resource_invalid
    clc
    ret

resource_invalid:
    stc
    ret


/* Validate and patch ALADDIN.EXE. */
patch_game:
    call open_game
    jc patch_open_error

    mov bx, word ptr [file_handle]
    xor cx, cx
    xor dx, dx
    mov ax, 0x4202
    int 0x21
    jc patch_io_error_close
    cmp dx, 0x0002
    jne patch_unsupported_close
    cmp ax, 0x6178
    jne patch_unsupported_close

    call crc_file
    jc patch_io_error_close
    cmp eax, 0x2e54c424
    je patch_already_close
    cmp eax, 0x70da4da8
    je patch_already_close
    cmp eax, 0xf05135f0
    je patch_apply
    jmp patch_unsupported_close

patch_apply:
    call write_patch_records
    jc patch_io_error_close
    call close_game
    jc patch_io_error

    call open_game
    jc patch_open_error
    call crc_file
    jc patch_io_error_close
    cmp eax, 0x2e54c424
    jne patch_verify_error_close
    call close_game
    jc patch_io_error
    lea dx, [msg_patched]
    call print_dollar
    clc
    ret

patch_already_close:
    call close_game
    lea dx, [msg_already]
    call print_dollar
    clc
    ret

patch_open_error:
    lea dx, [msg_open_error]
    call print_dollar
    stc
    ret

patch_unsupported_close:
    call close_game
    lea dx, [msg_unsupported]
    call print_dollar
    stc
    ret

patch_verify_error_close:
    call close_game
    lea dx, [msg_verify_error]
    call print_dollar
    stc
    ret

patch_io_error_close:
    call close_game
patch_io_error:
    lea dx, [msg_io_error]
    call print_dollar
    stc
    ret


open_game:
    lea dx, [game_name]
    mov ax, 0x3d02
    int 0x21
    jc open_game_return
    mov word ptr [file_handle], ax
open_game_return:
    ret

close_game:
    mov bx, word ptr [file_handle]
    mov ah, 0x3e
    int 0x21
    ret


/* Return the CRC-32 of the open file in EAX. */
crc_file:
    mov bx, word ptr [file_handle]
    xor cx, cx
    xor dx, dx
    mov ax, 0x4200
    int 0x21
    jc crc_error
    mov dword ptr [crc_value], 0xffffffff

crc_read:
    mov bx, word ptr [file_handle]
    mov ah, 0x3f
    mov cx, 1024
    lea dx, [io_buffer]
    int 0x21
    jc crc_error
    or ax, ax
    jz crc_done
    mov bp, ax
    lea si, [io_buffer]

crc_byte:
    mov eax, dword ptr [crc_value]
    xor al, byte ptr [si]
    mov cx, 8
crc_bit:
    shr eax, 1
    jnc crc_no_xor
    xor eax, 0xedb88320
crc_no_xor:
    loop crc_bit
    mov dword ptr [crc_value], eax
    inc si
    dec bp
    jnz crc_byte
    jmp crc_read

crc_done:
    mov eax, dword ptr [crc_value]
    not eax
    clc
    ret
crc_error:
    stc
    ret


write_patch_records:
    lea si, [patch_table]
    mov di, 9
patch_record_loop:
    push di
    call write_patch_record
    pop di
    jc patch_records_error
    dec di
    jnz patch_record_loop
    clc
    ret
patch_records_error:
    stc
    ret


/* Record: dword file offset, word length, word data address. */
write_patch_record:
    mov dx, word ptr [si]
    mov cx, word ptr [si + 2]
    mov bx, word ptr [file_handle]
    mov ax, 0x4200
    int 0x21
    jc write_record_error

    mov cx, word ptr [si + 4]
    mov dx, word ptr [si + 6]
    mov bx, word ptr [file_handle]
    mov ah, 0x40
    int 0x21
    jc write_record_error
    cmp ax, cx
    jne write_record_error
    add si, 8
    clc
    ret
write_record_error:
    stc
    ret


write_sound_cfg:
    lea dx, [cfg_name]
    xor cx, cx
    mov ah, 0x3c
    int 0x21
    jc sound_cfg_error
    mov bx, ax
    mov ah, 0x40
    mov cx, 54
    lea dx, [sound_cfg]
    int 0x21
    jc sound_cfg_close_error
    cmp ax, 54
    jne sound_cfg_close_error
    mov ah, 0x3e
    int 0x21
    jc sound_cfg_error
    clc
    ret
sound_cfg_close_error:
    pushf
    mov ah, 0x3e
    int 0x21
    popf
sound_cfg_error:
    stc
    ret


print_dollar:
    mov ah, 0x09
    int 0x21
    ret


.align 2
file_handle:
    .word 0
crc_value:
    .long 0
config_only:
    .byte 0

env_name:
    .ascii "ULTRASND="
game_name:
    .asciz "ALADDIN.EXE"
cfg_name:
    .asciz "SOUND.CFG"

msg_banner:
    .ascii "Aladdin GUS installer/configurator 1.1\r\n$"
msg_ultrasnd:
    .ascii "ERROR: Set ULTRASND=port,dma1,dma2,irq1,irq2 first.\r\n$"
msg_open_error:
    .ascii "ERROR: Cannot open ALADDIN.EXE for update.\r\n$"
msg_unsupported:
    .ascii "ERROR: Unsupported ALADDIN.EXE build or damaged file.\r\n$"
msg_io_error:
    .ascii "ERROR: Disk I/O failed while patching ALADDIN.EXE.\r\n$"
msg_verify_error:
    .ascii "ERROR: Patched-file verification failed; use RESTORE.BAT.\r\n$"
msg_patched:
    .ascii "ALADDIN.EXE patched successfully.\r\n$"
msg_already:
    .ascii "ALADDIN.EXE is already patched.\r\n$"
msg_cfg_error:
    .ascii "ERROR: Could not create SOUND.CFG.\r\n$"
msg_cfg_ok:
    .ascii "SOUND.CFG written from ULTRASND.\r\n$"


/* Packed 54-byte SOUNDCARD structure. Resource fields are filled at runtime. */
sound_cfg:
    .byte 10
    .word 0x0100
    .ascii "Gravis Ultrasound"
    .space 15, 0
    .word 0x0000
    .byte 0
    .byte 0
    .word 19293
    .word 44100
    .byte 1
    .byte 1
    .byte 1
    .byte 0
    .byte 0
    .byte 1
    .byte 1
    .space 4, 0
sound_cfg_end:


/* Patch-owned bytes and MZ relocation updates. */
patch_count:
    .byte 0x92, 0x01
patch_reclaimed_relocation:
    .byte 0xaf, 0x03, 0xd7, 0x19
patch_added_relocations:
    .byte 0x14, 0x01, 0xbe, 0x1f, 0x1c, 0x01, 0xbe, 0x1f
    .byte 0x21, 0x01, 0xbe, 0x1f, 0x32, 0x01, 0xbe, 0x1f
    .byte 0x59, 0x01, 0xbe, 0x1f, 0x65, 0x01, 0xbe, 0x1f
    .byte 0x78, 0x01, 0xbe, 0x1f, 0x7d, 0x01, 0xbe, 0x1f
patch_gus_route:
    .byte 0xe9, 0xba, 0x00
patch_trampoline:
    .byte 0x9a, 0x00, 0x01, 0xbe, 0x1f, 0x0b, 0xc0
    .byte 0x74, 0x05, 0xe9, 0xa5, 0x01, 0x90, 0x90
patch_start_skip:
    .byte 0xeb, 0x00
patch_start_call:
    .byte 0x9a, 0x4f, 0x01, 0xbe, 0x1f
patch_shutdown_call:
    .byte 0x9a, 0x68, 0x01, 0xbe, 0x1f
patch_dispatch_stub:
    .byte 0x80,0x3e,0x76,0x20,0x0a,0x75,0x39,0x2e
    .byte 0xc6,0x06,0x86,0x01,0x00,0x1e,0x68,0x76
    .byte 0x20,0x9a,0x36,0x05,0xd9,0x21,0x83,0xc4
    .byte 0x04,0x9a,0x17,0x01,0x3b,0x23,0x9a,0x00
    .byte 0x00,0x8f,0x23,0x6a,0x00,0x6a,0x1f,0x6a
    .byte 0x00,0x6a,0x00,0x1e,0x68,0xa5,0x14,0x9a
    .byte 0x24,0x00,0x8f,0x23,0x83,0xc4,0x0c,0x83
    .byte 0x0e,0x6e,0x1c,0x02,0xb8,0x01,0x00,0xcb
    .byte 0xc7,0x06,0xc2,0x1c,0xbe,0x1f,0xc7,0x06
    .byte 0xc0,0x1c,0x5e,0x04,0x33,0xc0,0xcb,0x80
    .byte 0x3e,0x76,0x20,0x0a,0x75,0x0c,0x9a,0xc0
    .byte 0x04,0xd9,0x21,0x2e,0xc6,0x06,0x86,0x01
    .byte 0x01,0xcb,0x9a,0xea,0x26,0xf2,0x1c,0xcb
    .byte 0x2e,0x80,0x3e,0x86,0x01,0x00,0x75,0x05
    .byte 0xc6,0x06,0x7c,0x14,0x00,0x9a,0xfe,0x06
    .byte 0xd9,0x21,0x9a,0x19,0x02,0x3b,0x23,0x2e
    .byte 0xc6,0x06,0x86,0x01,0x00,0xcb,0x00
    .ascii "ALADDIN GUS PATCH 1.1"
    .byte 0
patch_dispatch_stub_end:

patch_table:
    .long 0x00000006
    .word 2
    .word patch_count
    .long 0x000000f6
    .word 4
    .word patch_reclaimed_relocation
    .long 0x00000666
    .word 32
    .word patch_added_relocations
    .long 0x0001a85f
    .word 3
    .word patch_gus_route
    .long 0x0001a91c
    .word 14
    .word patch_trampoline
    .long 0x0001aafe
    .word 2
    .word patch_start_skip
    .long 0x0001ab00
    .word 5
    .word patch_start_call
    .long 0x0001acf6
    .word 5
    .word patch_shutdown_call
    .long 0x000204e0
    .word patch_dispatch_stub_end - patch_dispatch_stub
    .word patch_dispatch_stub

.align 2
io_buffer:
    .space 1024, 0
