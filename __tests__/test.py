import argparse, subprocess, os
import logging
from time import time, sleep

class Tester:
    def __init__(self):
        args = self.parseArgs()
        self.path = os.path.abspath(args.image)
        self.type = args.type
        self.logger = logging.getLogger('Tester')
        self.checkImage()
        if self.type == 'bios':
            self.testBIOS()
        elif self.type == 'uefi':
            self.testUEFI()
        else:
            raise ValueError("Invalid boot type")

    def parseArgs(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description='Test')
        parser.add_argument('image', type=str, help='Image Path')
        parser.add_argument('-t', '--type', type=str, help='Boot Type', choices=['bios', 'uefi'])
        return parser.parse_args()

    def checkImage(self):
        extension = self.path.split('.')[-1]
        if extension != 'iso':
            raise ValueError("Invalid image extension")
        if not os.path.exists(self.path):
            raise FileNotFoundError("Image not found")
        
    def test(self, cmd: list[str], bootFailMessage: list[str]):
        self.logger.info(f"Testing {self.type}")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        message = None
        timeout = 10 * 60
        startTime = time()
        try:
            for line in proc.stdout:
                print(line, end="")
                if proc.poll() is not None:
                    break
                for failMessage in bootFailMessage:
                    if failMessage in line:
                        message = "Failed to boot"
                        break
                if message is not None:
                    break
                if "Kernel panic" in line:
                    message = "Kernel panic"
                    break
                if time() - startTime > timeout:
                    message = "Timeout"
                    break
                sleep(1)
        finally:
            if proc.poll() is None:
                proc.terminate()
        if message is None:
            message = None if proc.poll() == 0 else f"Unknown Error: {proc.returncode}"
        if message is not None:
            raise RuntimeError(message)

    def testBIOS(self):
        cmd = ["qemu-system-x86_64", "-m", "256m", "-cdrom", self.path, "-boot", "d", "-nographic"]
        bootFailMessage = ["No bootable device"]
        self.test(cmd, bootFailMessage)

    def testUEFI(self):
        cmd = ["qemu-system-x86_64", "-m", "256m", "-cdrom", self.path, "-bios", "OVMF.fd", "-nographic"]
        bootFailMessage = ["failed to load Boot", "failed to start Boot", "Boot Failed"]
        self.test(cmd, bootFailMessage)

if __name__ == '__main__':
    tester = Tester()