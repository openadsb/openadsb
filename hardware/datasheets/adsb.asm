; RUNNING AT 20 MHz
; 1 Cycle = 50 nsec

; HEX SWITCH SETTINGS:
;----------------------
; 01 Do not print Errors
; 02 Only 112 usec frames



; v06 for simple Baseband receiver using Comparator Input, rewritten with macros
; v07 cleaned up, added docu on PLL

; -----------------------------------------------------------
; -----------------------------------------------------------
; -----------------------------------------------------------

.include "m48def.inc"


.equ	EXTENDED_BYTES = 14
.equ	SHORT_BYTES = 7
.equ	CHECK_SHORT = EXTENDED_BYTES - SHORT_BYTES

; -----------------------------------------------------------
; MACROS:
;   Quick nops with little memory (words) , some destroy R0
; -----------------------------------------------------------

.macro	nops1
	nop
.endmacro

.macro	nops2
	ld		r0,X		; 2 x nop
.endmacro

.macro	nops3
	lpm					; 3 x nop
.endmacro

.macro	nops4
	lpm					; 3 x nop
	nop
.endmacro

.macro	nops5
	lpm					; 3 x nop
	ld		r0,X		; 2 x nop
.endmacro

.macro	nops6
	lpm					; 3 x nop
	lpm					; 3 x nop
.endmacro

.macro	nops7
	lpm					; 3 x nop
	lpm					; 3 x nop
	nop
.endmacro

.macro	nops8
	lpm					; 3 x nop
	lpm					; 3 x nop
	ld		r0,X		; 2 x nop
.endmacro

; -----------------------------------------------------------
; -----------------------------------------------------------
; -----------------------------------------------------------


.CSEG 


	ldi	r16,high(RAMEND)
	out SPH,r16
	ldi r16,low(RAMEND)
	out SPL,r16


; *** Init I2C to 50kHz

	ldi r16,0
	sts TWSR,r16
	ldi r16,192
	sts TWBR,r16
	ldi r16,4
	sts TWCR,r16

; *** Init Serial ***

   ldi      r16,21
   ldi      r17,0
   sts   UBRR0H,r17         ;baud register high
   sts   UBRR0L,r16            ;baud register low   
   ldi      r16,(1<<RXEN0)|(1<<TXEN0)      
;   ldi      r16,(1<<TXEN0)      
   sts   UCSR0B,r16            ;enable bits 
	ldi		r16,(1<<UCSZ00)|(1<<UCSZ01)
    sts     UCSR0C,r16                  ; 1 stop, 8 bit
	ldi		r16,(1<<U2X0)
    sts     UCSR0A,r16                  ; Double Speed


	ldi r16, 0b00000000				; PB0 is input
	out DDRB, r16

	ldi r16, 0b00000000				; PC0-3 is HexSwitch
	out DDRC, r16
	ldi r16, 0b00001111				; PC0-3 is HexSwitch Pullup
	out PORTC, r16

									; PD7 and PD6 high Z input for Comparator

	ldi r16, 0b00010000				; PD is input / PD4 is LED
	out DDRD, r16
	ldi r16, 0b00000000				; PD no pullup
	out PORTD, r16

	ldi	r24, 0						; To use for PC5 and PD5-7

	cbi	PORTD,4						; LED off

; *** Wait a bit ***


	ldi r17,255
wlp2:
	ldi r16,255
wlp1:
	dec r16
	brne wlp1
	dec r17
	brne wlp2


; *** Set Freq Tuner to 1090 +/- offset into edge of SAW ***
;
; Tuner is of TSA5055T type. Local Oscillator usually 479.5 MHz higher
; for TV broadcast reception.
; For ADSB tune pulse signal into filter flank of SAW filter
; Example in this case:
; Receive Frequency Wanted = 1090000 kHz
; Filter offset is -16000 kHz (Right into the flank of the SAW)
; SAW Flank Frequency is 1074000 kHz
; SAW Center Freuqency is usually 479500 kHz for Sat FM
; Local Oscillator needs to be 1074000 + 479500 = 1553500 kHz
; Note: Making offset positive, you need to change Comparator
;       pins as signal is inverted.
; PLL works in 125 kHz steps, 1553500 kHz / 125 = 12428
; 12428 = 0x308C 

; First Byte is I2C address of TSA5055T = 0b11000010 = 0xC2
; Second Byte is Higher Part of Divider, so 0x30
; Third Byte is Lower Part of Divider, so 0x8C
; Fourth Byte is Ports and Controls, this is fixed to 0x8E

	ldi	r16	,(1<<TWINT)|(1<<TWSTA)|(1<<TWEN)	;send START condition
	sts	TWCR	,r16

twi_1:
	lds	r16	,TWCR
	sbrs	r16	,TWINT
	rjmp	twi_1								; wait for START end


	ldi	r18	,0xC2								; send 0xC2
	sts	TWDR	,r18
	ldi	r18	,(1<<TWINT)|(1<<TWEN)
	sts	TWCR	,r18
twi_2:
	lds	r18	,TWCR
	sbrs	r18	,TWINT
	rjmp	twi_2


	ldi	r18	,0x30								; send 0x30
	sts	TWDR	,r18
	ldi	r18	,(1<<TWINT)|(1<<TWEN)
	sts	TWCR	,r18
twi_3:
	lds	r18	,TWCR
	sbrs	r18	,TWINT
	rjmp	twi_3


;	ldi	r18	,0x8C								; send 0x8C (for BSKE5-101A)
	ldi r18 ,0xBC								; send 0xBC (for SF1218C MK2)
	sts	TWDR	,r18
	ldi	r18	,(1<<TWINT)|(1<<TWEN)
	sts	TWCR	,r18
twi_4:
	lds	r18	,TWCR
	sbrs	r18	,TWINT
	rjmp	twi_4


	ldi	r18	,0x8E								; send 0x8E
	sts	TWDR	,r18
	ldi	r18	,(1<<TWINT)|(1<<TWEN)
	sts	TWCR	,r18
twi_5:
	lds	r18	,TWCR
	sbrs	r18	,TWINT
	rjmp	twi_5


	ldi	r18	,0x00								; send 0x00 *** NEXT VERSION: what was this / remove ? ***
	sts	TWDR	,r18
	ldi	r18	,(1<<TWINT)|(1<<TWEN)
	sts	TWCR	,r18
twi_6:
	lds	r18	,TWCR
	sbrs	r18	,TWINT
	rjmp	twi_6


	ldi	r18	,(1<<TWINT)|(1<<TWSTO)|(1<<TWEN)	; send STOP
	sts	TWCR	,r18

;--------------------------------------------------------
;--------------------------------------------------------
;--------------------------------------------------------
; MAIN LOOP, always return here
;--------------------------------------------------------
;--------------------------------------------------------
;--------------------------------------------------------
main_loop:
	cbi	PORTD,4						; LED off

	ldi r27,$02						; ldi X,0h0200 Start putting data at 0x0200
	ldi r26,$00

	ldi r25,EXTENDED_BYTES+1		; As DEC and BREQ is done at first Manchester bit, need +1

;--------------------------------------------------------
; EDGE DETECT with comparator
;--------------------------------------------------------
; Input is ACSR,ACO
; Start by detecting edge of first pulse
edge_det:
	in		r23,ACSR	; 1 cycle	
	sbrs	r23,ACO		; 2 cycles (jump 1 word)
	rjmp	edge_det	;     rjmp in loop adds possible delay up to +2 cycles
	nops2				; 2 cycles makes 4 or 4+2=6 so just before / after middle of pulse

; SYNC DETECT
;--------------------------------------------------------
;	Each Section starts with sample of Comparator and has 10 cycles total
;	16 checks for sync = 1010000101000000
;   At a later stage maybe decode mode A and C

;--------------------------------------------------------
	in		r23,ACSR
	sbrs	r23,ACO		; Check for 1
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO		; Check for 0
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrs	r23,ACO		; Check for 1
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO		; Check for 0
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO		; Check for 0
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO		; Check for 0
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR	; 1
	sbrc	r23,ACO		; 2 Check for 0
	rjmp	edge_det
	nops5				; 5
	rjmp sync_cont1		; 2 = total 10 cycles
;--------------------------------------------------------
; Shortcut
;--------------------------------------------------------
mdecode_err1:
	rjmp	CheckForShort
;--------------------------------------------------------
sync_cont1:
	in		r23,ACSR
	sbrs	r23,ACO		; Check for 1
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO		; Check for 0
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrs	r23,ACO		; Check for 1
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO		; Check for 0
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR			; 1 cycle
	sbrc	r23,ACO				; 2 cycles to skip 1 word
	rjmp	edge_det			;             skip 1 word
	nops7						; 7 cycles
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO		; Check for 0
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR
	sbrc	r23,ACO
	rjmp	edge_det
	nops7
;--------------------------------------------------------
	in		r23,ACSR			; 1 cycle
	sbrc	r23,ACO				; 2 cycles to skip 1 word
	rjmp	edge_det			;			  skip 1 word

	sbi		PORTD,4				; 2 cycles

	clc							; 1 cycle (is this necessary, if so for what?, Paranoid for rotates ...)
	nops2						; 2 cycles
	rjmp	manchester_decode	; 2 cycles


;--------------------------------------------------------
; Short Cuts ...
;--------------------------------------------------------

manchester_done_ext:
	rjmp	manchester_done
mdecode_err1_ext:
	rjmp	mdecode_err1


;--------------------------------------------------------
; Decode frame ...
;--------------------------------------------------------
manchester_decode:
;--------------------------------------------------------
; 1st manchester is bit no 7
;--------------------------------------------------------
	in		r16,ACSR			; 1 cycle - Sample Signal
	andi	r16,(1 << ACO)		; 1 cycle - Mask first half of manchester into R16
	eor		r19,r19				; 1 cycle - Clear R19 as bits are ORed into R19
	dec		r25					; 1 cycle - does not affect carry - check for done here adding 1 loop
	breq	manchester_done_ext	; 1 cycle -   to r25 as no room left at end of decode loop
	nops5						; 5 cycles
;--------------------------------------------------------
	in		r17,ACSR			; 1 cycle - Sample Signal
	andi	r17,(1 << ACO)		; 1 cycle - ACO is bit 5 of ACSR
	eor		r17,r16				; 1 cycle - exor check valid destroying r17, r16 has bit value
	breq	mdecode_err1_ext	; 1 cycle - No toggle of bit is error (error on first bit may be short squitter)
	or		r19,r16				; 1 cycle - add to shift register, now R19 = oo7ooooo and C = X
	nops5						; 5 cycles
;--------------------------------------------------------
; 2nd manchester is bit no 6
;--------------------------------------------------------
	in		r16,ACSR			; 1 cycle
	andi	r16,(1 << ACO)		; 1 cycle
	nops8						; 8 cycles
;--------------------------------------------------------
	in		r17,ACSR			; 1 cycle
	andi	r17,(1 << ACO)		; 1 cycle
	eor		r17,r16				; 1 cycle - exor check valid destroying r17
	breq	mdecode_errex		; 1 cycle - No toggle of bit is error (real error)
	rol		r19					; 1 cycle - now R19 = o7oooooX and C = o
	or		r19,r16				; 1 cycle - now R19 = o76ooooX and C = o
	nops4						; 4 cycles
;--------------------------------------------------------
; 3rd manchester is bit no 5
;--------------------------------------------------------
	in		r16,ACSR
	andi	r16,(1 << ACO)
	nops8
;--------------------------------------------------------
	in		r17,ACSR
	andi	r17,(1 << ACO)
	eor		r17,r16
	breq	mdecode_errex
	rol		r19					; 1 cycle - now R19 = 76ooooXo and C = o
	or		r19,r16				; 1 cycle - now R19 = 765oooXo and C = o
	nops4
;--------------------------------------------------------
; 4th manchester is bit no 4
;--------------------------------------------------------
	in		r16,ACSR
	andi	r16,(1 << ACO)
	nops8
;--------------------------------------------------------
	in		r17,ACSR
	andi	r17,(1 << ACO)
	eor		r17,r16
mdecode_errex:					; Extend error jump for 2nd manchester (Flag test will be same)
	breq	mdecode_error		; No toggle of bit is error
	rol		r19					; 1 cycle - now R19 = 65oooXoo and C = 7
	or		r19,r16				; 1 cycle - now R19 = 654ooXoo and C = 7
	nops4
;--------------------------------------------------------
; 5th manchester is bit no 3
;--------------------------------------------------------
	in		r16,ACSR
	andi	r16,(1 << ACO)
	nops8
;--------------------------------------------------------
	in		r17,ACSR
	andi	r17,(1 << ACO)
	eor		r17,r16
	breq	mdecode_error
	rol		r19					; 1 cycle - now R19 = 54ooXoo7 and C = 6
	bst		r16,ACO				; Store bit in temp, leave bit holder 0 in r19
	nops4						; Has to be done to recover bit 3 in the end T = 3
;--------------------------------------------------------
; 6th manchester is bit no 2
;--------------------------------------------------------
	in		r16,ACSR
	andi	r16,(1 << ACO)
	nops8
;--------------------------------------------------------
	in		r17,ACSR
	andi	r17,(1 << ACO)
	eor		r17,r16
	breq	mdecode_error
	rol		r19					; 1 cycle - now R19 = 4ooXoo76 and C = 5, T=3
	or		r19,r16				; 1 cycle - now R19 = 4o2Xoo76 and C = 5, T=3
	nops4
;--------------------------------------------------------
; 7th manchester is bit no 1
;--------------------------------------------------------
	in		r16,ACSR
	andi	r16,(1 << ACO)
	nops8
;--------------------------------------------------------
	in		r17,ACSR
	andi	r17,(1 << ACO)
	eor		r17,r16
	breq	mdecode_error
	rol		r19					; 1 cycle - now R19 = o2Xoo765 and C = 4, T=3
	or		r19,r16				; 1 cycle - now R19 = o21oo765 and C = 4, T=3
	nops4
;--------------------------------------------------------
; 8th manchester is bit no 0 - Lots to do as storing R19
;--------------------------------------------------------
	in		r16,ACSR
	andi	r16,(1 << ACO)
	nops7
	rol		r19					; 1 cycle - now R19 = 21oo7654 and C = o, T=3
;--------------------------------------------------------
	in		r17,ACSR			; 1 cycle
	andi	r17,(1 << ACO)		; 1 cycle
	eor		r17,r16				; 1 cycle
	breq	mdecode_error		; 1 cycle
	or		r19,r16				; 1 cycle - now R19 = 210o7654 and C = o, T=3
	bld		r19,4				; 1 cycle - Move temp to bit 4 - now R19 = 21037654 and C = o
	st		x+,r19				; 2 cycles
	rjmp	manchester_decode	; 2 cycles
;--------------------------------------------------------
; End of Manchester Decode Loop
;--------------------------------------------------------



;--------------------------------------------------------
; Error during Manchester Decode Loop
;--------------------------------------------------------
mdecode_error:
;	sbi	PORTD,5
;	cbi	PORTD,5
	ldi r16, 0b00011110				; PC1-4 is HexSwitch Pullup
	out PORTC, r16
	sbis PINC,1						; PINC1 is print Error
	rjmp	main_loop
;	sbi	PORTD,5
	ldi	r16,'!'
	rcall	COUT_0
	mov	r16,r25
	rcall	HEXOUT
	ldi	r16,';'
	rcall	COUT_0
	ldi	r16,10
	rcall	COUT_0
	ldi	r16,13
	rcall	COUT_0
;	cbi	PORTD,5
	rjmp	main_loop
;--------------------------------------------------------



;--------------------------------------------------------
; Finished Decoding Extended Squitter
;--------------------------------------------------------
manchester_done:
;	out PORTC,r24	; nop
;	sbi	PORTD,4						; LED on
	ldi	r16,'*'
	rcall	COUT_0
	ldi r27,$02					; ldi X,0h0200
	ldi r26,$00
	ldi r25,EXTENDED_BYTES
serial_loop:
	ld	r16,X+
	rcall	HEXOUT_Reshuffle
	dec	r25
	brne serial_loop

	ldi	r16,';'
	rcall	COUT_0
	ldi	r16,10
	rcall	COUT_0
	ldi	r16,13
	rcall	COUT_0
;	cbi	PORTD,4						; LED off
	rjmp main_loop
;--------------------------------------------------------



CheckForShort:
	cpi	r25,CHECK_SHORT
	brne mdecode_error

	ldi r16, 0b00001111				; PC0-3 is HexSwitch Pullup
	out PORTC, r16
	sbis PINC,0
	rjmp main_loop

	ldi	r16,'*'
	rcall	COUT_0
	ldi r27,$02					; ldi X,0h0200
	ldi r26,$00
	ldi r25,SHORT_BYTES
serial_loop2:
	ld	r16,X+
	rcall	HEXOUT_Reshuffle
	dec	r25
	brne serial_loop2

	ldi	r16,';'
	rcall	COUT_0
	ldi	r16,10
	rcall	COUT_0
	ldi	r16,13
	rcall	COUT_0
;	cbi	PORTD,4						; LED off

	rjmp main_loop



;--------------------------------------------------------
; Serial Character Stuff
;--------------------------------------------------------

HEXOUT_Reshuffle:
									; R16 = 21037654
	bst	r16,4						; store bit no4 in temp, T=3
	rol	r16							; R16 = 1037654C , C=2
	rol	r16							; R16 = 037654C2 , C=1
	rol	r16							; R16 = 37654C21 , C=0
	rol	r16							; R16 = 7654C210 , C=3
	bld	r16,3						; R16 = 76543210 , C=3

HEXOUT:

	push r16
	swap r16
	rcall HexNibble
	pop  r16

HexNibble:
	andi r16,$0F
	subi r16,-'0'
	cpi  r16,'9'+1
	brcs DisplHexDigit
	subi r16,-7
DisplHexDigit:
 
COUT_0:
   lds   r17,UCSR0A
   sbrs   r17,UDRE0      ;Check if data register empty
   rjmp   COUT_0         ;loop until UDRE1=1

	sts   UDR0,r16         ;send character     
	ret
