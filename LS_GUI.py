### installation instruction for wxPython-Phoenix  : https://wiki.wxpython.org/How%20to%20install%20wxPython#Installing_wxPython-Phoenix_using_pip
### modified from : https://stackoverflow.com/questions/28417602/ask-multiple-directories-dialog-in-tkinter
###					https://wxpython.org/pages/overview/#hello-world

import os
import wx
import wx.lib.agw.multidirdialog as MDD

class MultiSelect(wx.Frame):
	# Our normal wxApp-derived class, as usual
	app = wx.App(0)

	#menu where directory selection(s) will be made
	dlg = MDD.MultiDirDialog(None, title="Custom MultiDirDialog", defaultPath=os.getcwd(),  # defaultPath="C:/Users/users/Desktop/",
    	             	    agwStyle=MDD.DD_MULTIPLE|MDD.DD_DIR_MUST_EXIST)
	
	#setup listbox list as global var
	init_list = []	
	cont = None

	def __init__(self, *args, **kargs):
		super(MultiSelect, self).__init__(*args, **kargs)

		#panel setup for button and listbox use
		panel = wx.Panel(self, size = (400,300))

		#app contains 4 buttons for interactive use
		exitbutton = wx.Button(panel, label="Exit", pos = (150,140), size = (100,60))
		clearbutton = wx.Button(panel, label="Clear All", pos = (150,180), size = (100,60))
		addbutton = wx.Button(panel, label = "+", pos = (50,50), size = (40,40))
		delbutton = wx.Button(panel, label = "-", pos = (50,110), size = (40,40))

		#event handling - button binded with functions
		self.Bind(wx.EVT_BUTTON, self.on_exit_button, exitbutton)
		self.Bind(wx.EVT_BUTTON, self.on_clear_button, clearbutton)
		self.Bind(wx.EVT_BUTTON, self.on_add_button, addbutton)
		self.Bind(wx.EVT_BUTTON, self.on_del_button, delbutton)

		#event handling - close app with "x" button located in corner
		self.Bind(wx.EVT_CLOSE, self.closewindow)

		#setup listbox
		self.cont = wx.ListBox(panel, -1, (100,50), (200,100), self.init_list, wx.LB_EXTENDED)

	#opens a new menu and closes when selection(s) is made
	#adds currently selected directory/directories to listbox
	def on_add_button(self, event):
		self.main()

	#deletes currently selected directory/directories from listbox
	def on_del_button(self,event):
		deleted_items = self.cont.GetSelections()
		deleted_items.reverse()
		for file in deleted_items:
			self.cont.Delete(file)
	
	#closes window, does NOT terminate app
	def on_exit_button(self, event):
		self.dlg.Destroy()
		self.Close(True)

	#deletes all current directories in listbox
	def on_clear_button(self, event):
		while (self.cont.GetCount() != 0):
			self.cont.Delete(0)

	#closes app
	def closewindow(self, event):
		self.Destroy()

	#obtains path for selected directory to be added to the listbox
	def main(self):
		if self.dlg.ShowModal() != wx.ID_OK:
			print("You Cancelled The Dialog!")
			self.dlg.Destroy()

		#obtains currently selected directory path
		paths = self.dlg.GetPaths() 
		for path in enumerate(paths):

			#adds string of currently selected directory to listbox
			#for windows os: dir_path= path[1].replace('OS (C:)','C:')
			dir_path = path[1].replace('Macintosh HD','')
			directory = [os.path.basename(dir_path)]
			self.cont.InsertItems(directory, 0)

			#any additional functionalty for selected directory 
			# should be added here

if __name__ == '__main__':
	app = wx.App()
	frame = MultiSelect(None, title = 'MultiFolderSelect')
	frame.Show()
	app.MainLoop()