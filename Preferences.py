import wx;

from PyQt5.QtWidgets import (QFileDialog, QDialog, QListView, QAbstractItemView, QTreeView)

class PreferencesEditor(wx.PreferencesEditor):
    def __init__(self, config):
        super().__init__('Preferences')
        self.general = GeneralPreferencesPage(config)
        self.AddPage(self.general)
        

class GeneralPreferencesPage(wx.StockPreferencesPage):
    def __init__(self, config):
        super().__init__(wx.StockPreferencesPage.Kind_General)
        self.config = config

    def CreateWindow(self, parent):
        # THe main container window
        panel = wx.Panel(parent)

        panel.SetMinSize((600, 430))
        fgSizer1 = wx.FlexGridSizer( 0, 3, 0, 0 )
        fgSizer1.AddGrowableCol( 1 )
        fgSizer1.SetFlexibleDirection( wx.BOTH )
        fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_ALL )

        self.m_staticText1 = wx.StaticText( panel, wx.ID_ANY, u"Browse Path", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText1.Wrap( -1 )

        fgSizer1.Add( self.m_staticText1, 0, wx.ALL, 5 )

        self.browsePath = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,-1 ), 0 )
        fgSizer1.Add( self.browsePath, 1, wx.ALL|wx.EXPAND, 5 )

        self.m_button1 = wx.Button( panel, wx.ID_ANY, u"Browse", wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.m_button1, 0, wx.ALL, 5 )

        self.m_staticText2 = wx.StaticText( panel, wx.ID_ANY, u"Archive Path", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText2.Wrap( -1 )

        fgSizer1.Add( self.m_staticText2, 0, wx.ALL, 5 )

        self.archivePath = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,-1 ), 0 )
        fgSizer1.Add( self.archivePath, 1, wx.ALL|wx.EXPAND, 5 )

        self.m_button2 = wx.Button( panel, wx.ID_ANY, u"Browse", wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.m_button2, 0, wx.ALL, 5 )

        self.m_staticText3 = wx.StaticText( panel, wx.ID_ANY, u"Core Output Path", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText3.Wrap( -1 )

        fgSizer1.Add( self.m_staticText3, 0, wx.ALL, 5 )

        self.corePath = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,-1 ), 0 )
        fgSizer1.Add( self.corePath, 1, wx.ALL|wx.EXPAND, 5 )

        self.m_button3 = wx.Button( panel, wx.ID_ANY, u"Browse", wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.m_button3, 0, wx.ALL, 5 )

        self.m_staticText5 = wx.StaticText( panel, wx.ID_ANY, u"Zerene Path", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText5.Wrap( -1 )

        fgSizer1.Add( self.m_staticText5, 0, wx.ALL, 5 )

        self.zerenePath = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.zerenePath, 0, wx.ALL|wx.EXPAND, 5 )

        self.m_button4 = wx.Button( panel, wx.ID_ANY, u"Browse", wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.m_button4, 0, wx.ALL, 5 )

        self.m_staticText6 = wx.StaticText( panel, wx.ID_ANY, u"Zerene License", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText6.Wrap( -1 )

        fgSizer1.Add( self.m_staticText6, 0, wx.ALL, 5 )

        self.zereneLicense = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.zereneLicense, 0, wx.ALL|wx.EXPAND, 5 )

        fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )
        self.m_staticText7 = wx.StaticText( panel, wx.ID_ANY, u"Zerene Launch", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText7.Wrap( -1 )

        fgSizer1.Add( self.m_staticText7, 0, wx.ALL, 5 )

        self.zereneLaunch = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.zereneLaunch, 0, wx.ALL|wx.EXPAND, 5 )


        fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_staticText9 = wx.StaticText( panel, wx.ID_ANY, u"Zerene Template", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText9.Wrap( -1 )

        fgSizer1.Add( self.m_staticText9, 0, wx.ALL, 5 )

        self.zereneTemplate = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.zereneTemplate, 0, wx.ALL|wx.EXPAND, 5 )


        fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_staticText10 = wx.StaticText( panel, wx.ID_ANY, u"Core Count", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText10.Wrap( -1 )

        fgSizer1.Add( self.m_staticText10, 0, wx.ALL, 5 )

        self.coreCount = wx.SpinCtrl( panel, wx.ID_ANY, u"4", wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 2, 32, 0 )
        fgSizer1.Add( self.coreCount, 0, wx.ALL, 5 )


        fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_staticText11 = wx.StaticText( panel, wx.ID_ANY, u"Focus Threshold", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText11.Wrap( -1 )

        fgSizer1.Add( self.m_staticText11, 0, wx.ALL, 5 )

        self.focusThreshold = wx.SpinCtrlDouble( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0, 20, 0, 1 )
        self.focusThreshold.SetDigits( 1 )
        fgSizer1.Add( self.focusThreshold, 0, wx.ALL, 5 )

        fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_staticText11 = wx.StaticText( panel, wx.ID_ANY, u"Vignette Magic Number", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText11.Wrap( -1 )
        fgSizer1.Add( self.m_staticText11, 0, wx.ALL, 5 )
 
        self.vignetteMagic = wx.SpinCtrlDouble( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0, 20, 0, 0.1 )
        self.vignetteMagic.SetDigits( 1 )
        fgSizer1.Add( self.vignetteMagic, 0, wx.ALL, 5 )


        fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )


        self.m_staticText12 = wx.StaticText( panel, wx.ID_ANY, u"Focus Stack Path", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText12.Wrap( -1 )

        fgSizer1.Add( self.m_staticText12, 0, wx.ALL, 5 )

        self.focusStack = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.focusStack, 0, wx.ALL|wx.EXPAND, 5 )

        self.m_button6 = wx.Button( panel, wx.ID_ANY, u"Browse", wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.m_button6, 0, wx.ALL, 5 )

        self.focuslabel = wx.StaticText( panel, wx.ID_ANY, u"Focus Stack Launch", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.focuslabel.Wrap( -1 )

        fgSizer1.Add( self.focuslabel, 0, wx.ALL, 5 )

        self.focusLaunch = wx.TextCtrl( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.focusLaunch, 0, wx.ALL|wx.EXPAND, 5)
		
        fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )
        self.m_button7 = wx.Button( panel, wx.ID_ANY, u"Save", wx.DefaultPosition, wx.DefaultSize, 0 )
        fgSizer1.Add( self.m_button7, 0, wx.ALL, 5 )

        panel.SetSizer( fgSizer1 )
        panel.Layout()

        # Connect Events
        self.m_button1.Bind( wx.EVT_BUTTON, self.browseForFiles )
        self.zereneLaunch.Bind( wx.EVT_KILL_FOCUS, self.save )
        self.zereneTemplate.Bind( wx.EVT_KILL_FOCUS, self.save )
        self.focusLaunch.Bind( wx.EVT_KILL_FOCUS, self.save )
        # Connect Events
        self.m_button1.Bind( wx.EVT_BUTTON, lambda event: self.browseForDirectories(event, 'BrowsePath') )
        self.m_button2.Bind( wx.EVT_BUTTON, lambda event: self.browseForDirectories(event, 'ArchivePath') )
        self.m_button3.Bind( wx.EVT_BUTTON, lambda event: self.browseForDirectories(event, 'CoreOutputPath') )
        self.m_button4.Bind( wx.EVT_BUTTON, lambda event: self.browseForFiles(event, 'ZereneLaunchPath') )
        self.m_button6.Bind( wx.EVT_BUTTON, lambda event: self.browseForFiles(event, 'FocusStackInstall') )
        self.m_button7.Bind( wx.EVT_BUTTON,  self.save )
        self.reload()
        
        return panel
    

    def save(self, event=None):
        print("HEY")
        self.config.configValues['ZereneLicense'] = self.zereneLicense.GetValue()
        self.config.configValues['ZereneLaunchPath'] = self.zereneLaunch.GetValue()
        self.config.configValues['ZereneTemplateFile'] = self.zereneTemplate.GetValue()
        self.config.configValues['CoreCount'] = str(self.coreCount.GetValue())
        self.config.configValues['VignetteMagic'] = str(self.vignetteMagic.GetValue())
        self.config.configValues['FocusThreshold'] = str(self.focusThreshold.GetValue())
        self.config.configValues['FocusStackLaunchPath'] = self.focusLaunch.GetValue()
        self.config.save_config()
    
    def reload(self, event=None):
        
        self.browsePath.SetValue(self.config.configValues["BrowsePath"])
        self.archivePath.SetValue(self.config.configValues["ArchivePath"])
        self.corePath.SetValue(self.config.configValues["CoreOutputPath"])
        self.zerenePath.SetValue(self.config.configValues["ZereneInstall"])
        self.zereneLicense.SetValue(self.config.configValues["ZereneLicense"])
        self.zereneLaunch.SetValue(self.config.configValues["ZereneLaunchPath"])
        self.zereneTemplate.SetValue(self.config.configValues["ZereneTemplateFile"])
        self.coreCount.SetValue(self.config.configValues["CoreCount"])
        self.vignetteMagic.SetValue(self.config.configValues["VignetteMagic"])
        self.focusThreshold.SetValue(self.config.configValues["FocusThreshold"])
        self.focusStack.SetValue(self.config.configValues["FocusStackInstall"])
        self.focusLaunch.SetValue(self.config.configValues["FocusStackLaunchPath"])


    def browseForFiles( self, event, target):
        dlg = getExistingFiles()
        if dlg.exec_() == QDialog.Accepted:
            self.config.configValues[target] = dlg.selectedFiles()[0]
            self.save();
            self.reload();

    def browseForDirectories(self, event, target):
        dlg = getExistingDirectories()
        dlg.setDirectory(self.config.configValues[target])
        if dlg.exec_() == QDialog.Accepted:
            self.config.configValues[target] = dlg.selectedFiles()[0]
            self.save();
            self.reload();

class getExistingFiles(QFileDialog):
        def __init__(self, *args):
            super(getExistingFiles, self).__init__(*args)
            self.setOption(self.DontUseNativeDialog, True)
            self.setFileMode(self.ExistingFile)
            self.setOption(self.ShowDirsOnly, False)

class getExistingDirectories(QFileDialog):
    def __init__(self, *args):
        super(getExistingDirectories, self).__init__(*args)
        self.setOption(self.DontUseNativeDialog, True)
        self.setFileMode(self.Directory)
        self.setOption(self.ShowDirsOnly, True)
        # self.setDirectory(args[0])
        self.findChildren(QListView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.findChildren(QTreeView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
