import os
import time
import subprocess
import sys
import getopt
from selenium import webdriver
from shutil import rmtree
from PIL import Image
from subprocess import Popen, PIPE

# **************************
# SETUP
# **************************

SCREENWIDTHS = [360, 1024, 1280]
SCREENHEIGHT = 768
SHOTSDIR = "shots"
RESIZEDIR = "resized"
BASEDIR = "baseline"
DIFFDIR = "diff"
PAGESLEEP = 2
PAGES = [["homepage", "https://github.com/"],
         ["signinpage", "https://github.com/login"]]


# *******************************
# FUNCTIONS
# *******************************

# Gets filename from page name and screensize
def getfilename(pagename, screensize):
    return pagename + "_" + str(screensize) + ".png"


# Gets the full path of a file in the 'shots' directory
def getshotspath(filename):
    return os.path.join(os.getcwd(), SHOTSDIR + "/" + filename)


# Gets the full path of a file in the 'resized' directory
def getresizedpath(filename):
    return os.path.join(os.getcwd(), RESIZEDIR + "/" + filename)


# Gets the full path of a file in the 'baseline' directory
def getbasepath(filename):
    return os.path.join(os.getcwd(), BASEDIR + "/" + filename)


# Gets the full path of a file in the 'diff' directory
def getdiffpath(filename):
    return os.path.join(os.getcwd(), DIFFDIR + "/" + filename)


# Get the width*height of an image
def getimagesize(filepath):
    im = Image.open(filepath)
    (width, height) = im.size
    return width * height


# Attempts to resize images for comparison
# If (actual < expected) we resize the actual
# If (actual > expected) we crop the actual
# else we do nothing
def resizeimages(basepath, shotspath, resizepath):
    base = Image.open(basepath)
    shot = Image.open(shotspath)
    (basewidth, baseheight) = base.size
    (actwidth, actheight) = shot.size
    if (actwidth < basewidth) or (actheight < baseheight):
        # resize actual
        resized = shot.resize((basewidth, baseheight), Image.BICUBIC)
        resized.save(resizepath)
    elif (actwidth > basewidth) or (actheight > baseheight):
        # crop actual
        resized = shot.crop((0, 0, basewidth, baseheight))
        resized.save(resizepath)
    else:
        shot.save(resizepath)


# Loops over images to compare and does the comparison
# Outputs a comparison report
def docomparison():
    # Setup directory
    if os.path.exists(DIFFDIR):
        rmtree(DIFFDIR)
    os.makedirs(DIFFDIR)
    if os.path.exists(RESIZEDIR):
        rmtree(RESIZEDIR)
    os.makedirs(RESIZEDIR)
    # Generate diffs
    print("Comparing screenshots and generating diffs")
    diffreport = []
    for page in PAGES:
        for size in SCREENWIDTHS:
            rtnmessage = compareimages(page[0], size)
            diffline = [page[0], str(size), rtnmessage]
            diffreport.append(diffline)
    # Write report
    print("-- Differences summary --")
    for item in diffreport:
        print("| " + item[0].ljust(40) + " | " + str(item[1]).ljust(40) + " | " + item[2])


# Compares two single images
# Attempts to resize and apply ImageMagik to generate a diff image and % difference
def compareimages(pagename, screensize):
    shotspath = getshotspath(getfilename(pagename, screensize))
    basepath = getbasepath(getfilename(pagename, screensize))
    diffpath = getdiffpath(getfilename(pagename, screensize))
    resizepath = getresizedpath(getfilename(pagename, screensize))
    similarity = "100%"
    pixel_diff = 0
    magikout = ""
    try:
        if (os.path.exists(shotspath)):
            if (os.path.exists(basepath)):
                resizeimages(basepath, shotspath, resizepath)
                try:
                    cmd = "compare -dissimilarity-threshold 1 -fuzz 20% -metric AE -highlight-color blue " + basepath + " " + resizepath + " " + diffpath
                    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
                    stdout, magikout = p.communicate()
                except subprocess.CalledProcessError, e:
                    magikout = e.output
                magikout = magikout.strip()
                if (magikout != ""):
                    pixel_diff = float(magikout)
                    similarity = str((pixel_diff / float(getimagesize(basepath))) * 100) + "%"
            else:
                return "Base file not found"
        else:
            return "Shot file not found"
        return similarity
    except Exception, e:
        return "Error " + str(e)


# Caputure screenshots of all pages and screensizes
def captureScreenshots(outputdir):
    # open browser
    print("Opening browser")
    driver = webdriver.Firefox()
    driver.implicitly_wait(5)
    driver.set_page_load_timeout(20)
    # loop taking actual screenshots
    try:
        print("Taking screenshots")
        for page in PAGES:
            name = page[0]
            url = page[1]
            print("Taking screenshots of page '" + name + "'")
            for size in SCREENWIDTHS:
                filename = name + "_" + str(size) + ".png"
                driver.set_window_size(size, SCREENHEIGHT)
                driver.get(url)
                time.sleep(PAGESLEEP)
                driver.get_screenshot_as_file(outputdir + "/" + filename)
    except:
        print("Error taking actual screenshots, closing browser")
        driver.quit()
        sys.exit(1)
    # close browser
    print("Closing browser")
    driver.quit()


# Gets new baseline images
def getbaselineimages():
    # Setup output directory
    if os.path.exists(BASEDIR):
        rmtree(BASEDIR)
    os.makedirs(BASEDIR)
    # Capture
    captureScreenshots(BASEDIR)


# Captures the actual images only
def getactualimages():
    # Setup output directory
    if os.path.exists(SHOTSDIR):
        rmtree(SHOTSDIR)
    os.makedirs(SHOTSDIR)
    # Capture
    captureScreenshots(SHOTSDIR)


# **************************
# SCRIPT
# **************************

# Get command line options
try:
    opts, args = getopt.getopt(sys.argv[1:], "eac", ["expected", "actual", "compare"])
except getopt.GetoptError:
    print("Usgae: --actual --expected --compare")
    sys.exit(2)
# Do as per cmd line args
for opt, arg in opts:
    if opt in ("-e", "--expected"):
        getbaselineimages()
    if opt in ("-a", "--actual"):
        getactualimages()
    if opt in ("-c", "--compare"):
        docomparison()
