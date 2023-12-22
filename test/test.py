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

    def testBIOS(self):
        cmd = ["qemu-system-x86_64", "-m", "256m", "-cdrom", self.path, "-boot", "d", "-nographic"]
        self.logger.info("Testing BIOS")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = True
        timeout = 10 * 60
        try:
            for line in proc.stdout:
                if proc.poll() is not None:
                    break
                if "No bootable device" in line:
                    success = False
                    break
                if time() > timeout:
                    success = False
                    break
                sleep(1)
        except:
            success = False
        finally:
            if proc.poll() is None:
                proc.terminate()
        if success:
            success = proc.poll() == 0
        if not success:
            raise RuntimeError("BIOS Test Failed")

    def testUEFI(self):
        cmd = ["qemu-system-x86_64", "-m", "256m", "-cdrom", self.path, "-bios", "OVMF.fd", "-nographic"]
        self.logger.info("Testing UEFI")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = True
        timeout = 10 * 60
        try:
            for line in proc.stdout:
                if proc.poll() is not None:
                    break
                if "filed to load Boot" in line:
                    success = False
                    break
                if time() > timeout:
                    success = False
                    break
                sleep(1)
        except:
            success = False
        finally:
            if proc.poll() is None:
                proc.terminate()
        if success:
            success = proc.poll() == 0
        if not success:
            raise RuntimeError("UEFI Test Failed")

if __name__ == '__main__':
    tester = Tester()