import PyInstaller.__main__
import main
import os

icon_path = os.path.join('icon.ico')
PyInstaller.__main__.run(['--name=emubt', '-F', '--windowed', '-i={}'.format(icon_path),
                          '--specpath=spec', '--onefile',
                          '__main__.py'])