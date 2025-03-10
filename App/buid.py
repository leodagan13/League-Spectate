# build.py
import PyInstaller.__main__
import shutil
import os

def build_exe():
    PyInstaller.__main__.run([
        'src/main.py',  # your main script
        '--name=LeagueStreamManager',  # name of your exe
        '--onefile',  # create a single exe file
        '--windowed',  # no console window
        '--icon=assets/icon.ico',  # if you have an icon
        '--add-data=assets;assets',  # include any additional files
        '--clean',  # clean cache before building
        '--noconsole',  # no console window
        # Add any additional python packages that need to be included
        '--hidden-import=pantheon',
        '--hidden-import=obswebsocket',
        '--hidden-import=pynput',
    ])

    # Copy default config if it exists
    if os.path.exists('config.default.json'):
        shutil.copy('config.default.json', 'dist/config.default.json')

if __name__ == "__main__":
    build_exe()