#!/bin/bash

# image converter needs colormath library for Python:
# sudo pip3 install colormath

# this script needs these packages:
# vice (for c1541 tool)
# cc65 (for compiling, version 2.18 or later)

echo
echo This script converts the images in the folder srcimages to the C64 palette
echo and generates a slideshow disk. The images are displayed as multicolor images
echo with a sprite overlay, converted by my own script.
echo Files are packed with exomizer and loaded with dreamload.
echo

read -ep "Enter code for border color: " -i "0" bordercolor
read -ep "Enter extra delay between pics in ms: " -i "500" extradelayms
read -ep "Enter amount of dithering: " -i "10" dither

c1541="c1541"
exomizer="./exttools/exomizer-linux/exomizer"
dload="./exttools/dreamload/dload3000.prg"

if [ ! -f "$exomizer" ]; then
    pushd . 1>/dev/null
    echo -e "\nCompiling exomizer..."
    cd "./exttools/exomizer-linux/"
    make
    popd 1>/dev/null
fi

echo -e "\nConverting images..."
rm -f ./convertedimages/*.*
for img in ./images/*; do
    i=$(basename "$img")
    echo "    $i"
    python3 ./imgconverter/scol64.py --nograydither --dither $dither -p pepto --format CTGnoviewer -o "./convertedimages/${i%.*}.prg" -c simple "$img"
done

echo -e "\nCrunching files with exomizer..."
rm -f ./crunchedimages/*.*
IMGNUM=0
for img in ./convertedimages/*.prg; do
    formattedNumber=$(printf "%02d" $IMGNUM)
    $exomizer level "$img" -o "./crunchedimages/$formattedNumber.inc" -B
    cat "./code/9000.inc" "./crunchedimages/$formattedNumber.inc" > "./crunchedimages/$formattedNumber.exo"
    IMGNUM=$((IMGNUM+1))
done

echo Compiling code...
echo ".define numberofpics $IMGNUM" > ./code/presets.inc
echo ".define extradelayms $extradelayms" >> ./code/presets.inc
echo ".define bordercolor $bordercolor" >> ./code/presets.inc
cd code
cl65 main.s exodecrunch.s ctgviewerVICbank4000.s ctgviewerVICbankC000.s -lib ../exttools/LAMAlib/LAMAlib.lib -t c64 -C c64-asm.cfg -u __EXEHDR__ -o main.prg
../$exomizer sfx basic main.prg "../music/"*.prg ../$dload -o slideshow.prg  -B
cd ..

echo -e "\nCreating disc..."
rm -f ./outfile/slideshow.d64
$c1541 -format slideshow,id d64 "./outfile/slideshow.d64"
$c1541 -attach "./outfile/slideshow.d64" -write "./code/slideshow.prg" "slideshow"
for img in ./crunchedimages/*.exo; do
    i=$(basename "$img")
    $c1541 -attach "./outfile/slideshow.d64" -write "$img" "${i%.*}"
done

echo -e "\nDone... please find your slideshow in folder outfile"

read -ep "Test the slideshow y/n: " -i "y" testsl
if [ "$testsl" == "y" ]; then
    x64 ./outfile/slideshow.d64 1>/dev/null
fi

