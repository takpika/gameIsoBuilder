import os

from src.logic.runtime import Runtime

class WindowsBuilder:
    def __init__(self, output: str, folder: str, initCmd: str, name: str, version: str, resolution: str, debug: bool = False):
        Runtime.checkRoot()
        self.output = os.path.abspath(output)
        self.folder = folder
        self.initCmd = initCmd
        self.name = name
        self.version = version
        self.resolution = resolution
        self.debug = False

    def build(self) -> str:
        pass