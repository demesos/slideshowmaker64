# slideshowmaker64
Slideshowmaker64
by Wil 
V1.1 2019-12-07

## About Slideshow Maker

Slideshow Maker is a tool that takes images, converts them into a format that can be displayed on a C64 and adds a slideshow player with music.

## Usage

To make a slideshow, put your pictures into folder "images" and start "makeslideshow.bat" (sorry for only haveing a windows batch file). Your pictures can be of different file formats and different size - the converter scales it to the target format. The filesize of converted images depends on the complexity of the images, but you can fit around 20-25 pics on one disk.

The imageconverter is rather slow. If you have Python 3 installed on your system, enter "makeslideshow.bat -python", this speeds the generation process a little bit up.

To change the music, put your SID file into folder "music". The filename does not matter, but there should be only one SID file in this directory. The SID must start at $1000 and be no longer than 8K in size. MUSIC_INIT must be at $1000 and MUSIC_PLAY at $1003.

The batch file asks for the border color, the extra delay between pics (there is a basic delay of around 10 seconds for loading and decrunching), and a dithering value (should be between 0 and 100).

The output is a d64 image named "slideshow.d64".

## Technical details

Slideshow Maker uses a multicolor image format with a resolution of 320x200 pixels. In front of the image is a sprite layer of 8 times 10 unexpanded sprites which increases the number of available colors in the central part of the image. 
The display routine is using 10 raster line interrupts per frame, but keeps the raster time to a minimum. This way the loader has sufficient CPU time to load the next image.

The image converter is a python program, which has a lot more options, feel free to experiment with them.

The used loader is dreamload (DLOAD) which provides decent performance, is easy to use and supports also SD2IEC drives. An assembled version of dload for the memory area $3000 is linked to the code.

Crunching is done with exomizer version 3.0.2. Exomizer's decrunching routine is linked to the code.

The code is written for the cc65 Assembler and uses some macros from my LAMAlib library.

For building the slide show disk, the tool c1541 from the VICE emulator suite is used.

Everything you need to run Slideshow Maker (on Windows) is included with this release.

## Acknowledgments

This project wouldn't have been possible without the existence of great tools like exomizer (credits to Zagon), Dreamland (The Dreams), VICE (VICE Team) and cc65 (von Bassewitz, Schmidt), thanks guys!
