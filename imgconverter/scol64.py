## 
## scol64 Converting images to C64 format
## supports multicolor mode and color mixing
## 
## by Wilfried Elmenreich 2018-19
##

from __future__ import print_function
from PIL import Image, ImageFilter, ImageEnhance
import math
import operator
import colorsys
import time
import argparse
import sys
import os
import struct
from io import BytesIO
from array import array

gla=0

sys.setrecursionlimit(2000)

c64basecolorsVICE = (0x000000,0xF1F1F1,0x9A6049,0xA667BA,0xA667BA,0x84C16E,0x624BB7,0xDCE58C,
                 0xA48040,0x706700,0xCD9985,0x717171,0x9F9F9F,0xBDE9A8,0xA18DE4,0xC3C3C3)

c64basecolorsVICE2 = (0x000000,0xFFFFFF,0x9A6049,0xA667BA,0xA667BA,0x84C16E,0x624BB7,0xDCE58C,
                 0xA48040,0x706700,0xCD9985,0x4A4A4A,0x7B7B7B,0xBDE9A8,0xA18DE4,0xB2B2B2)


c64basecolorsWeb = (0x000000,0xFFFFFF,0x880000,0xAAFFEE,0xCC44CC,0x00CC55,0x0000AA,0xEEEE77,
                 0xDD8855,0x664400,0xFF7777,0x333333,0x777777,0xAAFF66,0x0088FF,0xBBBBBB)

c64basecolorsPepto = (0x000000,0xFFFFFF,0x813338,0x75CEC8,0x8E3C97,0x56AC4D,0x2E2C9B,0xEDF171,
                      0x8E5029,0x553800,0xC46C71,0x4A4A4A,0x7B7B7B,0xA9FF9F,0x706DEB,0xB2B2B2)

c64basecolors=c64basecolorsVICE

lowflickercombinations42c= ((1,13),(1,7),(10,12),(10,14),(12,14),(12,15),(12,15),(13,15),
                         (2,12),(2,4),(3,13),(3,15),(3,5),(3,7),(4,8),(5,10),(5,12),
                         (5,14),(5,15),(6,12),(6,9),(7,13),(7,15),(8,12),(2,8),(9,11))


lowflickercombinations= ((2,4),(2,11),(3,15),(4,8),(5,10),(5,12),
                         (5,15),(6,9),(6,11),(7,13),(7,15),(9,11),(10,12),(10,14),(12,14),
                         (13,15))

#flickering (3,7),(12,15)(8,12),(2,9),(5,14),(3,13),(3,5),(1,13)(1,7),(2,8),,
#bad combinations (2,12)(3,15)(5,10)(6,9)

dithering=False
CM=0

def makeExtColors():
    global c64extcolors
    global colorcode
    c64extcolors=c64basecolors
    colorcode=range(16)
    for co in lowflickercombinations:
        c64extcolors+=(combineHex(c64basecolors[co[0]],c64basecolors[co[1]]),)
        colorcode.append(co[0]*16+co[1])

def HextoRGB(RGBnumber):
    r=(RGBnumber & 0xFF0000) >> 16
    g=(RGBnumber & 0x00FF00) >> 8
    b=RGBnumber & 0x0000FF;
    return (r,g,b)

def RGBtoHex(c):
    return c[0]*0x10000+c[1]*0x100+c[2]

def combineHex(c1,c2):
    c=tuple(int(sum(x)/2) for x in zip(HextoRGB(c1), HextoRGB(c2)))
    return c[0]*0x10000+c[1]*0x100+c[2]

def isGray(c):
    if not math.isclose(c[0], c[1], rel_tol=0.03, abs_tol=1.0):
        return False
    if not math.isclose(c[1], c[2], rel_tol=0.03, abs_tol=1.0):
        return False
    return True

def diffRGB(c1,c2):
    if args.nograydither:
        if isGray(c1) and isGray(c2):
            return (0,0,0)
    return (c1[0]-c2[0],c1[1]-c2[1],c1[2]-c2[2])

def addRGB(c1,c2):
    return (c1[0]+c2[0],c1[1]+c2[1],c1[2]+c2[2])

def scaleRGB(c,factor):
    return (c[0]*factor,c[1]*factor,c[2]*factor)

def combineRGB(c1,c2):
    c=tuple(int(sum(x)/2) for x in zip(c1, c2))
    return c

def intRGB(c):
    return (int(c[0]+0.5),int(c[1]+0.5),int(c[2]+0.5))

def reduceColors(pixelMap,width,height,colors,blobSizeMap):
    reducedImg=Image.new( 'RGB', (width,height), "black")
    reducedMap=reducedImg.load()
    RGBcolors=[HextoRGB(c) for c in colors]
    if dithering:
        errorMap=[[(0,0,0)]*height for i in range(width)]
        
        for y in range(height):
            for x in range(0,width):
                if blobSizeMap[x][y]==-1:
                    colors=RGBcolors[:16]
                else:
                    colors=RGBcolors
                cr=nearestColor(addRGB(pixelMap[x,y],errorMap[x][y]),colors)[0]
                reducedMap[x,y]=cr
                distributeError(diffRGB(cr,pixelMap[x,y]),errorMap,x,y,width,height)
    else:
        for y in range(height):
            for x in range(0,width):
                if blobSizeMap[x][y]==-1:
                    colors=RGBcolors[:16]
                else:
                    colors=RGBcolors                
                cr=nearestColor(pixelMap[x,y],RGBcolors)[0]
                reducedMap[x,y]=cr
    return reducedImg

def getHistogramBaseColors(imgMap,width,height,colors):
    hist={}
    RGBcolors=[HextoRGB(c) for c in colors]
    for y in range(height):
        for x in range(width):
            c1=imgMap[x,y]
            cCodes=colorcode[RGBcolors.index(c1)]
            if cCodes<16:
                colcodes=[cCodes]
            else:
                colcodes=[cCodes & 0x0F, cCodes >> 4]
            for c in colcodes:
                if c in hist:
                    hist[c]=hist[c]+1
                else:
                    hist[c]=1
    return sorted(hist.items(), key=operator.itemgetter(1), reverse=True)

def imageColorScore(imgMap,width,height,colors):
    hist=getHistogramBaseColors(imgMap,width,height,colors)
    logsum=0
    for x in hist:
        logsum+=math.log(x[1])
    vprintln(logsum,hist)
    return logsum

def getHistogram(imgMap,x1,x2,y1,y2):
    hist={}
    for y in range(y1,y2):
        for x in range(x1,x2):
            c=imgMap[x,y]
            if c in hist:
                hist[c]=hist[c]+1
            else:
                hist[c]=1
            #give pixels at borders more weight to avoid discontinuitues across 8x8 blocks
            if y==y1 or y==y2-1:
                hist[c]=hist[c]+1
            if x==x1 or x==x2-1:
                hist[c]=hist[c]+1               
    return sorted(hist.items(), key=operator.itemgetter(1), reverse=True)

def getmostneededcolor(blockhistos,commoncolors,columns):
    bestc=-1
    bestcnt=0
    hist={}
    for blines in blockhistos:
        for xb in range(len(blines)):
            if not xb in columns:
                continue #skip columns to ignore
            colorsusedinblock=[x[0] for x in blines[xb]]
            bhist=blines[xb].copy()
            # remove known colors from histogram
            for colors in colorsusedinblock:
                if colors in commoncolors:
                    colorsusedinblock.remove(colors)      
            # skip block if there are less than 4 colors to display
            if len(colorsusedinblock)<=3:
                continue
            for c in colorsusedinblock:
                if c in hist:
                    hist[c]=hist[c]+1
                else:
                    hist[c]=1
    #now lets look for the most need color
    if len(hist)>0:
        return max(hist, key=hist.get)
    return

def getblockcolset(blockhist,commoncolors):
    hist={}
    for c in blockhist:
        if not c[0] in commoncolors:
            hist[c[0]]=c[1]
    blockcolors=[]
    while len(blockcolors)<3:
        if len(hist)==0:
            blockcolors.append(commoncolors[0])
        else:
            blockcolors.append(max(hist, key=hist.get))
            del hist[max(hist, key=hist.get)]
    return commoncolors[:1]+blockcolors+commoncolors[1:]

def getSprAddr(x,y):
    # find the address in the spritemap
    # sprites are placed 8 in a row starting from bitmap xpos 64
    # sprites repeat every 21 lines, in total 80 sprites
    # second 40 sprites start one line earlier
    # and have their last line stored first
    sprite=int((x-64)/24)+8*int((y+(y>=13*8))/21)
    offs= int((x-64)/8) % 3 + (y % 21) * 3
    return sprite*64 + offs

def quantifyCTG(reducedMap,width,height,colors):
    global gla
    blockhistos=[[0]*40 for i in range(25)]
    commoncolors=[] #this will contain bg color, spr common col 1 and 2
    sprcolors=[] #colors for sprites 1..8
    #let's make a histogram for each block first
    for yb in range(25):
        for xb in range(40):
            blockhistos[yb][xb]=getHistogram(reducedMap,xb*4,xb*4+4,yb*8,yb*8+8)
    #find the common background color from columns 0..7 and 32..39
    #because the other columns have a sprite covering it so they are less in
    #need of color
    bestc=getmostneededcolor(blockhistos,commoncolors,list(range(8))+list(range(32,40)))
    if not bestc is None:
        commoncolors.append(bestc)
    for sprcommoncolor in range(2):
        bestc=getmostneededcolor(blockhistos,commoncolors,range(8,32))
        if not bestc is None:
            commoncolors.append(bestc)
    #just in case the outer parts didn't choose a background color, we will choose it now
    if len(commoncolors)<3:
        bestc=getmostneededcolor(blockhistos,commoncolors,range(8,32))
        if not bestc is None:
            commoncolors.append(bestc)
    #just in case we still have less than 3 colors in our list
    while len(commoncolors)<3:
        commoncolors.append((0, 0, 0))           
    #now find the best color for each sprite
    for sprite in range(8):
        bestc=getmostneededcolor(blockhistos,commoncolors,range(8+sprite*3,11+sprite*3))
        if not bestc is None:
            sprcolors.append(bestc)
        else:
            sprcolors.append((0, 0, 0))
    #now generate the bitmaps
    bitmap=[]
    colram=[]
    scr1=[]
    spritemap=[0]*8*10*64
    #debug
    gla+=1 # gla is debug
    if gla % 100 == 0:
        print(gla,"hello")
        print("commoncolors (bg,sprmuco1,sprmuco2):",commoncolors) # contains [((195, 195, 195), 5), ((195, 195, 195), 5), ((195, 195, 195), 5)]
    c0i=colorcode[c64extcolors.index(RGBtoHex(commoncolors[0]))]
    sprmuc1=colorcode[c64extcolors.index(RGBtoHex(commoncolors[1]))]
    sprmuc2=colorcode[c64extcolors.index(RGBtoHex(commoncolors[2]))]
    for yb in range(25):
        for xb in range(40):
            if xb<8 or xb>=32:
                blockcommoncolors=commoncolors[:1]
            else:
                sprite=int((xb-8)/3)
                blockcommoncolors=commoncolors+sprcolors[sprite:1]
            blockcolors=getblockcolset(blockhistos[yb][xb],blockcommoncolors)
            c1i=colorcode[c64extcolors.index(RGBtoHex(blockcolors[1]))]
            c2i=colorcode[c64extcolors.index(RGBtoHex(blockcolors[2]))]
            c3i=colorcode[c64extcolors.index(RGBtoHex(blockcolors[3]))]
            colram.append(c3i)
            scr1.append(16*c1i + c2i)
            for y in range(yb*8,yb*8+8):
                b=0
                for x in range(xb*4,xb*4+4):
                    c=reducedMap[x,y]
                    cused=nearestColor(c,blockcolors)[0]
                    ind=blockcolors.index(cused)
                    b=b*4
                    if ind<4:
                        b+=ind
                    else:
                        #we need to write to a sprite                   
                        if ind==4:
                           pattern=0b01 #muco1
                        elif ind==5:
                           pattern=0b11 #muco2
                        else:
                           pattern=0b10 #sprcolor
                        addr=getSprAddr(x*2,y)
                        spritemap[addr]+=pattern * 4**(3-(x-xb*4))
                        #debug
                        if spritemap[addr]>255:
                            print(">255")
                            print("x:",x,"y:",y,"addr:",addr)
                            print("pattern=",pattern,"factor=",4**(x-xb*4))
                bitmap.append(b)
    colorcodes=[c64extcolors.index(RGBtoHex(c)) for c in commoncolors+sprcolors]
    #insert three zeros into list
    colorcodes[1:1]=[0,0,0]
    padding=[0]*10                
    return [colram,scr1,colorcodes,padding,spritemap,bitmap]                   
            
def quantify8x8(reducedMap,width,height,colors):
    totalhist=getHistogram(reducedMap,0,width,0,height)
    besterr=1e9
    blockhistos=[[0]*40 for i in range(25)]
    currentcolset=[[0]*40 for i in range(25)]
    for yb in range(25):
        for xb in range(40):
            blockhistos[yb][xb]=getHistogram(reducedMap,xb*4,xb*4+4,yb*8,yb*8+8)
    for c0 in [x[0] for x in totalhist[:4]]:
        err=0
        for yb in range(25):
            for xb in range(40):
                if err>besterr: continue
                besterrb=1e12
                blockhist=blockhistos[yb][xb]
                blockcols=[x[0] for x in blockhist]
                if c0 in blockcols:
                    blockcols.remove(c0)
                if len(blockcols)<3:
                    currentcolset[yb][xb]=([c0]+blockcols+[(0,0,0)]*3)[:4]
                    continue #block can be shown without error
                for i1 in range(len(blockcols)-1):
                    c1=blockcols[i1]
                    for i2 in range(i1+1,len(blockcols)):
                        c2=blockcols[i1]
                        for c3 in c64basecolors:
                            c3=HextoRGB(c3)
                            if c3 in [c0,c1,c2]:
                                continue                            
                            errb=evaluate(blockhist,c0,c1,c2,c3,besterrb)
                            if errb<besterrb:
                                besterrb=errb
                                currentcolset[yb][xb]=[c0,c1,c2,c3]
                err+=besterrb
        if err<besterr:
            bestc0=c0
            besterr=err
            bestcolset = [row[:] for row in currentcolset]
    #now generate the bitmap
    c0=bestc0
    bitmap=[]
    colram=[]
    scr1=[]
    scr2=[]
    c0i=colorcode[c64extcolors.index(RGBtoHex(c0))]
    for yb in range(25):
        for xb in range(40):
            blockcolors=bestcolset[yb][xb]
            c1i=colorcode[c64extcolors.index(RGBtoHex(blockcolors[1]))]
            c2i=colorcode[c64extcolors.index(RGBtoHex(blockcolors[2]))]
            c3i=colorcode[c64extcolors.index(RGBtoHex(blockcolors[3]))]
            colram.append(c3i)
            scr1.append(16*(c1i & 15) + (c2i & 15))
            if c1i>15:
                c1i=c1i/16
            if c2i>15:
                c2i=c2i/16
            scr2.append(16*(c1i & 15) + (c2i & 15))  
            for y in range(yb*8,yb*8+8):
                b=0
                for x in range(xb*4,xb*4+4):
                    c=reducedMap[x,y]
                    cused=nearestColor(c,blockcolors)[0]
                    ind=blockcolors.index(cused)
                    b=b*4+ind
                bitmap.append(b)
    return [bitmap,scr1,scr2,colram,[c0i]]

def floodFill(x,y,color,imageMap,blobSizeMap):
    width=len(blobSizeMap)
    height=len(blobSizeMap[0])
    points=[]
    stack=[[x,y]]
    while len(stack)>0:
        x1,y1=stack[-1]
        del stack[-1]
        if blobSizeMap[x1][y1]!=0 or imageMap[x1,y1]!=color:
            continue
        #find left boundary
        while x1>0 and (imageMap[x1-1,y1]==color and blobSizeMap[x1-1][y1]==0):
            x1-=1
        #scan to right
        up,down=True,True
        while x1<width and (imageMap[x1,y1]==color and blobSizeMap[x1][y1]==0):
            blobSizeMap[x1][y1]=-1
            points.append([x1,y1])
            #detect color change above
            if y1+1 < height:
                up_=imageMap[x1,y1+1]==color and blobSizeMap[x1][y1+1]==0
                if up and up_:
                    stack.append([x1,y1+1])
                up = not up_
            #detect color change below
            if y1 > 0:
                down_=imageMap[x1,y1-1]==color and blobSizeMap[x1][y1-1]==0
                if down and down_:
                    stack.append([x1,y1-1])
                down=not down_
            x1+=1
    return points
            
def determineBlobSizes(imageMap,width,height):
    blobSizeMap=[[0]*height for i in range(width)]
    for x in range(width):
        for y in range(height):
            if blobSizeMap[x][y]!=0:
                continue
            points=floodFill(x,y,imageMap[x,y],imageMap,blobSizeMap)
            blobSize=len(points)          
            for p in points:
                blobSizeMap[p[0]][p[1]]=blobSize
    return blobSizeMap

def evaluate(blockhist,c0,c1,c2,c3,besterrb):
    errsum=0
    for x in blockhist:
        colerr=nearestColor(x[0],[c0,c1,c2,c3])[1]
        if colerr>0:
            colerr+=20
        errsum+=x[1]*colerr
        if errsum>=besterrb:
            break
    return errsum
                

#implementation of Floyd-Steinberg Dithering algorithm
#weights are adapted to wide pixels and have an intensity scaler
def distributeError(err,errorMap,x,y,width,height):
    if x<width-1:
        errorMap[x+1][y]=addRGB(errorMap[x+1][y],scaleRGB(err,FSweights[0]))
    if y<height-1:
        errorMap[x][y+1]=addRGB(errorMap[x][y+1],scaleRGB(err,FSweights[1]))
        if x>0:
            errorMap[x-1][y+1]=addRGB(errorMap[x-1][y+1],scaleRGB(err,FSweights[2]))        
        if x<width-1:
            errorMap[x+1][y+1]=addRGB(errorMap[x+1][y+1],scaleRGB(err,FSweights[3]))

#this function is not used but is here in case someone wants to see the results
#when original Floyd-Steinberg Dithering algorithm is used on wide pixels
def OrigFSdistributeError(err,errorMap,x,y,width,height):
    if x<width-1:
        errorMap[x+1][y]=addRGB(errorMap[x+1][y],scaleRGB(err,-7.0/16))
    if y<height-1:
        errorMap[x][y+1]=addRGB(errorMap[x][y+1],scaleRGB(err,-5.0/16))
        if x>0:
            errorMap[x-1][y+1]=addRGB(errorMap[x-1][y+1],scaleRGB(err,-3.0/16))        
        if x<width-1:
            errorMap[x+1][y+1]=addRGB(errorMap[x+1][y+1],scaleRGB(err,-1.0/16))

def nearestColor(rgb,RGBcolors):
    besterr=1e9
    for i in range(len(RGBcolors)):
        e=ColorDiff(rgb,RGBcolors[i])
        if i>15:
            e=e*1.2
        if e<besterr:
            bestmatch=i
            besterr=e
    return RGBcolors[bestmatch],besterr

# Convert from RGB to Lab Color Space
def Lab(rgb):
    def PPn(P,Pn):
        r=P/Pn
        if r<216.0/24389:
            return 1.0/116*(24389.0/27*P/Pn+16)
        else:
            return (P/Pn)**0.33
    R=rgb[0]/255.0
    G=rgb[1]/255.0
    B=rgb[2]/255.0
    X=0.4124564*R+0.3575761*G+0.1804375*B
    Y=0.2126729*R+0.7151522*G+0.0721750*B
    Z=0.0193339*R+0.1191920*G+0.9503041*B
    Xn=94.811 # 10° entspricht dem CIE-Normalbeobachter von 1976
    Yn=100.0  # Normlichtart D65 = 6500K (bedeckter Himmel bei Abmusterung am Nordfenster)
    Zn=107.304
    y3=PPn(Y,Yn)
    L=116*y3-16
    a=500*(PPn(X,Xn)-y3)
    b=200*(y3-PPn(Z,Zn))
    return (L,a,b)

def deltaE(lab1,lab2):
    return math.sqrt((lab1[0]-lab2[0])**2+(lab1[1]-lab2[1])**2+(lab1[2]-lab2[2])**2)

# Speed of ColorDiff is central for overall performance

def ColorDiff(rgb1,rgb2):  
    #simple model
    if CM==0:
        b=(rgb1[0]+rgb2[0]+rgb1[1]+rgb2[1]+rgb1[2]+rgb2[2])/6.0+1
        r=(rgb1[0]+rgb2[0])/(2.0*255.0)
        br=r*((rgb1[0]-rgb2[0])**2-(rgb1[2]-rgb2[2])**2)
        cD=2*(rgb1[0]-rgb2[0])**2 + 4*(rgb1[1]-rgb2[1])**2 + 3*(rgb1[2]-rgb2[2])**2 + br
    else:
        #convert colors to Lab space
        lab1 = Lab(rgb1)
        lab2 = Lab(rgb2)
        cD=deltaE(lab1,lab2)
    return cD

def save64(img42,filename,startaddress):
    #print(filename)
    #print(img42)
    outfile = open(filename,"wb")
    #write startaddress
    outfile.write(struct.pack("<H", startaddress))
    for x in img42:
        for b in x:
            outfile.write(struct.pack("B", b))

## Main function
###faked command-line-args
##sys.argv = ['scol64.py','--optimize','-v','--koala','forum4mlp-26.scol','-c','MLP','--dither','20','-d','testimages/forumromanum4.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','hausmlpC-26.scol','-c','MLP','--dither','20','-d','testimages/haus317.png']
##sys.argv = ['scol64.py','-v','--koala','hausmlp-26.scol','-c','MLP','--dither','20','-d','testimages/haus317.png']
##sys.argv = ['scol64.py','-v','--koala','forum4mlp-26.scol','-c','MLP','--dither','20','-d','testimages/forumromanum4.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','wilciec-26b.scol','-c','CIE','--dither','20','-d','testimages/wil.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','forumciec-26b.scol','-c','CIE','--dither','20','-d','testimages/forumromanum4.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','easter-cie2.scol','-c','CIE','--dither','20','-d','testimages/halfeaster2.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','uhrturm.kla','-c','MLP','--dither','20','-d','testimages/uhrturm2-320.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','wilportraits.kla','-c','MLP','--dither','20','-d','testimages/wil-portraits.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','blackhole.kla','-c','MLP','--dither','30','-d','testimages/blackhole.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','katiec.kla','-c','CIE','--dither','30','-d','testimages/katiebouman.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','bastibumsti.kla','-c','CIE','--dither','30','-d','testimages/bastibumsti.jpg']
##sys.argv = ['scol64.py','--optimize','-v','--koala','testimages/ctgbook/martinland.kla','-c','CIE','-d','testimages/ctgbook/martinland.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','testimages/ctgbook/flexman.kla','-c','CIE','-d','testimages/ctgbook/flexman.png']
##sys.argv = ['scol64.py','--optimize','-v','--koala','testimages/ctgbook/andreas.kla','-c','CIE','-d','testimages/ctgbook/andreas.png']
#sys.argv = ['scol64.py','-v','--koala','testimages/ctgbook/KLAs/'+str(nam)+'.kla','-c','CIE','-d','testimages/ctgbook/'+str(nam)+'.png']
#sys.argv = ['scol64.py','--optimize','-v','--koala','testimages/ctgbook/KLAs optimized/'+str(nam)+'.kla','-c','CIE','-d','testimages/ctgbook/'+str(nam)+'.png']

#nam="wil4"
#sys.argv = ['scol64.py','--dither','50','-p','vice','-v','--format','Koala','-o','testimages/ctgbook/KLAs optimized/'+str(nam)+'.kla','-c','fast','-d','testimages/ctgbook/'+str(nam)+'.png']

#sys.argv = ['scol64.py','--dither','50','-p','vice','-v','--format','CTG','-o',str(nam)+'-ctg.prg','-c','fast','-d','testimages/ctgbook/'+str(nam)+'.png']
#sys.argv = ['scol64.py','--dither','50','-p','vice','-v','--format','Koala','-o',str(nam)+'-kla.prg','-c','fast','-d','testimages/ctgbook/'+str(nam)+'.png']
#sys.argv = ['scol64.py','--dither','50','-p','vice','-c','CIE','-v','--format','CTG','-o',str(nam)+'CIE-ctg.prg','-d','testimages/ctgbook/'+str(nam)+'.png']
#sys.argv = ['scol64.py','--nograydither','--dither','50','-p','vice','-c','fast','-v','--format','CTG','-o',str(nam)+'fast-nctg.prg','-d','testimages/ctgbook/'+str(nam)+'.png']
#sys.argv = ['scol64.py','--nograydither','--dither','50','-p','vicedark','-c','fast','-v','--format','CTG','-o',str(nam)+'fast-vd-ctg.prg','-d','testimages/ctgbook/'+str(nam)+'.png']

#sys.argv = ['scol64.py','--dither','50','-p','vice','-v','--format','CTGnoviewer','-o',str(nam)+'nov-ctg.prg','-c','fast','-d','testimages/ctgbook/'+str(nam)+'.png']


tstart=time.time()
# Parse command-line arguments
parser = argparse.ArgumentParser(description='Convert an image to a switched multicolor image on the C64.')
parser.add_argument("filename", help="File to be converted.")
parser.add_argument("-d", "--display", help="display image after conversion",
                    action="store_true", default=False)
parser.add_argument("-m", "--mixedcolors", help="use mixed colors",
                    action="store_true", default=False)

parser.add_argument("-c","--colorcomparison", help="Select model for color comparison: simple, CIE1976 (more accurate)")
parser.add_argument("--dither", nargs="?", type=int, const=20,
                    help="Enable dithering")
parser.add_argument("--nograydither", help="Don't differ gray pixels.",
                    action="store_true", default=False)
parser.add_argument("-b","--maxFlickerBlobSize", nargs="?", type=int, const=0,
                    help="Define largest allowed blob of switched color")
parser.add_argument("--reportExecutionTime", help="Report execution time",
                    action="store_true", default=False)
parser.add_argument("--optimize", help="Optimze image for best color range",
                    action="store_true", default=False)
parser.add_argument("-v","--verbose", help="Report status information via console",
                    action="store_true", default=False)
parser.add_argument("--format", help="select output format: Koala, CTG, CTGhimem, CTGnoviewer, SCOL")
parser.add_argument("-p","--palette", help="Palette to use: web, vice, vicedark, pepto")
parser.add_argument("-o", "--outfile", help="save converted image")
parser.add_argument("--png", help="save converted image as png")


args = parser.parse_args()
if args.verbose:
    def vprint(*args):
        # Print each argument separately so caller doesn't need to
        # stuff everything to be printed into a single string
        spc=''
        for arg in args:
           print(spc,end="") 
           print(arg,end="")
           spc=' ' 
    def vprintln(*args):
        # Print each argument separately so caller doesn't need to
        # stuff everything to be printed into a single string
        spc=''
        for arg in args:
           print(spc,end="") 
           print(arg,end="")
           spc=' '
        print()
else:   
    vprint = lambda *a: None      # do-nothing function
    vprintln = vprint
if args.dither:
    FSweights=[-7.0/32,-14.0/32,-3.0/32,-1.0/32]
    FSweights=[x*args.dither/100.0 for x in FSweights]
    dithering=True
targetformat='Koala'    
if args.format:
    if args.format.lower() == 'koala':
        targetformat='Koala'
    elif args.format.lower() == 'ctg':
        targetformat='CTG'
    elif args.format.lower() == 'ctghimem':
        targetformat='CTGhimem'
    elif args.format.lower() == 'ctgnoviewer':
        targetformat='CTGnoviewer'         
    elif args.format.lower() == 'scol':
        targetformat='SCOL'             
    else:
        sys.stderr.write('Unknown or unsupported format, please specify Koala, SCOL or CTG.')
        sys.exit(1)    
if args.mixedcolors:
    if targetformat!='SCOL':
        sys.stderr.write('Option --mixedcolors only works with SCOL format.')
        sys.exit(1)
    
if args.colorcomparison:
    if args.colorcomparison=='CIE2000' or args.colorcomparison=='CIE':
        CM=1
    elif args.colorcomparison=='simple':
        CM=0
    else:
        sys.stderr.write('Unknown color model, please specify simple or CIE2000.')
        sys.exit(1)
        
if args.palette:
    if args.palette=='web':
        c64basecolors=c64basecolorsWeb
    elif args.palette=='pepto':
        c64basecolors=c64basecolorsPepto
    elif args.palette=='vice':
        c64basecolors=c64basecolorsVICE
    elif args.palette=='vicedark':
        c64basecolors=c64basecolorsVICE2    
    else:
        sys.stderr.write('Unknown palette, please specify web, vice, or pepto.')
        sys.exit(1)

if args.nograydither:
    #overwrite gray values
    col_lst = list(c64basecolors)
    col_lst[11] = 0x606060 # dark gray
    col_lst[12] = 0x909090 #0x8A8A8A # mid gray
    col_lst[15] = 0xB3B3B3 # light gray    
    c64basecolors = tuple(col_lst)
##

t0=time.time()
if args.mixedcolors:
    vprint("Mixing paint...")
    makeExtColors()
    vprintln("using",len(c64extcolors),"colors.")
else:
    c64extcolors=c64basecolors
    colorcode=range(len(c64basecolors))
    vprintln("Using",len(c64extcolors),"colors.")
#Read image
loadedim = Image.open( args.filename ) #forumromanum4 terminator320
#Applying a filter to the image
img0 = loadedim.filter( ImageFilter.UnsharpMask(radius=2, percent=50, threshold=3))

if targetformat in ['Koala','SCOL','CTG','CTGhimem','CTGnoviewer']:
    #size to 160x200 (fat pixel)
    img0=img0.resize((160, 200))

#if args.nufli:
#    #size to 320x200
#    img0=img0.resize((320, 200))


bestimg=img0
#generate multiple image candidates with different brightness, contrast and color saturation
#this option requires a lot of computation time
if args.optimize:
    imgcandidates=[]
    variants=[]
    for brightness in [0.8,1.0,1.2]:
        img2=ImageEnhance.Brightness(img0).enhance(brightness)
        for contrast in [1.0,1.5]:
            img3=ImageEnhance.Contrast(img2).enhance(contrast)
            for saturation in [1.0,1.5]:
                img4 = ImageEnhance.Color(img3).enhance(saturation)
                s="brightness="+str(brightness)+",contrast="+str(contrast)+",saturation="+str(saturation)
                imgcandidates.append(img4)
                variants.append(s)
    bestscore=0
    for i in range(len(imgcandidates)):
        im=imgcandidates[i]
        if len(imgcandidates)>1:
            vprintln("Testing variant",variants[i])
        pixelMap = im.load() #create the pixel map
        dummyBlobs=[[0]*im.height for i in range(im.width)]
        reducedImg=reduceColors(pixelMap,im.width,im.height,c64extcolors,dummyBlobs)
        reducedMap=reducedImg.load()
        jpg_file = BytesIO()
        reducedImg.save(jpg_file, 'jpeg')
        filesize_jpeg = jpg_file.tell()
        vprintln("size=", filesize_jpeg)
        score=imageColorScore(reducedMap,im.width,im.height,c64extcolors)
        #score=filesize_jpeg
        if score>bestscore:
            bestscore=score
            bestimg=im
            bestreducedmap=reducedMap
else:
    pixelMap = img0.load() #create the pixel map
    dummyBlobs=[[0]*img0.height for i in range(img0.width)]
    reducedImg=reduceColors(pixelMap,img0.width,img0.height,c64extcolors,dummyBlobs)
    bestreducedmap=reducedImg.load()

im=bestimg
pixelMap = im.load()
reducedMap=bestreducedmap
vprintln("Image colors reduced to",len(c64extcolors),"in","%.1f" % (time.time()-t0),"seconds.")
if args.mixedcolors and args.maxFlickerBlobSize>0:
    t0=time.time()
    vprint("Checking for large color blobs...")
    blobSizeMap=determineBlobSizes(reducedMap,im.width,im.height)
    #mark all larger blobs as forbidden
    forbiddenBlobs=False
    for i in range(len(blobSizeMap)):
        for j in range(len(blobSizeMap[0])):
            if blobSizeMap[i][j]>=args.maxFlickerBlobSize:
                blobSizeMap[i][j]=-1
                forbiddenBlobs=True
    #redo
    if forbiddenBlobs:
        reducedImg=reduceColors(pixelMap,im.width,im.height,c64extcolors,blobSizeMap)
        reducedMap=reducedImg.load()
    vprintln( "done in","%.1f" % (time.time()-t0),"seconds.")
t0=time.time()        
if targetformat=='Koala' or targetformat=='SCOL':
    vprint("Quantifying, this may take a while...")
    img42=quantify8x8(reducedMap,im.width,im.height,c64extcolors)
    vprintln("image fitted to 8x8 restrictions in","%.1f" % (time.time()-t0),"seconds.")
    if args.mixedcolors:
        save64(img42,args.outfile,0x6000)
    else:
        save64(img42[0:2]+img42[3:],args.outfile,0x6000)
    vprintln("Saved "+args.outfile)
    caculationtime=(time.time()-t0)
    vprintln("Overall conversion time","%.1f" % (time.time()-tstart),"seconds.")
elif targetformat=='CTG' or targetformat=='CTGhimem' or targetformat=='CTGnoviewer':
    if targetformat=='CTGhimem':
        endaddr=0xFF40
        viewer='CTGviewerC28A.bin'
    else:
        endaddr=0x7F40
        viewer='CTGviewer428A.bin'    
    #now make a CTG
    vprint("Quantifying colors for CTG image, this may take a while...")
    imgCTG=quantifyCTG(reducedMap,im.width,im.height,c64extcolors)
    if targetformat!='CTGnoviewer':
        with open(viewer, 'rb') as f:
           displayctgbin = f.read()
        displayctg = [int(b) for b in displayctgbin[2:]]
        imgplusviewer=[displayctg]+imgCTG
    else:
        imgplusviewer=imgCTG
    length=sum([len(i) for i in imgplusviewer])
    startaddr=endaddr - length   
    save64(imgplusviewer,args.outfile,startaddr)
    vprintln("Saved "+args.outfile)
    if targetformat!='CTGnoviewer':
        vprintln("Use SYS "+str(startaddr)+" to view image after loading.")        
    caculationtime=(time.time()-t0)
    vprintln("Overall conversion time","%.1f" % (time.time()-tstart),"seconds.")    
if args.reportExecutionTime:
    print("%.3f" % (time.time()-tstart))

if args.png:
    viewImg.save(args.png)

if args.display:
    #prepare image to be displayed
    viewImg=Image.new( 'RGB', (320,200), "black")
    viewMap=viewImg.load()
    for y in range(200):
        for x in range(320):
            viewMap[x,y]=reducedMap[x/2,y]    
    viewImg.show()


