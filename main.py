import stitcher
import numpy as np
import os
import tkinter
from tkinter import filedialog
from stitcher import Stitcher
import _thread

class MyFirstGUI:

	fileList = None;
	progress = 0;

	def __init__(self, master):
		self.master = master
		master.title("Stitcher")
		self.outputFile = ""
		self.browse_button = tkinter.Button(master, text="Select Files", command=self.browseFiles)
		self.browse_button.pack()

		self.save_file = tkinter.Button(master, text="Output File", command=self.saveFile)
		self.save_file.pack()

		frame1 = tkinter.Frame(master)
		frame1.pack(fill=tkinter.X)

		self.file_label_text = tkinter.StringVar()
		self.file_label_text.set(self.outputFile)
		self.file_label = tkinter.Label(frame1, textvariable=self.file_label_text)
		self.label = tkinter.Label(frame1, text="Output File:")
		self.label.pack(side=tkinter.LEFT, padx=5, pady=5);
		self.file_label.pack(fill=tkinter.X, padx=5, expand=True);


		self.stitch = tkinter.Button(master, text="Stitch", command=self.stitch)
		self.stitch.pack(side=tkinter.LEFT)

		self.progressText = tkinter.IntVar()
		self.progressText.set(self.progress)
		
		self.progress_label = tkinter.Label(master, textvariable=self.progressText)
		self.progress_label.pack();
		
	def browseFiles(self):
		# Tk().withdraw()
		files = filedialog.askopenfilenames(filetypes = (("JPEG", "*.jpeg"),("JPEG", "*.jpg")
														 ,("PNG", "*.png")
														 ,("All files", "*.*") ))
		self.fileList = root.tk.splitlist(files)

	def saveFile(self):
		# Tk().withdraw()
		self.outputFile = filedialog.asksaveasfilename(filetypes=[("TIFF", ".tiff")], title="Select Output File")
		self.file_label_text.set(self.outputFile)

	def stitch(self):
		stitcherHandler = Stitcher()
		print(self.fileList)
		print(self.outputFile);
		_thread.start_new_thread(stitcherHandler.stitchFileList, (self.fileList, self.outputFile, self.progressCallback))


	def progressCallback(self, status, progress):
		self.progressText.set(progress);


root = tkinter.Tk()
root.geometry('{}x{}'.format(640, 300))
my_gui = MyFirstGUI(root)
root.mainloop()