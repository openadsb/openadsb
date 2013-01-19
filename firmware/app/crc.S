# From http://miniadsb.web99.de/
# calc parity for Mode S
# Implementation for AVR processors 
.include "m48def.inc"

.MACRO XLDI                  ;Start macro definition
        ldi r16,@1        
        mov @0,r16         
.ENDMACRO                    ;End macro definition


;Test patterns
;==============
test88:
    ldi     r16,high(RAMEND)    ;init stack
    out     SPH,r16
    ldi     r16,low(RAMEND)
    out     SPL,r16

    rcall  setup

;5D 3C6614 => C315D2
    xldi    r0,0x5D
    xldi    r1,0x3C
    xldi    r2,0x66
    xldi    r3,0x14
    rcall  crc32

;8F 45AC52 60BDF348222A58 => B98284
    xldi    r0,0x8F
    xldi    r1,0x45
    xldi    r2,0xAC
    xldi    r3,0x52
    xldi    r4,0x60
    xldi    r5,0xBD
    xldi    r6,0xF3
    xldi    r7,0x48
    xldi    r8,0x22
    xldi    r9,0x2A
    xldi    r10,0x58
    rcall  crc88

test881:
    rjmp   test881

;setup CRC constant FFFA0480
;============================
setup:
    xldi    r11,0xff
    xldi    r12,0xfa
    xldi    r13,0x04
    xldi    r14,0x80
    ret

;CRC32 - calculate a CRC value for a 56-bit message (over 32-bit)
;================================================================
;Input: r0..r3, r11..r14
;Output: r0..r2
;Used: r16
;Duration: 50% 0/1 = 32x10+16x4+1=365 cycles = 18.25 µs @ 20 MHz clock
crc32:
    ldi    r16,32    ;1
crc322:
    sbrs   r0,7      ;2
    rjmp   crc321
    eor    r0,r11    ;1
    eor    r1,r12    ;1
    eor    r2,r13    ;1
    eor    r3,r14    ;1
crc321: 
    clc              ;1
    rol    r3        ;1
    rol    r2        ;1
    rol    r1        ;1
    rol    r0        ;1
    dec    r16       ;1
    brne   crc322    ;2
   ret

;CRC88 - calculate a CRC value for a 112-bit message (over 88-bit)
;=================================================================
;Input: r0..r10, r11..r14
;Output: r0..r2
;Used: r16
;Duration: 50% 0/1 = 88x14+44x4+1= 1409 cycles = 70,45 cycles
crc88:
    ldi    r16,88
crc882:
    sbrs   r0,7
    rjmp   crc881
    eor    r0,r11
    eor    r1,r12
    eor    r2,r13
    eor    r3,r14
crc881:    clc
    rol    r10
    rol    r9
    rol    r8
    rol    r7
    rol    r6
    rol    r5
    rol    r4
    rol    r3
    rol    r2
    rol    r1
    rol    r0
    dec    r16
    brne   crc882
    ret    

