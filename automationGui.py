import stitcher
import numpy as np
import os
import subprocess
from os.path import isfile, join
import tkinter
from tkinter import filedialog
from stitcher import Stitcher
import _thread
from subprocess import DEVNULL, STDOUT, check_call


class StitcherGUI:

	fileList = None;
	progress = 0;
	# maskImages = 0;

	def shorten_filename(self,filename):
		f = os.path.split(filename)[1]
		return "%s~%s" % (f[:3], f[-16:]) if len(f) > 19 else f

	def __init__(self, master):
		self.master = master
		master.title("Stitcher")
		self.outputFile = None
		self.browse_button = tkinter.Button(master, text="Select Folders", command=self.browseFiles)
		self.browse_button.grid(row=0)

		self.maskImages = tkinter.BooleanVar()
		self.maskImages.set(0);
		self.mask_button = tkinter.Checkbutton(master, text="Mask Images", onvalue=1, offvalue=0,variable=self.maskImages)
		self.mask_button.grid(row=5)

		self.stitch = tkinter.Button(master, text="Stack and Stitch", command=self.start)
		self.stitch.grid(row=3, column=1)

		self.progressText = tkinter.IntVar()
		self.progressText.set(self.progress)
		
		tkinter.Label(master, text="Progress :").grid(row=4,column=0)
		self.progress_label = tkinter.Label(master, textvariable=self.progressText)
		self.progress_label.grid(row=4, column=1)
		
	def browseFiles(self):
		# Tk().withdraw()
		dirs = []
		title = 'Choose Directory'
		while True:
			dir = filedialog.askdirectory(title=title)
			if not dir:
				break
			dirs.append(dir)
			title = 'got %s. Next dir' % dirs[-1]
		# parentName = os.path.split(os.path.dirname(files[0]))[1]
		# self.outputFile = os.path.join(os.path.dirname(files[0]),parentName + ".tiff")
		# self.file_label_text.set(parentName + ".tiff")
		self.fileList = root.tk.splitlist(dirs)

	def start(self):
		for folder in self.fileList:
			onlyFiles = [f for f in os.listdir(folder) if isfile(join(folder, f))]
			print(onlyFiles)
			print(folder)
			for files in onlyFiles:
				if(files.endswith(".xml")):
					# self.stack(folder + "/" + files)
					self.stitchFolder(folder)


		# stitcherHandler = Stitcher()
		# print(self.fileList)
		# print(self.outputFile);
		# if(self.outputFile is None):
		# 	exit()
		# _thread.start_new_thread(stitcherHandler.stitchFileList, (self.fileList, self.outputFile, self.progressCallback))

	def stack(self, xmlFile):
		commandLine = r'"C:/Program Files/ZereneStacker/jre/bin/java.exe" -Xmx8000m -DjavaBits=64bitJava -Dlaunchcmddir="C:/Documents and Settings/AISOS Lab PC/Application Data/ZereneStacker" -classpath "C:/Program Files/ZereneStacker/ZereneStacker.jar;C:/Program Files/ZereneStacker/JREextensions/*" com.zerenesystems.stacker.gui.MainFrame -noSplashScreen -exitOnBatchScriptCompletion -runMinimized  -batchScript "' + xmlFile + '"'
		subprocess.call( commandLine, stdout=DEVNULL, stderr=subprocess.STDOUT)

	def stitchFolder(self, targetFolder):
		stitcherHandler = Stitcher()
		filesToStitch = []
		onlyFiles = [f for f in os.listdir(targetFolder) if isfile(join(targetFolder, f))]
		for files in onlyFiles:
				if(files.endswith(".jpg")):
					filesToStitch.append(targetFolder + "/" + files)

		parentName = os.path.split(os.path.dirname(filesToStitch[0]))[1]
		outputFile = os.path.join(os.path.dirname(filesToStitch[0]),parentName + ".tiff")

		print(filesToStitch)
		print(outputFile);
		if(outputFile is None):
			exit()

		_thread.start_new_thread(stitcherHandler.stitchFileList, (filesToStitch, outputFile,"test.txt", self.progressCallback, self.maskImages.get(), None))


	def progressCallback(self, status, progress):
		self.progressText.set(progress);


root = tkinter.Tk()
root.geometry('{}x{}'.format(400, 200))
my_gui = StitcherGUI(root)
root.mainloop()