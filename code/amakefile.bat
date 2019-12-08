setlocal ENABLEDELAYEDEXPANSION
set c1541="C:\Users\Wilfried\Documents\software\c64\WinVICE-3.1-x64\c1541"

cl65 main.s exodecrunch.s ctgviewerVICbank4000.s ctgviewerVICbankC000.s -lib ../../LAMAlib/LAMAlib.lib -t c64 -C c64-asm.cfg -u __EXEHDR__ -o main.prg -Ln labels.txt
grep -v ".__" labels.txt
exomizer sfx basic main.prg "../music/*" dload3000.prg -o slideshow.prg  -B

pause

del "slideshow.d64"
%c1541% -format slideshow,id d64 "slideshow.d64"
%c1541% -attach "slideshow.d64" -write "slideshow.prg" "slideshow"
FOR /r %%i IN ("..\crunchedimages\*.prg") DO (
  echo %%~ni
  %c1541% -attach "slideshow.d64" -write "%%i" "%%~ni"
)
pause
slideshow.d64