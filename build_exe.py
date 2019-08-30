import PyInstaller.__main__
import main
import os

icon_path = os.path.join('spec', 'icon.ico')
PyInstaller.__main__.run(['--name=emubt', '-F', '--windowed', '-i={}'.format(icon_path),
                          '--specpath=spec', '--onefile',
                          'main_release.py'])


# PyInstaller.__main__.run(['--name=totest', '-F', '-i={}'.format(icon_path),
#                           '--specpath=spec', '--onefile',
#                           'tmp.py'])