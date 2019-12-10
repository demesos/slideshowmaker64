; A viewer for the CTG format
;
; assemble via:
; cl65 ctgviewer.s -lib ../LAMAlib/LAMAlib.lib -t c64 -C c64-asm.cfg -u __EXEHDR__ -o ctgviewer.prg
; or
; cl65 ctgviewer.s -lib ../LAMAlib/LAMAlib.lib -t c64 -C c64-asm.cfg --start-addr 0x42b0 -o ctgviewer.bin
;

.export ctgviewC000 := install
;.export stopctgviewC000 := deinstall

;the two isr routines are exported for debugging reasons
;isr1 and isr 2 must be on the same page
.export ctgviewC000ISR1 := isr1, ctgviewC000ISR2 := isr2  

.include "../exttools/LAMAlib/LAMAlib.inc"
;.FEATURE STRING_ESCAPES

vicbase=$C000
screen=vicbase + $0800
colramdata=screen-1000
spriteaddr=screen+$0400 ;space for 80 sprites, usually $4C00-$5FFE
spriteptrs=(spriteaddr-vicbase)/64

imgcolors=screen+1000 ;bgcolor, 0,0, sprmuco1, sprmuco2, colors for sprite 0-7

.import musicirq

install: 
	;wait for a rasterline >255 to start to avoid flickering
waitHiRaster:
	lda $D011
	bpl waitHiRaster
	lda #80
waitHiRaster2:
	cmp $D012	;wait for rasterline > 80
	bcs waitHiRaster2

	lda $01
	pha
	lda #$35 
	sta $01 
;----------------------------------------------------------
;copy values to $D800 (color ram)
;this takes around 185 rastercycles time
;----------------------------------------------------------
	ldx #00
copycolram:
copy1:
	lda colramdata,x
	sta $d800,x
	inx
	bne copy1
copy2:
	lda colramdata+$100,x
	sta $d800+$100,x
	inx
	bne copy2
	
copy3:
	lda colramdata+$200,x
	sta $d800+$200,x
	inx
	bne copy3

	ldx #$18
copy4:
	lda colramdata+$2E8,x
	sta $d800+$2E8,x
	inx
	bne copy4

	sei

	lda #<isr0
	sta $fffe
	lda #>isr0
	sta $ffff

	lda #<isr1
	sta $314
	lda #>isr1
	sta $315

	; -----------------------------
	; Set VIC bank, screen, etc
	; -----------------------------	
	
	;setVICbank
	lda #199-vicbase/$4000
	sta $DD00

	;set VIC screen to vicbase + $0800: %0001....
	;set bitmap to vicbase + $2000: %....1000
	lda #%00101000
	sta $D018

	;Enable Multicolor mode
	lda #216
	sta $D016

	lda #%00111011
	sta $D011	;enable bitmap mode, set rasterline interrupt high bit to 0
	lda #48
	sta $D012	;set rasterline interrupt lower bits to 0
	lda #00
	sta $D01D 	;no x-expand
	sta $D017 	;no y-expand
	sta $D01B 	;sprites in foreground
	sta nextraster+1 ;index for interrupt raster lines

	ldx #$f8
	stx sm1+1	;prepare following loop
	
	;lda #24+8*8+7*24	;lo byte of x-position of last sprite is 0
	ldy #spriteptrs
	ldx #$0e
	
	;set sprite X-positions and initial pointers
loop1:	sta $d000,X	;set x position
	sec
	sbc #24		
sm1:	sty screen+$3f8
	inc sm1+1
	iny
	dex
	dex
	bpl loop1

	lda #$80
	sta $D010	; sprites X 9th bit
	lda #$FF
	sta $D015	; sprites on
	sta $D01C 	; all sprites multicolor

	;set color values of background and sprites
	ldx #14	;need to copy 14 color values
copycol:
	lda imgcolors,x
	sta $d021,x
	dex
	bpl copycol

	lda #$7f
	sta $dc0d	; disable timer interrupts
	sta $dd0d
	lda $dc0d	; acknowledge CIA interrupts

	lda #01
	sta $D01A 	; set raster interrupt

	lda #00		; prepare self-mod values
	sta nextraster+1
	lda #spriteptrs+1
	sta sprptr1+1
	lda #50
	sta spry+1

	pla
	sta $1

	cli
	rts

deinstall:
	sei           ; disable interrupts
	lda #$1b
	sta $d011     ; restore text screen mode
	lda #$81
	sta $dc0d     ; enable Timer A interrupts on CIA 1
	lda #0
	sta $d01a     ; disable video interrupts
	lda #$31
	sta $314      ; restore old IRQ vector
	lda #$ea
	sta $315
	bit $dd0d     ; re-enable NMI interrupts
	lda #00
	sta $d015     ; sprites off

	;setVICbank
	lda #199
	sta $DD00

	;set VIC screen to default
	lda #21
	sta $D018

	;disable Multicolor mode
	lda #200
	sta $D016

	;disable bitmap mode
	lda #27
	sta $D011

	;default memory configuration
	lda #$37
	sta 1

	cli
	rts

isr0:	pha
	txa
	pha
	;tya
	;pha	;we save y later

isr1:	ldx $1
	lda #$35	;reset memory configuration
	sta $1
	asl $d019	;acknowledge raster interrupt
	inc $D012	;set raster interrupt for next line
	lda #<isr2
	sta $fffe
	;lda #>isr2	;isr1 and isr2 need to be aligned to same page to work
	;sta $ffff
	cli
waitloop:
	.REPEAT 9
	nop
	.ENDREP
	bne waitloop    ;this line is usually never reached
isr2:
	stx recover1+1	;remember previous memory configuration
		
	pla	;remove status and PC from stack that was pushed by second interrupt
	pla
	pla
	tya	;save y now
	pha

	.REPEAT 4
	nop
	.ENDREP

	clc
sprptr1: lda #spriteptrs+1
	ldx #$FE

	.macro sax arg
	.byte $8F,<(arg),>(arg)
	.endmacro
	
	sax screen+$3f8
	sta screen+$3f9
	adc #$02
	sax screen+$3fa
	sta screen+$3fb
	adc #$02
	sax screen+$3fc
	sta screen+$3fd
	adc #$02
	sax screen+$3fe
	sta screen+$3ff
	adc #$02

	sta sprptr1+1

	;pla		;remove status and PC from stack that was pushed by second interrupt
	;pla
	;pla

	asl $d019	;acknowledge raster interrupt

	clc
spry:	lda #50
	adc #21
	bcc skip
	lda #spriteptrs+1
	sta sprptr1+1
	lda #50
skip:
	sta spry+1	

	.REPEAT 16
	nop
	.ENDREP

	sta $D001
	sta $D003
	sta $D005
	sta $D007
	sta $D009
	sta $D00b
	sta $D00d
	sta $D00f
 
	bcs endofscreen

nextraster: ldx #00	
	lda rasterlines,x
	sta $D012	;next raster irq
	inc nextraster+1

	lda #<isr0
	sta $fffe
	lda #>isr0
	sta $ffff

recover1:	lda #$35	;will be overwritten
	sta 1

	pla	;exit irq
	tay	;this is the same code as at $EA81
	pla	;but since the ROM might be turned off
	tax	;we better copy this here	
	pla
	rti

endofscreen:
	lda #<isr0
	sta $fffe
	lda #>isr0
	sta $ffff

	lda #48
	sta $D012	;next raster irq
	lda #00
	sta nextraster+1
	
	lda recover1+1
	sta 1

	jmp musicirq	

rasterlines: .byte 69,89,111,132,152,173,193,215,236


