import os
import wx
import wx.lib.agw.multidirdialog as MDD
import cv2
import numpy
import multiprocessing

import sys
from PyQt5.QtWidgets import (QFileDialog, QAbstractItemView, QListView,
                             QTreeView, QApplication, QDialog)

from os.path import isfile, isdir, join
from os.path import expanduser

import shutil

class Fixstack(wx.Frame):

    # Our normal wxApp-derived class, as usual
    app = wx.App(0)
    config = None

    #setup listbox list as global var
    init_list = []
    cont = None
    stackPath = ""
    sourcefolder = ""

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title,
                          pos=(150, 150), size=(600, 300))


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

        scale_horzSizer = wx.BoxSizer(wx.HORIZONTAL)
        selectScale = wx.Button(panel, label = "Select Stack Group")
        self.scaleControl = wx.TextCtrl(panel, size=(400, -1), style=wx.TE_READONLY)
        scale_horzSizer.Add(selectScale, 0, wx.ALL, 10);
        scale_horzSizer.Add(self.scaleControl, 0, wx.ALL, 10);


        badcore_horzSizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(panel, -1, style=wx.ALIGN_CENTER)
        lbl.SetLabel("Name of first bad stack:")
        self.badcore = wx.TextCtrl(panel, size=(300, -1), style=wx.TE_LEFT)
        badcore_horzSizer.Add(lbl, 0, wx.ALL, 10)
        badcore_horzSizer.Add(self.badcore, 0, wx.ALL, 10)


        num_horzSizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(panel, -1, style=wx.ALIGN_CENTER)
        lbl.SetLabel("Number of bad files:")
        self.number = wx.TextCtrl(panel, size=(30, -1), style=wx.TE_LEFT)
        num_horzSizer.Add(lbl, 0, wx.ALL, 10)
        num_horzSizer.Add(self.number, 0, wx.ALL, 10)


        sizer = wx.BoxSizer(wx.VERTICAL)


        panelCtrls_horzSizer = wx.BoxSizer( wx.HORIZONTAL )
        buttonSizer = wx.BoxSizer(wx.VERTICAL)

        self.AddLinearSpacer( sizer,10 )


        button_horzSizer = wx.BoxSizer( wx.HORIZONTAL )
        startProcessing = wx.Button(panel, label = "Fix")

        button_horzSizer.Add(startProcessing, 0, wx.ALL, 10);
        
        sizer.Add(scale_horzSizer, 0, wx.ALL, 10)
        sizer.Add(badcore_horzSizer, 0, wx.ALL, 10)
        sizer.Add(num_horzSizer, 0, wx.ALL, 10)
        sizer.Add(button_horzSizer, 0, wx.ALL, 10)
        sizer.Add(panelCtrls_horzSizer, 0, wx.ALL, 10)
        panel.SetSizer(sizer)
        panel.Layout()

        #event handling - button binded with functions
        # self.Bind(wx.EVT_BUTTON, self.on_exit_button, exitbutton)
        self.Bind(wx.EVT_BUTTON, self.startProcessing, startProcessing)
        self.Bind(wx.EVT_BUTTON, self.on_scale_button, selectScale)

        #event handling - close app with "x" button located in corner
        self.Bind(wx.EVT_CLOSE, self.on_exit_button)


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


    def on_scale_button(self, event):
        dlg = getExistingFiles()
        # dlg.setDirectory(self.config['General']['BrowsePath'])
        if dlg.exec_() == QDialog.Accepted:
            selectedFiles = dlg.selectedFiles()
            self.sourcefolder = selectedFiles[0]
            self.scaleControl.SetValue(self.sourcefolder)


    #terminates app
    def on_exit_button(self, event):
        self.Destroy()
    #closes window, does NOT terminate app
    def closewindow(self, event):
        self.Destroy()



    def startProcessing(self, event):
        sourcefolder = self.sourcefolder
        badstack = self.badcore.GetValue()
        num = int(self.number.GetValue())
        
        childrenStacks = [f for f in os.listdir(
            sourcefolder) if isdir(join(sourcefolder, f))]
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




class getExistingFiles(QFileDialog):
	def __init__(self, *args):
		super(getExistingFiles, self).__init__(*args)
		self.setOption(self.DontUseNativeDialog, True)
		self.setFileMode(self.Directory)
		self.setOption(self.ShowDirsOnly, True)


class MyApp(wx.App):
    def OnInit(self):
        frame = Fixstack(None, "Stack Fixer")
        self.SetTopWindow(frame)

        frame.Show(True)
        return True

qapp = QApplication(sys.argv)
app = MyApp(redirect=True)
app.MainLoop()

