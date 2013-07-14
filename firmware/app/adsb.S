; Mode S (and hopefully A/C, TACAN/DME) decoding in assembly.  
; B. Kuschak 5/2012 
;
; Based on adsb.asm by Edward. http://www.lll.lu/~edward/edward/adsb/VerySimpleADSBreceiver.html
; 
; Assumptions:
; Running on Xmega
; ACA0 comparator is input bit sampler
; if clkcpu is 20 MHz (1 cycle is 50 nsec), 10 cycles per 500 nsec ADS-B half-bit period
; if clkcpu is 24 MHz (1 cycle is 41.7 nsec), 12 cycles per 500 nsec ADS-B half-bit period
; if clkcpu is 32 MHz (1 cycle is 31.25 nsec), 16 cycles per 500 nsec ADS-B half-bit period
; 
; Calling convention: 
;	Scratch registers:   R18-R27, R30-R31
;	Preserved registers: R2-R17, R28-R29
;	Input Parameter registers: R8-R25 (2-,4-, or 8- byte alignment) (R25 downwards?)
;	Return registers:    R18-R25 (up to 64-bit) (R25 downwards?)

;.include "m48def.inc"

#define EXT_SQUITTER	14
#define SHORT_SQUITTER	7

.extern	adsb_buf
.extern bad_short_pkts			# failed after preamble, before 56 bits 
.extern bad_long_pkts			# failed after 56 bits, before 112 bits

; -----------------------------------------------------------
; MACROS:
;   Quick nops with little memory (words) , some destroy R0
; -----------------------------------------------------------

.macro	nops1
	nop
.endm

.macro	nops2
	nop
	nop
.endm

.macro	nops3
	lpm				; 3 x nop
.endm

.macro	nops4
	lpm				; 3 x nop
	nop
.endm

.macro	nops5
	lpm				; 3 x nop
	nop
	nop
.endm

.macro	nops6
	lpm				; 3 x nop
	lpm				; 3 x nop
.endm

.macro	nops7
	lpm				; 3 x nop
	lpm				; 3 x nop
	nop
.endm

.macro	nops8
	lpm				; 3 x nop
	lpm				; 3 x nop
	nop
	nop
.endm

.macro	nops10
	lpm				; 3 x nop
	lpm				; 3 x nop
	lpm				; 3 x nop
	nop
.endm

; -----------------------------------------------------------
; -----------------------------------------------------------
; -----------------------------------------------------------


; ---
; This routine decodes ADS-B messages bit by bit
; ---
; PPM (manchester) encoded.  HI in first half-bit means 1, HI in second half-bit means 0.  Preamble is special.
; Data input: _-_-____-_-______AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQRRSSTTUUVVWWXXYYZZ...
; Half-bits:  X01234567890123456789012345678901234567890123456789012345678901234567...
; Bits:        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 ...
; Decoded:      1 1 X 0 0 X X X A B C D E F G H I J K L M N O P Q R S T U V W X Y Z ...
; 
; expects TCC0 to be running, and OVFIF flag to be clear upon entry.
; Returns 0 if TCCO overflows (timeout)
; Returns (number of bytes) >1 if packet received (fixme - need bitfield for packet type also?)
; FIXME - allow multiple packets (each prefixed with byte count?) until buffer full

.section .text
.global decode_adsb

decode_adsb:
	push	r16
	push	r17
	push	r23
	push	r24
	push	r25
	push	r26
	push	r27
try_again:
	ldi	r16,2				; Green LED
	ldi 	r27,hi8(adsb_buf)		; buffer address in X ptr
	ldi 	r26,lo8(adsb_buf)
	adiw	r26,8				; advance 8 bytes to skip header area
look_for_more:
	ldi 	r25,EXT_SQUITTER+1		; As DEC and BREQ is done at first Manchester bit, need +1
	;ldi 	r25,7+1		; As DEC and BREQ is done at first Manchester bit, need +1
	rjmp	edge_det

ret_timeout:
	sts	PORTB_OUTSET,r19		; LED off (line hi), 2 cycles
	pop	r27
	pop	r26
	pop	r25
	pop	r24
	pop	r23
	pop	r17
	pop	r16
	ldi	r24,0				; zero means timeout - no bytes received
						; FIXME - don't return zero, return total byte count
	ret

;--------------------------------------------------------
; EDGE DETECT with comparator
;--------------------------------------------------------
; Input is ACA_STATUS,AC_AC0STATE_bp
; Start by detecting edge of first pulse
edge_det:
	;ldi	r16,2				; Green LED
	ldi	r16,0				; nothing
	ldi	r19,2				; green led
	;sts	PORTB_OUTSET,r16		; LED off (line hi), 2 cycles
	sts	PORTB_OUTSET,r19		; LED off (line hi), 2 cycles
edge_loop:
	lds	r23,ACA_STATUS			; 2 cycles

	; bounce out every time the timer overflows
	lds	r24,TCC0_INTFLAGS		; 2 cycles
	sbrc	r24,TC0_OVFIF_bp		; 2 cycles if skip
	rjmp	ret_timeout

	sbrs	r23,AC_AC0STATE_bp		; 1 cycle if no-skip, 2 cycles if skip (jump 1 word)
	rjmp	edge_loop			; 2 cycles

; SYNC DETECT
;--------------------------------------------------------
;	Each Section starts with sample of Comparator and has 10 cycles total
;	16 checks for sync = 1010000101000000
;   At a later stage maybe decode mode A and C
;--------------------------------------------------------
	lds	r23,ACA_STATUS					; 2
	sts	PORTB_OUTCLR,r19		; 2, LED on
	;sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrs	r23,AC_AC0STATE_bp				; Check for 1, 2 cycles if skip
	rjmp	edge_det					; 2 cycles 
	nops3
	;nops8
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det		; ok wasn't mode s or mode a/c - split to parallel track checking for tcan/dme
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrs	r23,AC_AC0STATE_bp				; Check for 1
	rjmp	edge_det		; ok wasn't mode s, fixme - split to parallel track, checking for mode c pulse
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS			
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10				
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrs	r23,AC_AC0STATE_bp				; Check for 1
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrs	r23,AC_AC0STATE_bp				; Check for 1
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS		
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det	
	nops10		
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS
	sts	PORTB_OUTTGL,r16				; toggle LED, 2 cycles
	sbrc	r23,AC_AC0STATE_bp				; Check for 0
	rjmp	edge_det
	nops10
;--------------------------------------------------------
	lds	r23,ACA_STATUS					; 2 cycles
	sts	PORTB_OUTTGL,r16				; 2 cycles toggle LED
	sbrc	r23,AC_AC0STATE_bp				; 2 cycles if skip
	rjmp	edge_det					; skip 1 word
	nops8
	rjmp	manchester_decode				; 2 cycles
;--------------------------------------------------------

goto_ext_squitter_done:
	rjmp	ext_squitter_done				; to handle branch relative limitation

;--------------------------------------------------------
; Preamble received, now decode frame ...
; first bit position in byte register r24 is AC_AC0STATE_bp
; breq can only jump +/- 64 bytes, so need to insert some intermediates
;--------------------------------------------------------

manchester_decode:
;--------------------------------------------------------
; 1st manchester is bit no 7 (MSB)
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2 cycle - Sample Signal
	sts	PORTB_OUTTGL,r16			; toggle LED, 2 cycles
	andi	r23,(1 << AC_AC0STATE_bp)		; 1 cycle - Mask first half of manchester into R16
	eor	r24,r24					; 1 cycle - clear r24, accumulator
	dec	r25					; 1 cycle - does not affect carry - check for done here adding 1 loop - 
	breq	goto_ext_squitter_done			; 1 cycle -   to r25 as no room left at end of decode loop
	nops8						; 10 cycles
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2 cycle - Sample Signal
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1 cycle - Mask 2nd half of manchester into r17
	eor	r17,r23					; 1 cycle - exor check valid, destroying r17, r23 has bit value
	breq	check_short				; 1 skipped, 2 taken - No toggle of bit is error 
							; (error on first bit may be short squitter)
	nop						; 1 cycle
	nop						; 1 cycle
	rjmp	next					; 2 cycles
check_short:
	cpi	r25,(EXT_SQUITTER-SHORT_SQUITTER)	; 1 cycle - 7 bytes received?
	;breq	next					; 1 skipped, 2 taken
	brne	mdecode_errex2				; 1 skipped, 2 taken - not 7, must be error
	rjmp	short_squitter_done			; 1 cycle 
next:
	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x80				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x80				; 1 cycle
	nop
	;nops3						; 3 cycles
;--------------------------------------------------------
; 2nd manchester is bit no 6
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2 cycle
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r23,(1 << AC_AC0STATE_bp)		; 1 cycle
	nops10						; 2 cycles
	nop						; 7 cycles
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2 cycle
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1 cycle
	eor	r17,r23					; 1 cycle - exor check valid destroying r17
	breq	mdecode_errex2				; 1 cycle - No toggle of bit is error (real error)
	;rol	r24					; 1 cycle - now R19 = o7oooooX and C = o
	;or	r24,r23					; 1 cycle - now R19 = o76ooooX and C = o

	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x40				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x40				; 1 cycle
	nops5						; 4 cycles
;--------------------------------------------------------
; 3rd manchester is bit no 5
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2 cycles
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r23,(1 << AC_AC0STATE_bp)		; 1 cycle
	nops10						; 10 cycles
	nop						; 1
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1
	eor	r17,r23					; 1
mdecode_errex2:
	breq	mdecode_errex3				; 1
	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x20				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x20				; 1 cycle
	nops5						; 4 cycles
;--------------------------------------------------------
; 4th manchester is bit no 4
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r23,(1 << AC_AC0STATE_bp)		; 1
	nops10						; 10 cycles
	nop						; 1
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1
	eor	r17,r23					; 1
	breq	mdecode_errex3				; 1 - No toggle of bit is error
	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x10				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x10				; 1 cycle
	nops5						; 4 cycles
;--------------------------------------------------------
; 5th manchester is bit no 3
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r23,(1 << AC_AC0STATE_bp)		; 1
	nops10						; 10 cycles
	nop						; 1
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1
	eor	r17,r23					; 1
mdecode_errex3:
	breq	mdecode_errex				; 1
	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x08				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x08				; 1 cycle
	nops5						; 2 cycles
;--------------------------------------------------------
; 6th manchester is bit no 2
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r23,(1 << AC_AC0STATE_bp)		; 1
	nops10						; 10 cycles
	nop						; 1
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1
	eor	r17,r23					; 1
mdecode_errex:						; Extend error jump for 2nd manchester (Flag test will be same)
	breq	mdecode_error				; 1
	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x04				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x04				; 1 cycle
	nops5						; 2 cycles
;--------------------------------------------------------
; 7th manchester is bit no 1
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r23,(1 << AC_AC0STATE_bp)		; 1
	nops10						; 10 cycles
	nop						; 1
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1
	eor	r17,r23					; 1
	breq	mdecode_error				; 1
	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x02				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x02				; 1 cycle
	nops5						; 2 cycles
;--------------------------------------------------------
; 8th manchester is bit no 0 - Lots to do as storing R19
;--------------------------------------------------------
	lds	r23,ACA_STATUS				; 2
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r23,(1 << AC_AC0STATE_bp)		; 1
	nops10						; 10 cycles
	nop						; 1
;--------------------------------------------------------
	lds	r17,ACA_STATUS				; 2 cycle
	sts	PORTB_OUTTGL,r16			; 2 cycles - toggle LED
	andi	r17,(1 << AC_AC0STATE_bp)		; 1 cycle
	eor	r17,r23					; 1 cycle
	breq	mdecode_error				; 1 cycle
	sbrc	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	sbr	r24,0x01				; 1 cycle
	sbrs	r23,AC_AC0STATE_bp			; 1 no skip, 2 skip
	cbr	r24,0x01				; 1 cycle
	nop
	;st	x+,r24					; 2 cycles
	st	x+,r24					; 1 cycles on xmega
	nop						; 1 cycles
	rjmp	manchester_decode			; 2 cycles	- bk fixme - two cycles over
;--------------------------------------------------------
; End of Manchester Decode Loop
;--------------------------------------------------------


;--------------------------------------------------------
; Error during Manchester Decode Loop
;--------------------------------------------------------
; FIXME - don't return, rather reset pointer and jump to look_for_more
mdecode_error:
	; r25 bytes to go counter > 7 means bad short pkt
	; r25 bytes to go counter < 7 means bad long pkt
	ldi 	r27,hi8(bad_short_pkts)			; first assume it was short pkt
	ldi 	r26,lo8(bad_short_pkts)
	cpi	r25,(EXT_SQUITTER-SHORT_SQUITTER)	; 7 bytes received?
	brge	incr_ctr				; taken if r25 > 7 (was short pkt)
	ldi 	r27,hi8(bad_long_pkts)		
	ldi 	r26,lo8(bad_long_pkts)
incr_ctr:
	ld	r16,x					; increment ctr
	inc	r16
	st	x,r16
	rjmp	ret_timeout				;  testing bk
	;rjmp	try_again				;  testing bk
	
	
; fixme error counters - bad pkt detected- check r25
; 	ldi 	r27,hi8(bad_long_pkts)		 
;	ldi 	r26,lo8(bad_long_pkts)
;	ld	r16,X
;	inc	r16
;	st	r16,X
;


;--------------------------------------------------------
; Successful packet
;--------------------------------------------------------
; FIXME - instead of returning, check if we have buffer space for another
; long squitter.  if not, return total number of bytes (keep in register)
; if so, jump back to look_for_more

short_squitter_done:
	pop	r27
	pop	r26
	pop	r25
	pop	r24
	pop	r23
	pop	r17
	pop	r16
	ldi	r24,7			; return 7 
	ret
	
ext_squitter_done:
	;; bk 
	;ldi	r23,1			; red led
	;sts	PORTB_OUTTGL,r23		; toggle LED, 2 cycles	testing
	pop	r27
	pop	r26
	pop	r25
	pop	r24
	pop	r23
	pop	r17
	pop	r16
	ldi	r24,14			; return 14
	ret


#if 0

; TACAN/DME decoder.  It identifies itself with Morse Code every 37.2 seconds
; pulse width 3.5 +/- 0.5 uS.  Trise/fall = 2.5 +/- 0.5 uS. Period = 12.0 uS
; 3 digit identifier.  Local is 'SJC' DME
; "North burst" is 12+? pulse pairs spaced by 30 uS.
; "Aux rate" is pulse pairs spaced by 24 uS.
; "ID group" - 2 pulse pairs space by 100 uS, repeating every 740.7 uS.


;--------------------------------------------------------
; Finished Decoding Extended Squitter
;--------------------------------------------------------
ext_squitter_done:
;	out 	PORTC,r24		; nop
;	sbi	PORTB_OUT,0			; LED on
	ldi	r16,'*'
	rcall	COUT_0
	ldi 	r27,$02			; ldi X,0h0200
	ldi 	r26,$00
	ldi 	r25,EXT_SQUITTER
serial_loop:
	ld	r16,X+
	rcall	HEXOUT_Reshuffle
	dec	r25
	brne 	serial_loop

	ldi	r16,';'
	rcall	COUT_0
	ldi	r16,10
	rcall	COUT_0
	ldi	r16,13
	rcall	COUT_0
;	cbi	PORTB_OUT,0			; LED off
	rjmp 	decode_adsb
;--------------------------------------------------------


CheckForShort:
	cpi	r25,CHECK_SHORT
	brne 	mdecode_error

	ldi 	r16, 0b00001111		; PC0-3 is HexSwitch Pullup
	out 	PORTC, r16
	sbis 	PINC,0
	rjmp 	decode_adsb
	
	ldi	r16,'*'
	rcall	COUT_0
	ldi 	r27,$02			; ldi X,0h0200
	ldi 	r26,$00
	ldi 	r25,SHORT_SQUITTER
serial_loop2:
	ld	r16,X+
	rcall	HEXOUT_Reshuffle
	dec	r25
	brne 	serial_loop2

	ldi	r16,';'
	rcall	COUT_0
	ldi	r16,10
	rcall	COUT_0
	ldi	r16,13
	rcall	COUT_0
;	cbi	PORTB_OUT,0			; LED off

	rjmp 	decode_adsb



;--------------------------------------------------------
; Serial Character Stuff
;--------------------------------------------------------
#endif

