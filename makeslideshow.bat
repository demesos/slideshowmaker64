@echo off
setlocal ENABLEDELAYEDEXPANSION

echo This script converts the images in the folder srcimages to the C64 palette
echo and generates a slideshow disk. The images are displayed as multicolor images
echo with a sprite overlay, converted by my own script.
echo Files are packed with exomizer and loaded with dreamload.

SET /P bordercolor="Enter code for border color (default=0):" || SET "bordercolor=0"
SET /P extradelayms="Enter extra delay between pics in ms (default=500):" || SET "extradelayms=500"
SET /P dither="Enter amount of dithering (default=10):" || SET "dither=10"

set c1541="exttools\c1541\c1541"
set exomizer="exttools\exomizer\exomizer"
set dload="..\exttools\dreamload\dload3000.prg"

echo Converting images...
del /Q convertedimages\*.*
cd imgconverter
for %%i in ("..\images\*") do (
  echo %%~ni
  IF [%1]==[-python] (
    python scol64.py --nograydither --dither %dither% -p pepto --format CTGnoviewer -o "../convertedimages/%%~ni.prg" -c simple "%%i"
  ) ELSE (
    scol64.exe --nograydither --dither %dither% -p pepto --format CTGnoviewer -o "../convertedimages/%%~ni.prg" -c simple "%%i"
  )
)
cd ..


echo Crunching files with exomizer... 
del /Q crunchedimages\*.*

SET /A IMGNUM=0
for %%i in (".\convertedimages\*.prg") do (
  echo %%i
  set "formattedNumber=00!IMGNUM!"
  %exomizer% level "%%i" -o "crunchedimages\!formattedNumber:~-2!.inc" -B
  type "code\9000.inc" "crunchedimages\!formattedNumber:~-2!.inc" > "crunchedimages\!formattedNumber:~-2!.exo"
  set /A IMGNUM=IMGNUM+1
)

echo .define numberofpics %IMGNUM% > code\presets.inc
echo .define extradelayms %extradelayms% >> code\presets.inc
echo .define bordercolor %bordercolor% >> code\presets.inc

echo Compiling code...
cd code
cl65 main.s exodecrunch.s ctgviewerVICbank4000.s ctgviewerVICbankC000.s -lib ../exttools/LAMAlib/LAMAlib.lib -t c64 -C c64-asm.cfg -u __EXEHDR__ -o main.prg 
exomizer sfx basic main.prg "../music/*" %dload% -o slideshow.prg  -B
cd ..

echo Creating disc...
del /Q "outfile\slideshow.d64"
%c1541% -format slideshow,id d64 "outfile\slideshow.d64"
%c1541% -attach "outfile\slideshow.d64" -write "code\slideshow.prg" "slideshow"
set /A IMGNUM=IMGNUM-1
FOR /L %%I IN (0,1,%IMGNUM%) DO (
  set "formattedNumber=00%%I"
  %c1541% -attach "outfile\slideshow.d64" -write "crunchedimages\!formattedNumber:~-2!.exo" "!formattedNumber:~-2!"
)
echo Done... please find your slideshow in folder outfile
pause