# stdlib
import configparser
import sys
import pathlib
import os
# 3rd party
import appdirs

homedir = pathlib.Path.home()
class LSConfig:
	
	configValues = {}

	def __init__(self):
		self.configfile = pathlib.Path(appdirs.user_config_dir("LinearStitch")) / "config.ini"
		self.Config = configparser.ConfigParser()
		
		if not self.configfile.is_file():
			print("Creating Configuration file")
			self.__load_defaults()
		else:
			print("Loading Internal Configuration")
			self._load_from_file()
			
	def __load_defaults(self):
		# Touch file
		isExist = os.path.exists(self.configfile.parent)
		if not isExist:
			os.makedirs(self.configfile.parent)

		self.configfile.write_text("""
[General]
[Zerene]
[Processing]
[FocusStack]
		""")
		
		self._load_from_file()
		return
	
	def _load_from_file(self):
		self.Config.read(self.configfile)
		
		if "General" not in self.Config:
			self.Config["General"] = {}
		if "Zerene" not in self.Config:
			self.Config["Zerene"] = {}
		if "Processing" not in self.Config:
			self.Config["Processing"] = {}
		if "FocusStack" not in self.Config:
			self.Config["FocusStack"] = {}
			
		self.configValues["BrowsePath"] = self.Config.get("General", "BrowsePath", fallback=str(homedir.absolute()))
		self.configValues["ArchivePath"] = self.Config.get("General", "ArchivePath", fallback=str(homedir.absolute()))
		self.configValues["CoreOutputPath"] = self.Config.get("General", "CoreOutputPath", fallback=str(homedir.absolute()))
		self.configValues["ZereneInstall"] = self.Config.get("Zerene", "Install", fallback=str(homedir.absolute()))
		self.configValues["ZereneLicense"] = self.Config.get("Zerene", "License", fallback="{{APPDATA}}/ZereneStacker/")
		self.configValues["ZereneLaunchPath"] = self.Config.get("Zerene", "LaunchPath", fallback='"{{Install}}jre/bin/java.exe" -Xmx8000m -DjavaBits=64bitJava -Dlaunchcmddir="{{License}}" -classpath "{{Install}}ZereneStacker.jar;{{Install}}JREextensions/*" com.zerenesystems.stacker.gui.MainFrame -noSplashScreen -exitOnBatchScriptCompletion -runMinimized  -batchScript "{{script}}"')
		self.configValues["ZereneTemplateFile"] = self.Config.get("Zerene", "TemplateFile", fallback="zereneTemplate.xml")
		self.configValues["CoreCount"] = self.Config.get("Processing", "CoreCount", fallback="4")
		self.configValues["FocusThreshold"] = self.Config.get("Processing", "FocusThreshold", fallback="13.0")
		self.configValues["FocusStackInstall"] = self.Config.get("FocusStack", "Install", fallback=str(homedir.absolute()))
		self.configValues["FocusStackLaunchPath"] = self.Config.get("FocusStack", "LaunchPath", fallback='"{{Install}}" --consistency=0 --align-keep-size --jpgquality=100 --output="{{outputPath}}" "{{folderPath}}/"*jpg')
			
	def save_config(self):

		# Configuration
		self.Config.set("General", "BrowsePath", self.configValues["BrowsePath"])
		self.Config.set("General", "ArchivePath", self.configValues["ArchivePath"])
		self.Config.set("General", "CoreOutputPath",self.configValues["CoreOutputPath"])

		self.Config.set("Zerene", "Install", self.configValues["ZereneInstall"])
		self.Config.set("Zerene", "License", self.configValues["ZereneLicense"])
		self.Config.set("Zerene", "LaunchPath",self.configValues["ZereneLaunchPath"])
		self.Config.set("Zerene", "TemplateFile",self.configValues["ZereneTemplateFile"])
	
		self.Config.set("Processing", "CoreCount",self.configValues["CoreCount"])
		self.Config.set("Processing", "FocusThreshold",self.configValues["FocusThreshold"])
		
		self.Config.set("FocusStack", "Install",self.configValues["FocusStackInstall"])
		self.Config.set("FocusStack", "LaunchPath",self.configValues["FocusStackLaunchPath"])
		
		with open(self.configfile, "w") as f:
			self.Config.write(f)


if __name__ == "__main__":
	sys.exit(1)