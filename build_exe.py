import PyInstaller.__main__
import main
import os

#pyinstaller -F -i icon.ico --noconsole -n emubt main.py

PyInstaller.__main__.run(['--name=emubt', '-F', '--noconsole', '-i=icon.ico', '--specpath=spec', 'main.py'])