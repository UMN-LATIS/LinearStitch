import sys
import os
from os.path import isfile, isdir, join
from os.path import expanduser
import shutil

import click

@click.command()
@click.option('--sourcefolder', prompt='Base folder containing all your stacks')
@click.option('--badstack', prompt='The name of the bad stack')
@click.option('--num', prompt='Number of bad images in bad stack', type=int)

def fixfolder(sourcefolder, badstack, num):
    """Program to fix missing photos in gigamacro stacks."""
    childrenStacks = [f for f in os.listdir(sourcefolder) if isdir(join(sourcefolder, f))]
    childrenStacks.sort()
    fileCountList = []
    foundBadStack = False
    pathToBadStack = None
    badFiles = []
    negativeNum = -1 * num

    for stack in childrenStacks:
        pathToStack = sourcefolder + "/" + stack
        if(stack == badstack):
            foundBadStack = True
            pathToBadStack = pathToStack
        
        if(foundBadStack):
            if(len(badFiles) > 0):       
                for badFile in badFiles:
                    print("moving: " + badFile)
                    shutil.move(badFile, pathToStack)
            
            files = [os.path.join(pathToStack, f) for f in os.listdir(
                pathToStack) if isfile(join(pathToStack, f))]
            files.sort()
            badFiles = files[negativeNum:]

    if(len(badFiles) > 0):
        for badFile in badFiles:
            print("removing: " + badFile)
            os.remove(badFile)
    badFiles = []

if __name__ == '__main__':
    fixfolder()
