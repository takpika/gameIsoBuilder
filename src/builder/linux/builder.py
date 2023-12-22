import argparse, sys, os, subprocess
from typing import Optional

from src.logic.runtime import Runtime

class LinuxBuilder:
    def __init__(self, output: str, folder: str, initCmd: str, name: str, version: str, resolution: str):
        Runtime.checkRoot()
        self.output = os.path.abspath(output)
        self.folder = folder
        self.initCmd = initCmd
        self.name = name
        self.version = version
        self.resolution = resolution
    
    def copyConfig(self, dst: str, replace: dict = {}):
        fileName = os.path.basename(dst)
        if not os.path.exists(os.path.join("configs/", fileName)):
            print(f"Config {fileName} not found")
            return
        original = open(os.path.join("configs/", fileName), 'r').read()
        for key, value in replace.items():
            original = original.replace(key, value)
        open(dst, 'w').write(original)
    
    def runCmd(self, cmd: str, ignoreError: bool = False):
        res = subprocess.run(["chroot", ".tmp/rootdir", "sh", "-c", "DEBIAN_FRONTEND=noninteractive " + cmd.replace("\n", " ")])
        if not ignoreError and res.returncode != 0:
            raise Exception("Command failed")
        if cmd.startswith("apt "):
            subprocess.run(["chroot", ".tmp/rootdir", "sh", "-c", "apt clean"])

    def runLocalCmd(self, cmd: str, ignoreError: bool = False):
        res = subprocess.run(["sh", "-c", cmd.replace("\n", " ")])
        if not ignoreError and res.returncode != 0:
            raise Exception("Command failed")

    def calcFolderSize(self, folder: str) -> int:
        totalSize = 0
        for dirpath, dirnames, filenames in os.walk(folder):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                totalSize += os.path.getsize(fp)
            for d in dirnames:
                fp = os.path.join(dirpath, d)
                totalSize += self.calcFolderSize(fp)
        return totalSize
    
    def getDisableServices(self) -> list[str]:
        services = []
        for line in open('configs/disable-services.txt', 'r').readlines():
            line = line.strip()
            if line.startswith('#') or line == '':
                continue
            services.append(line)
        return services
    
    def cleanRootFS(self):
        ### Cleanup
        self.runLocalCmd('df -h | grep /dev/loop0')
        self.runCmd('apt autoremove -y')
        self.runLocalCmd('umount .tmp/rootdir/dev/pts')
        self.runLocalCmd('umount .tmp/rootdir/dev')
        self.runLocalCmd('umount .tmp/rootdir/proc')
        self.runLocalCmd('umount .tmp/rootdir/sys')
        self.runLocalCmd('umount .tmp/rootdir')
        self.runLocalCmd('e2fsck -f -y .tmp/rootfs.img')
        self.runLocalCmd('resize2fs -M .tmp/rootfs.img')
        # delete ubuntu
        self.runLocalCmd('rm -rf /tmp/ubuntu.tar.gz')
    
    def buildRootFS(self):
        self.runLocalCmd('dd if=/dev/zero of=.tmp/rootfs.img bs=1M count=3584')
        self.runLocalCmd('mkfs.ext4 .tmp/rootfs.img')
        self.runLocalCmd('mount -o loop .tmp/rootfs.img .tmp/rootdir')
        
        ### Setup Ubuntu
        if not os.path.exists("/tmp/ubuntu.tar.gz"):
            self.runLocalCmd('curl -o /tmp/ubuntu.tar.gz https://cdimage.ubuntu.com/ubuntu-base/releases/20.04/release/ubuntu-base-20.04.1-base-amd64.tar.gz')
        self.runLocalCmd('tar -xzf /tmp/ubuntu.tar.gz -C .tmp/rootdir')
        self.runLocalCmd('mount --bind /dev .tmp/rootdir/dev')
        self.runLocalCmd('mount --bind /dev/pts .tmp/rootdir/dev/pts')
        self.runLocalCmd('mount --bind /proc .tmp/rootdir/proc')
        self.runLocalCmd('mount --bind /sys .tmp/rootdir/sys')
        self.runLocalCmd('cp /etc/resolv.conf .tmp/rootdir/etc/resolv.conf')
        ### Setup System
        #set root password
        self.runCmd('echo "root:root" | chpasswd')
        self.runCmd('chsh -s /bin/bash root')
        self.runCmd('apt update')
        self.runCmd('apt install -y tzdata')
        self.runCmd('apt install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" keyboard-configuration')
        self.runCmd('apt install -y linux-image-generic --no-install-recommends --no-install-suggests')
        self.runCmd('apt install -y systemd systemd-sysv --no-install-recommends --no-install-suggests')
        self.runCmd('echo "Game" > /etc/hostname')
        self.runCmd('systemctl enable serial-getty@ttyS0.service')

        ### Setup Partition Mount
        self.runCmd('echo "tmpfs /tmp tmpfs defaults,size=1m 0 0" >> /etc/fstab')
        self.runCmd('echo "tmpfs /var/log tmpfs defaults,size=1m 0 0" >> /etc/fstab')
        self.runCmd('cat /etc/fstab')

        ### Install Softwares
        self.runCmd('apt install -y xserver-xorg-core xserver-xorg-video-fbdev x11-xserver-utils xinit xinput --no-install-recommends --no-install-suggests')
        self.runCmd('apt install -y xserver-xorg-input-wacom xserver-xorg-input-mouse xserver-xorg-input-kbd xserver-xorg-input-libinput --no-install-recommends --no-install-suggests')
        self.runCmd('apt install -y pulseaudio ca-certificates eject psmisc --no-install-recommends --no-install-suggests')
        ### Setup Xinit
        self.copyConfig(".tmp/rootdir/usr/local/bin/set-resolution.sh", replace={"{{RESOLUTION}}": self.resolution})
        self.runCmd('chmod +x /usr/local/bin/set-resolution.sh')
        self.runCmd('echo "/usr/local/bin/set-resolution.sh ' + self.resolution + '" >> /root/.xinitrc')
        self.runCmd('echo "cd /app && LANG=ja_JP.UTF-8 LC_ALL="ja_JP" /usr/lib/wine/wine ' + self.initCmd + '; /sbin/poweroff" >> /root/.xinitrc')
        self.runCmd('chmod +x /root/.xinitrc')

        ### Setup Service
        if not os.path.exists(".tmp/rootdir/etc/systemd/system/getty@tty1.service.d/"):
            self.runLocalCmd('mkdir -p .tmp/rootdir/etc/systemd/system/getty@tty1.service.d/')
        self.runCmd('echo "[Service]" >> /etc/systemd/system/getty@tty1.service.d/override.conf')
        self.runCmd('echo "ExecStart=" >> /etc/systemd/system/getty@tty1.service.d/override.conf')
        self.copyConfig(".tmp/rootdir/etc/systemd/system/shutdown.service")
        self.copyConfig(".tmp/rootdir/etc/systemd/system/xorg.service")
        self.runCmd('systemctl enable shutdown.service xorg.service')
        for service in self.getDisableServices():
            self.runCmd('systemctl disable ' + service)
            self.runCmd('systemctl mask ' + service)

        ### Install Wine
        self.runCmd('dpkg --add-architecture i386 && apt update')
        self.runCmd('apt install -y wine32 winetricks --no-install-recommends --no-install-suggests')
        #self.runCmd('dpkg --remove-architecture i386')
        self.runCmd('/usr/lib/wine/wine cmd /c ver')
        self.runCmd('/usr/bin/winetricks fakejapanese_ipamona')

        ### Copy Files
        self.runLocalCmd('mkdir -p .tmp/rootdir/app')
        self.runLocalCmd('cp -r ' + self.folder + '/* .tmp/rootdir/app')

    def buildISO(self):
        self.runLocalCmd('mkdir -p .tmp/isoroot/boot .tmp/isoroot/isolinux .tmp/isoroot/EFI/BOOT')
        if not os.path.exists('syslinux-6.03.tar.gz'):
            self.runLocalCmd('curl -LO https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.tar.gz')
        self.runLocalCmd('tar -xzf syslinux-6.03.tar.gz')
        
        self.runLocalCmd('cp -a syslinux-6.03/bios/core/isolinux.bin .tmp/isoroot/isolinux/isolinux.bin')
        self.runLocalCmd('cp syslinux-6.03/bios/com32/elflink/ldlinux/ldlinux.c32 .tmp/isoroot/isolinux/ldlinux.c32')

        self.runLocalCmd('mkdir -p .tmp/efiboot')
        self.runLocalCmd('dd if=/dev/zero of=.tmp/efiboot.img bs=1k count=1440')
        self.runLocalCmd('/usr/sbin/mkfs.msdos -F 12 -M 0xf8 -n "EFI" .tmp/efiboot.img')
        self.runLocalCmd('mount -o loop .tmp/efiboot.img .tmp/efiboot && mkdir -p .tmp/efiboot/EFI/BOOT')
        self.runLocalCmd('cp -a syslinux-6.03/efi64/efi/syslinux.efi .tmp/efiboot/EFI/BOOT/BOOTX64.EFI')
        self.runLocalCmd('umount .tmp/efiboot && rm -rf .tmp/efiboot')
        self.runLocalCmd('mv .tmp/efiboot.img .tmp/isoroot/isolinux/efiboot.img')

        self.copyConfig('.tmp/isoroot/isolinux/isolinux.cfg', {"{{CDLABEL}}": self.name})
        self.runCmd('apt install -y dracut xz-utils --no-install-recommends --no-install-suggests')
        self.runCmd('dracut --xz --force --add "dmsquash-live convertfs pollcdrom" --omit plymouth --no-hostonly --no-early-microcode /boot/initrd.img `ls /lib/modules`')
        self.runCmd('apt remove -y lvm2 xz-utils')
        self.runLocalCmd('cp .tmp/rootdir/boot/initrd.img .tmp/isoroot/boot/initrd.img')
        self.runLocalCmd('cp .tmp/rootdir/boot/vmlinuz .tmp/isoroot/boot/vmlinuz')
        self.runCmd('rm -rf /boot/initrd.img /boot/vmlinuz')
        self.cleanRootFS()
        self.runLocalCmd('mkdir -p .tmp/squashfsroot/LiveOS')
        self.runLocalCmd('mv .tmp/rootfs.img .tmp/squashfsroot/LiveOS/rootfs.img')
        self.runLocalCmd('mksquashfs .tmp/squashfsroot .tmp/squashfs.img')
        self.runLocalCmd('mkdir -p .tmp/isoroot/LiveOS')
        self.runLocalCmd('mv .tmp/squashfs.img .tmp/isoroot/LiveOS/squashfs.img')
        self.runLocalCmd(f'''
            mkisofs -o "{self.output}" -R -J -T -V "{self.name}"
            -b isolinux/isolinux.bin
            -no-emul-boot -boot-load-size 4 -boot-info-table
            -eltorito-alt-boot -eltorito-platform efi -eltorito-boot isolinux/efiboot.img
            .tmp/isoroot
        ''')

    def build(self) -> str:
        try:
            if not os.path.exists('.tmp'):
                self.runLocalCmd('mkdir .tmp')
            if os.path.exists('.tmp/isoroot'):
                self.runLocalCmd('rm -rf .tmp/isoroot')
            self.runLocalCmd('mkdir -p .tmp/isoroot')
            if os.path.exists('.tmp/rootdir'):
                self.runLocalCmd('rm -rf .tmp/rootdir')
            self.runLocalCmd('mkdir -p .tmp/rootdir')
            self.buildRootFS()
            self.buildISO()
            return self.output
        except Exception as e:
            self.cleanRootFS()
            raise e