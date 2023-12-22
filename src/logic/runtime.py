import os
import sys

class Runtime:
    @staticmethod
    def isRoot() -> bool:
        return os.geteuid() == 0
    
    @staticmethod
    def checkRoot():
        if not Runtime.isRoot():
            print('You must run this script as root!')
            sys.exit(1)