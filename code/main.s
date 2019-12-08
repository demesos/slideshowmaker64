;==========================================================
;
; A slideshow viewer for the CTG format
; Version 1.0 by Wil
;
; to be assembled with ca65 from the cc65 suite
; build with amakefile.bat
;
;==========================================================

.include "../exttools/LAMAlib/LAMAlib.inc"
.include "presets.inc"
.FEATURE STRING_ESCAPES

;----------------------------------------------------------
; Constants
;----------------------------------------------------------

;SID Music player
music_init = $1000
music_play = music_init+3

;Dreamload
dload_install   = $3000
ldloc           = $3d00
ldlae		= $ae

;Exomizer decrunch (we have adjusted this in the included cruncher)
firstZP = $F8
lastZP = $FF
load_address = $9000	;this hardcoded in the crunched files

;----------------------------------------------------------
; Init
;----------------------------------------------------------
	lda #bordercolor
	sta $d020
	sta $d021

;----------------------------------------------------------
; Install dreamload
;----------------------------------------------------------

        jsr dload_install ;install fastloader
        bcc fastloadinstallok ;success?
        primm "error installing dreamload fastloader!"
        rts
fastloadinstallok:

;----------------------------------------------------------
; Install SID player
;----------------------------------------------------------
	jsr music_init

	sei 

	lda #<irq0
	sta $FFFE
	lda #>irq0
	sta $FFFF

	lda #<irq1
	sta $314
	lda #>irq1
	sta $315

	lda #$7f
	sta $dc0d	; disable timer interrupts
	sta $dd0d
	lda $dc0d	; acknowledge CIA interrupts

	lda #01
	sta $D01A 	; set raster interrupt

	cli
;----------------------------------------------------------
; slideshow
;----------------------------------------------------------
slideshowinit:

	lda #00
	sta picturenumber
;----------------------------------------------------------
; viewer addresses
;----------------------------------------------------------
.import ctgview4000 
.import stopctgview4000
.import ctgviewC000 
.import stopctgviewC000

slideshowloop:

;----------------------------------------------------------
; check for space key pressed
;----------------------------------------------------------
	jsr checkexit

;----------------------------------------------------------
; picture to be displayed in VIC bank $4000
;----------------------------------------------------------
	jsr load_pic
	jsr decrunchloadedfile
	jsr ctgview4000
	wait  extradelayms ;wait that many ms
	jsr next_pic_number

;----------------------------------------------------------
; check for space key pressed
;----------------------------------------------------------
	jsr checkexit

;----------------------------------------------------------
; picture to be displayed in VIC bank $C000
;----------------------------------------------------------
	jsr load_pic
	lda load_address 
	ora #$c0 ;change address from 4xxx to Cxxx
	sta load_address 
	jsr decrunchloadedfile
	jsr ctgviewC000
	wait extradelayms ;wait that many ms
	jsr next_pic_number
	jmp slideshowloop

;----------------------------------------------------------
; next picture number
;----------------------------------------------------------
next_pic_number:
	lda picturenumber
	clc
	adc #01	;carry is already cleared if number below numberofpics
	cmp #numberofpics
	bne nothelast
	lda #00
nothelast:
	sta picturenumber
	rts
;----------------------------------------------------------
; load picture subroutine
; picture number in register Y
; list of filenames are in a predefined list
;----------------------------------------------------------
load_pic:
	ldy picturenumber

    	lda picfilename_low,Y
	tax
    	lda picfilename_high,Y
	tay
	lda #filename00_len
	jmp ldloc ;load the file

;----------------------------------------------------------
; Decrunching routine
;----------------------------------------------------------
.import decrunch
.export get_crunched_byte

LDLAE=$ae
_byte_lo = lbl1 + 1
_byte_hi = lbl1 + 2

decrunchloadedfile:
	lda #$34
	sta $01		;make RAM visible		

	lda #<load_address
	sta _byte_lo
	lda #>load_address
	sta _byte_hi	

	jsr decrunch	;exomizer decrunch and return
	lda #$35 
	sta $01 
	rts
;----------------------------------------------------------
get_crunched_byte:
lbl1:	lda $ffff		; needs to be set correctly before
				; decrunch_file is called.
	inc16 lbl1+1
	rts

;----------------------------------------------------------
; IRQ wrapper for the SID player
;----------------------------------------------------------
.export musicirq:=irq1

irq0:	pha
	txa
	pha
	tya
	pha

irq1:
	lda $01
	pha
	lda #$35 
	sta $01 
	asl $d019	;recognize VIC IRQ
	;save ZP addresses used by exodecrunch since
	;the SID player might use them
	ldx #(lastZP-firstZP)
@loop1:
	lda firstZP,x
	pha
	dex
	bpl @loop1
	
	jsr music_play

	ldx #00
@loop2:
	pla
	sta firstZP,x
	inx
	cpx #(lastZP-firstZP+1)
	bne @loop2

	pla
	sta $01
	
	pla	;exit irq
	tay	;this is the same code as at $EA81
	pla	;but since the ROM might be turned off
	tax	;we better copy this here	
	pla
	rti	

picturenumber: .byte 0

.include "filenames.inc"

checkexit:	
	lda #%01111111
	sta $DC00
	lda $DC01
	cmp #%11101111 
	beq exit

	rts
exit:	
	;space was pressed, exit program
	sei
	lda #11
	sta 53280
	lda #12
	sta 53281
	lda #6
	sta 646
	jsr music_init
	cli
	jsr stopctgview4000
	jmp $FD15       ; set I/O vectors ($0314..$0333) to kernal defaults
