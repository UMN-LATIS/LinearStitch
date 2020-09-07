### installation instruction for wxPython-Phoenix  : https://wiki.wxpython.org/How%20to%20install%20wxPython#Installing_wxPython-Phoenix_using_pip
### modified from : https://stackoverflow.com/questions/28417602/ask-multiple-directories-dialog-in-tkinter
###					https://wxpython.org/pages/overview/#hello-world
"""
To run app, navigate to directory using the that contains LS_GUI.py using terminal. Then type:
	$ pythonw LS_GUI.py
"""

import os
import wx
import wx.lib.agw.multidirdialog as MDD
import cv2
import numpy
import multiprocessing
import shutil

# required by pyinstaller
import pkg_resources.py2_warn

if __name__ == "__main__":
	multiprocessing.freeze_support()

from PyQt5.QtWidgets import (QFileDialog, QAbstractItemView, QListView,
							 QTreeView, QApplication, QDialog)

import _thread
from os.path import isfile, isdir, join
from os.path import expanduser

import stitcher
from stitcher import Stitcher
import subprocess
from subprocess import DEVNULL, STDOUT, check_call

import statistics

import configparser

from string import Template

import threading
from queue import Queue

import time

from zipfile import ZipFile

class LinearStitch(wx.Frame):

	# Our normal wxApp-derived class, as usual
	app = wx.App(0)
	config = None

	#setup listbox list as global var
	init_list = []
	cont = None
	scalePath = ""

	scaleControl = None

	progressGauge = None

	ScanQueue = Queue()
	StitchQueue = Queue()
	StackQueue = Queue()
	ArchiveQueue = Queue()

	def __init__(self, parent, title):
		if not os.path.exists('./config.ini') and os.path.exists('./config.sample.ini'):
			shutil.copy('./config.sample.ini', './config.ini')

		self.config = configparser.ConfigParser()
		self.config.read('config.ini')

		for w in range(int(self.config['Processing']['CoreCount'])):
			t = threading.Thread(target=self.scanWorker, name='worker-%s' % w)
			t.daemon = True
			t.start()

		t = threading.Thread(target=self.stitchWorker, name='worker-%s' % w)
		t.daemon = True
		t.start()

		t = threading.Thread(target=self.stackWorker, name='worker-%s' % w)
		t.daemon = True
		t.start()

		t = threading.Thread(target=self.archiveWorker, name='worker-%s' % w)
		t.daemon = True
		t.start()


		wx.Frame.__init__(self, parent, -1, title,
						  pos=(150, 150), size=(600, 600))


		#panel setup for button and listbox use
		panel = wx.Panel(self)
		self.myPanel = panel

		# Create the menubar
		menuBar = wx.MenuBar()

		# and a menu
		menu = wx.Menu()

		# add an item to the menu, using \tKeyName automatically
		# creates an accelerator, the third param is some help text
		# that will show up in the statusbar
		menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Exit this simple sample")

		# bind the menu event to an event handler
		self.Bind(wx.EVT_MENU, self.OnTimeToClose, id=wx.ID_EXIT)

		# and put the menu on the menubar
		menuBar.Append(menu, "&File")
		self.SetMenuBar(menuBar)

		self.CreateStatusBar()

		#app contains 4 buttons for interactive use
		# exitbutton = wx.Button(panel, label="Exit")
		clearbutton = wx.Button(panel, label="Clear All")
		addbutton = wx.Button(panel, label = "+")
		delbutton = wx.Button(panel, label = "-")



		self.cont = wx.ListBox(panel, -1, (0,0), (200, 200), self.init_list, wx.LB_EXTENDED)


		scale_horzSizer = wx.BoxSizer( wx.HORIZONTAL )
		selectScale = wx.Button(panel, label = "Select Scale")
		self.scaleControl = wx.TextCtrl(panel, size=(400, -1), style=wx.TE_READONLY)
		scale_horzSizer.Add(selectScale, 0, wx.ALL, 10);
		scale_horzSizer.Add(self.scaleControl, 0, wx.ALL, 10);


		sizer = wx.BoxSizer(wx.VERTICAL)


		panelCtrls_horzSizer = wx.BoxSizer( wx.HORIZONTAL )
		buttonSizer = wx.BoxSizer(wx.VERTICAL)

		buttonSizer.Add(addbutton, 0, wx.ALL, 10)
		buttonSizer.Add(delbutton, 0, wx.ALL, 10)
		buttonSizer.Add(clearbutton, 0, wx.ALL, 10)

		panelCtrls_horzSizer.Add(buttonSizer)
		panelCtrls_horzSizer.Add(self.cont)

		self.AddLinearSpacer( sizer,10 )


		button_horzSizer = wx.BoxSizer( wx.HORIZONTAL )
		scanForProblems = wx.Button(panel, label = "Scan for Problems")
		startProcessing = wx.Button(panel, label = "Start Processing")
		self.progressGauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL, size = (100, -1));

		button_horzSizer.Add(scanForProblems, 0, wx.ALL, 10);
		button_horzSizer.Add(startProcessing, 0, wx.ALL, 10);
		button_horzSizer.Add(self.progressGauge, 0, wx.ALL, 10)
		self.progressGauge.Hide();

		self.maskBox = wx.CheckBox(panel, label="Mask Images")
		self.verticalCore = wx.CheckBox(panel, label="Vertical Core")
		self.stackImages = wx.CheckBox(panel, label="Stack Images")
		self.stackImages.SetValue(True)

		self.archiveImages = wx.CheckBox(panel, label="Achive Images")
		self.archiveImages.SetValue(True)

		sizer.Add(panelCtrls_horzSizer)
		sizer.Add(scale_horzSizer, 0, wx.ALL, 10)
		sizer.Add(self.maskBox, 0, wx.ALL, 10)
		sizer.Add(self.verticalCore, 0, wx.ALL, 10)
		sizer.Add(self.stackImages, 0, wx.ALL, 10)
		sizer.Add(self.archiveImages, 0, wx.ALL, 10)
		sizer.Add(button_horzSizer, 0, wx.ALL, 10)
		panel.SetSizerAndFit(sizer)
		panel.Layout()

		self.SetSizerAndFit(sizer)

		#event handling - button binded with functions
		# self.Bind(wx.EVT_BUTTON, self.on_exit_button, exitbutton)
		self.Bind(wx.EVT_BUTTON, self.on_clear_button, clearbutton)
		self.Bind(wx.EVT_BUTTON, self.on_add_button, addbutton)
		self.Bind(wx.EVT_BUTTON, self.on_del_button, delbutton)
		self.Bind(wx.EVT_BUTTON, self.on_scale_button, selectScale)
		self.Bind(wx.EVT_BUTTON, self.scanForProblems, scanForProblems)
		self.Bind(wx.EVT_BUTTON, self.startProcessing, startProcessing)

		#event handling - close app with "x" button located in corner
		self.Bind(wx.EVT_CLOSE, self.on_exit_button)

		self.pool=multiprocessing.Pool()

	def AddLinearSpacer( self, boxsizer, pixelSpacing ) :
		""" A one-dimensional spacer along only the major axis for any BoxSizer """

		orientation = boxsizer.GetOrientation()
		if   (orientation == wx.HORIZONTAL) :
			boxsizer.Add( (pixelSpacing, 0) )
		elif (orientation == wx.VERTICAL) :
			boxsizer.Add( (0, pixelSpacing) )



	def OnTimeToClose(self, evt):
		"""Event handler for the button click."""
		print("Exiting.")
		self.Close()

	#opens a new menu and closes when selection(s) is made
	#adds currently selected directory/directories to listbox
	def on_add_button(self, event):
		self.selectFolders()

	def on_scale_button(self, event):
		dlg = getExistingFiles()
		dlg.setDirectory(self.config['General']['BrowsePath'])
		if dlg.exec_() == QDialog.Accepted:
			selectedFiles = dlg.selectedFiles()
			self.scalePath = selectedFiles[0]
			self.scaleControl.SetValue(self.scalePath)



	#deletes currently selected directory/directories from listbox
	def on_del_button(self,event):
		deleted_items = self.cont.GetSelections()
		deleted_items.reverse()
		for file in deleted_items:
			self.cont.Delete(file)

	#terminates app
	def on_exit_button(self, event):
		self.Destroy()

	#deletes all current directories in listbox
	def on_clear_button(self, event):
		while (self.cont.GetCount() != 0):
			self.cont.Delete(0)

	#closes window, does NOT terminate app
	def closewindow(self, event):
		self.Destroy()

	#obtains path for selected directory to be added to the listbox
	def selectFolders(self):
		dlg = getExistingDirectories()
		dlg.setDirectory(self.config['General']['BrowsePath'])
		if dlg.exec_() == QDialog.Accepted:
			self.cont.InsertItems(dlg.selectedFiles(), 0)

	def scanForProblems(self, event):
		print("Starting Scan")
		for folder in self.cont.GetStrings():
			# self.scanCore(folder)
			self.ScanQueue.put(folder)

	def scanCore(self, folder):
		childrenCores = [f for f in os.listdir(folder) if isdir(join(folder, f))]
		childrenCores.sort()
		fileCountList = [];
		outputText = ""
		outputText += "Scanning for problems in: " + folder + "\n"
		outputText += "------------------------------------" + "\n"
		for core in childrenCores:
			fileCount = 0
			(problemList, fileCount) = self.scanFolder(folder + "/" + core)
			fileCountList.append(fileCount)
			if(len(problemList) > 0):
				for problemFile in problemList:
					outputText += "Problem detected in: " + folder + "/" + core + "/" + problemFile + "\n"
		if(len(fileCountList) < 2):
			outputText += "Empty Folder: " + folder + "/" + "\n"
		else:
			coreMode = max(set(fileCountList), key=fileCountList.count)
			for index, core in enumerate(fileCountList):
				if(core != coreMode):
					outputText += "File count mismatch in: " + folder + "/" + childrenCores[index] + "\n"
		outputText += "------------------------------------" + "\n" + "\n"
		self.echo(outputText)

	def echo(self, text):
		print(text)


	def scanFolder(self, path):
		files = [f for f in os.listdir(path) if isfile(join(path, f))]
		colorAverage = []
		fileCount = 0

		files.sort()
		onlyJpegs = [jpg for jpg in files if jpg.lower().endswith(".jpg")]
		if(len(onlyJpegs) < 1):
			return [], 0
		proc = Processor(path)
		# for file in onlyJpegs:
		# 	fileCount += 1
		# 	# myimg = cv2.imread(path + "/" + file)
		# 	# avg_color_per_row = numpy.average(myimg, axis=0)
		# 	# avg_color = numpy.average(avg_color_per_row, axis=0)
		# 	colorAverage.append(avg_color)

		
		colorAverage=self.pool.map(proc,onlyJpegs)
		hasProblem = False
		meanValues = numpy.array(colorAverage).mean(axis=0)

		problemIndex = []

		for index, item in enumerate(colorAverage):
			distance = numpy.array(item) - meanValues
			if(not all(abs(i) <= 20 for i in distance)):
				hasProblem = True
				problemIndex.append(index)

		problemFiles = []
		for problemItem in problemIndex:
			problemFiles.append(onlyJpegs[problemItem])

		return problemFiles, fileCount

	def scanWorker(self):
		while True:
			if not self.ScanQueue.empty():
				folder = self.ScanQueue.get()
				self.scanCore(folder)
				self.ScanQueue.task_done()
			time.sleep(1)

	def stitchWorker(self):
		while True:
			if not self.StitchQueue.empty():
				folder = self.StitchQueue.get()
				self.stitchFolder(folder)
				self.StitchQueue.task_done()
			time.sleep(1)

	def stackWorker(self):
		while True:
			if not self.StackQueue.empty():
				folder = self.StackQueue.get()
				self.stack(folder)
				self.StackQueue.task_done()
			time.sleep(1)

	def get_all_file_paths(self, directory):

	    # initializing empty file paths list
	    file_paths = []

	    # crawling through directory and subdirectories
	    for root, directories, files in os.walk(directory):
	    	for filename in files:
	            # join the two strings in order to form the full filepath.
	            filepath = os.path.join(root, filename)
	            file_paths.append(filepath)

	    # returning all file paths
	    return file_paths  

	def archiveWorker(self):
		while True:
			if not self.ArchiveQueue.empty():
				folder = self.ArchiveQueue.get()
				self.archive(folder)
				self.ArchiveQueue.task_done()
			time.sleep(1)

	def archive(self, folder):

		ArchivePath = self.config['General']['ArchivePath']
		if ArchivePath == 'NULL':
			print('WARNING: Folder not archived. See Archive option in config.ini file.')
		else:
			outputFile = os.path.basename(folder) + ".zip"
			outputFilePath = os.path.join(self.config['General']['ArchivePath'], outputFile)
			file_paths = self.get_all_file_paths(folder)
			print("Zipping to: " + outputFilePath)
			with ZipFile(outputFilePath,'w') as zip:
			# writing each file one by one
				for file in file_paths:
					zip.write(file, os.path.relpath(file, os.path.join(folder, '..')))

	def startProcessing(self, event):

		self.progressGauge.Show()
		self.myPanel.Layout();
		for folder in self.cont.GetStrings():
			onlyFiles = [f for f in os.listdir(folder) if isfile(join(folder, f))]
			print(onlyFiles)
			print(folder)
			if(self.stackImages.IsChecked()):
				self.StackQueue.put(folder)
			else:
				self.StitchQueue.put(folder)

	def stack(self, folder):

		onlyFolders = [f for f in os.listdir(folder) if isdir(join(folder, f))]
		onlyFolders.sort()
		sourceString = "";
		for stackFolder in onlyFolders:
			sourceString += '<Source value="' + folder + "/" + stackFolder + '"/>\n'

		substitutionDict = { 'batchLength': len(onlyFolders), 'sourceFiles': sourceString, 'outputPath': folder +"/" }
		template = open( self.config['Zerene']['TemplateFile'] )
		src = Template( template.read() )
		populatedTemplate = src.substitute(substitutionDict)

		xmlFile = folder + "/stack.xml"
		output = open(xmlFile, "w")
		output.write(populatedTemplate)
		output.close();

		ZereneInstall = self.config['Zerene'].get('Install', '')
		ZereneLicense = self.config['Zerene'].get('License', '')

		ZereneLicense = ZereneLicense.replace('{{APPDATA}}', os.getenv('APPDATA'))

		if not ZereneInstall.endswith('/'):
			ZereneInstall += '/'
		if not ZereneLicense.endswith('/'):
			ZereneLicense += '/'

		commandLine = self.config['Zerene']['LaunchPath'] \
			.replace('{{Install}}', ZereneInstall) \
			.replace('{{License}}', ZereneLicense) \
			.replace('{{script}}', xmlFile);

		subprocess.call( commandLine, stdout=DEVNULL, stderr=subprocess.STDOUT)
		self.StitchQueue.put(folder)

	def stitchFolder(self, targetFolder):
		stitcherHandler = Stitcher()
		filesToStitch = []
		onlyFiles = [f for f in os.listdir(targetFolder) if isfile(join(targetFolder, f))]
		for files in onlyFiles:
			if(files.endswith(".jpg")):
				filesToStitch.append(targetFolder + "/" + files)

		if(len(filesToStitch) < 2):
			return
		parentName = os.path.split(os.path.dirname(filesToStitch[0]))[1]
		outputFile = os.path.join(os.path.dirname(filesToStitch[0]),parentName + ".tiff")
		logFile = os.path.join(os.path.dirname(filesToStitch[0]),parentName + "_log.txt")
		filesToStitch.sort()
		print(filesToStitch)
		print(outputFile);
		print("Logging to: " + logFile);
		if(outputFile is None):
			exit()

		stitcherHandler.stitchFileList(filesToStitch, outputFile, logFile, self.progressCallback,
		                               self.maskBox.IsChecked(), self.scalePath, self.verticalCore.IsChecked())
		
		if(self.archiveImages.IsChecked()):
			self.ArchiveQueue.put(targetFolder)

		# _thread.start_new_thread(stitcherHandler.stitchFileList, (filesToStitch, outputFile,logFile, self.progressCallback, self.maskBox.IsChecked(), self.scalePath))


	def progressCallback(self, status, progress):
		self.progressGauge.SetValue(progress);




class getExistingDirectories(QFileDialog):
	def __init__(self, *args):
		super(getExistingDirectories, self).__init__(*args)
		self.setOption(self.DontUseNativeDialog, True)
		self.setFileMode(self.Directory)
		self.setOption(self.ShowDirsOnly, True)
		# self.setDirectory(args[0])
		self.findChildren(QListView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.findChildren(QTreeView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)

class getExistingFiles(QFileDialog):
	def __init__(self, *args):
		super(getExistingFiles, self).__init__(*args)
		self.setOption(self.DontUseNativeDialog, True)
		self.setFileMode(self.ExistingFile)
		self.setOption(self.ShowDirsOnly, False)

class Processor:
	def __init__(self,path):
		self._path=path

	def __call__(self,filename):
		myimg = cv2.imread(self._path + "/" + filename)
		avg_color_per_row = numpy.average(myimg, axis=0)
		avg_color = numpy.average(avg_color_per_row, axis=0)
		return avg_color


class MyApp(wx.App):
	def OnInit(self):
		frame = LinearStitch(None, "Linear Stitch")
		self.SetTopWindow(frame)


		frame.Show(True)
		return True
if __name__ == '__main__':    
	qapp = QApplication(sys.argv)
	app = MyApp(redirect=True)
	app.MainLoop()


