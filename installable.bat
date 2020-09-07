pyinstaller LS_GUI.spec -yFw
copy zereneTemplate.xml dist\
copy config.sample.ini dist\
7z a .\docs\linearstitch.zip dist\
