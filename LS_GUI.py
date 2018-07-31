####### Retrieve a list of directories with wxPython-Phoenix   - tested on python3.5
### installation instruction for wxPython-Phoenix  : https://wiki.wxpython.org/How%20to%20install%20wxPython#Installing_wxPython-Phoenix_using_pip
### modified from : https://wxpython.org/Phoenix/docs/html/wx.lib.agw.multidirdialog.html
import os
import wx
import wx.lib.agw.multidirdialog as MDD

class MultiSelect(wx.Frame):
	# Our normal wxApp-derived class, as usual
	app = wx.App(0)
	dlg = MDD.MultiDirDialog(None, title="Custom MultiDirDialog", defaultPath=os.getcwd(),  # defaultPath="C:/Users/users/Desktop/",
    	             	    agwStyle=MDD.DD_MULTIPLE|MDD.DD_DIR_MUST_EXIST)
	#setup listbox as global var
	init_list = []
	cont = None

	def __init__(self, *args, **kargs):
		super(MultiSelect, self).__init__(*args, **kargs)
		panel = wx.Panel(self, size = (400,300))
		exitbutton = wx.Button(panel, label="Exit", pos = (150,150), size = (100,60))
		addbutton = wx.Button(panel, label = "+", pos = (50,50), size = (40,40))
		delbutton = wx.Button(panel, label = "-", pos = (50,110), size = (40,40))

		#bind button with functions
		self.Bind(wx.EVT_BUTTON, self.on_add_button, addbutton)
		self.Bind(wx.EVT_BUTTON, self.on_del_button, delbutton)
		self.Bind(wx.EVT_BUTTON, self.on_exit_button, exitbutton)
		self.Bind(wx.EVT_CLOSE, self.closewindow)

		#setup listbox
		self.cont = wx.ListBox(panel, -1, (100,50), (200,100), self.init_list, wx.LB_EXTENDED)


	def on_add_button(self, event):
		#self.reset_listbox()
		self.main()

	def on_del_button(self,event):
		deleted_items = self.cont.GetSelections()
		deleted_items.reverse()
		for file in deleted_items:
			self.cont.Delete(file)
	
	def on_exit_button(self, event):
		self.dlg.Destroy()
		self.Close(True)
		#BUG: not closing properly

	def closewindow(self, event):
		self.Destroy()

	def reset_listbox(self):
		while (self.cont.GetCount() != 0):
			self.cont.Delete(0)

	def main(self):
		if self.dlg.ShowModal() != wx.ID_OK:
			print("You Cancelled The Dialog!")
			self.dlg.Destroy()
		paths = self.dlg.GetPaths()
		#Print directories' path and files 
		dir_list = []
		for path in enumerate(paths):
			#print(path[1])
			directory= path[1].replace('Macintosh HD','')
			#windows os: directory= path[1].replace('OS (C:)','C:')
			print(directory)
			for file in os.listdir(directory):
				dir_list.append(file)
				print(file)
		self.cont.InsertItems(dir_list, 0)

if __name__ == '__main__':
	app = wx.App()
	frame = MultiSelect(None, title = 'MultiFolderSelect')
	frame.Show()
	app.MainLoop()