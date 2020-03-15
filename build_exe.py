import PyInstaller.__main__
import main
import os, platform, sys

system_name = platform.system() + platform.release()

cwd = os.getcwd()
icon_path = os.path.join(cwd, 'spec', 'icon.ico')

#console
# PyInstaller.__main__.run(['--name=emubt', '-F', '-i={}'.format(icon_path),
#                           '--specpath=spec', '--onefile',
#                           'main_release.py'])

#no console
PyInstaller.__main__.run(['--name=emubt_{}'.format(system_name), '-F', '--windowed', '-i={}'.format(icon_path),
                          '--specpath=spec', '--onefile',
                          'main_release.py'])


# PyInstaller.__main__.run(['--name=totest', '-F', '-i={}'.format(icon_path),
#                           '--specpath=spec', '--onefile',
#                           'tmp.py'])