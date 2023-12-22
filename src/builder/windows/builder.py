import os

from src.logic.runtime import Runtime

class WindowsBuilder:
    def __init__(self, output: str, folder: str, initCmd: str, name: str, version: str, resolution: str):
        Runtime.checkRoot()
        self.output = os.path.abspath(output)
        self.folder = folder
        self.initCmd = initCmd
        self.name = name
        self.version = version
        self.resolution = resolution

    def build(self) -> str:
        pass