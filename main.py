import argparse, sys, os, subprocess, re

class LinuxWineIsoBuilder:
    def __init__(self):
        self.checkRoot()
        self.args = self.parseArgs()
        self.output = os.path.abspath(self.args.output)
        self.folder = self.args.folder
        self.initCmd = self.args.initCmd
        self.name = self.args.name
        self.version = self.args.version
        self.screenResolution = self.args.resolution

    def checkRoot(self):
        if os.geteuid() != 0:
            print('You must run this script as root!')
            sys.exit(1)

    def parseArgs(self):
        parser = argparse.ArgumentParser(description='Linux GUI ISO Builder')
        parser.add_argument('output', type=str, help='Output ISO file')
        parser.add_argument('--folder', type=str, help='Folder to include in ISO')
        parser.add_argument('--initCmd', type=str, help='Initial command to run')
        parser.add_argument('--name', type=str, help='ISO name', default='Game')
        parser.add_argument('--version', type=str, help='ISO version', default='1.0')
        parser.add_argument('--resolution', type=str, help='Screen Resolution', default='800x600')
        args = parser.parse_args()
        return args
    
    def copyConfig(self, dst: str, replace: dict = {}):
        fileName = os.path.basename(dst)
        if not os.path.exists(os.path.join("configs/", fileName)):
            print(f"Config {fileName} not found")
            return
        original = open(os.path.join("configs/", fileName), 'r').read()
        for key, value in replace.items():
            original = original.replace(key, value)
        open(dst, 'w').write(original)
    
    def runCmd(self, cmd: str):
        subprocess.run(["chroot", "rootdir", "sh", "-c", "DEBIAN_FRONTEND=noninteractive " + cmd])
        if cmd.startswith("apt "):
            subprocess.run(["chroot", "rootdir", "sh", "-c", "apt clean"])

    def runLocalCmd(self, cmd: str):
        subprocess.run(["sh", "-c", cmd])

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
        self.runLocalCmd('umount rootdir/dev/pts')
        self.runLocalCmd('umount rootdir/dev')
        self.runLocalCmd('umount rootdir/proc')
        self.runLocalCmd('umount rootdir/sys')
        self.runLocalCmd('umount rootdir')
        self.runLocalCmd('e2fsck -f -y rootfs.img')
        self.runLocalCmd('resize2fs -M rootfs.img')
        # delete ubuntu
        self.runLocalCmd('rm -rf /tmp/ubuntu.tar.gz')
    
    def buildRootFS(self):
        self.runLocalCmd('dd if=/dev/zero of=rootfs.img bs=1M count=3584')
        self.runLocalCmd('mkfs.ext4 rootfs.img')
        self.runLocalCmd('mount -o loop rootfs.img rootdir')
        
        ### Setup Ubuntu
        if not os.path.exists("/tmp/ubuntu.tar.gz"):
            self.runLocalCmd('curl -o /tmp/ubuntu.tar.gz https://cdimage.ubuntu.com/ubuntu-base/releases/20.04/release/ubuntu-base-20.04.1-base-amd64.tar.gz')
        self.runLocalCmd('tar -xzf /tmp/ubuntu.tar.gz -C rootdir')
        self.runLocalCmd('mount --bind /dev rootdir/dev')
        self.runLocalCmd('mount --bind /dev/pts rootdir/dev/pts')
        self.runLocalCmd('mount --bind /proc rootdir/proc')
        self.runLocalCmd('mount --bind /sys rootdir/sys')
        self.runLocalCmd('cp /etc/resolv.conf rootdir/etc/resolv.conf')
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
        self.runCmd('echo "tmpfs /tmp tmpfs defaults,size=8m 0 0" >> /etc/fstab')
        self.runCmd('echo "tmpfs /var/log tmpfs defaults,size=8m 0 0" >> /etc/fstab')
        self.runCmd('cat /etc/fstab')

        ### Install Softwares
        self.runCmd('apt install -y xserver-xorg-core xserver-xorg-video-fbdev x11-xserver-utils xinit xinput --no-install-recommends --no-install-suggests')
        self.runCmd('apt install -y xserver-xorg-input-wacom xserver-xorg-input-mouse xserver-xorg-input-kbd xserver-xorg-input-libinput --no-install-recommends --no-install-suggests')
        self.runCmd('apt install -y pulseaudio ca-certificates eject --no-install-recommends --no-install-suggests')
        ### Setup Xinit
        self.copyConfig("rootdir/usr/local/bin/set-resolution.sh", replace={"{{RESOLUTION}}": self.screenResolution})
        self.runCmd('chmod +x /usr/local/bin/set-resolution.sh')
        self.runCmd('echo "/usr/local/bin/set-resolution.sh ' + self.screenResolution + '" >> /root/.xinitrc')
        self.runCmd('echo "cd /app && LANG=ja_JP.UTF-8 LC_ALL="ja_JP" /usr/lib/wine/wine ' + self.initCmd + '; /sbin/poweroff" >> /root/.xinitrc')
        self.runCmd('chmod +x /root/.xinitrc')

        ### Setup Service
        if not os.path.exists("rootdir/etc/systemd/system/getty@tty1.service.d/"):
            self.runLocalCmd('mkdir -p rootdir/etc/systemd/system/getty@tty1.service.d/')
        self.runCmd('echo "[Service]" >> /etc/systemd/system/getty@tty1.service.d/override.conf')
        self.runCmd('echo "ExecStart=" >> /etc/systemd/system/getty@tty1.service.d/override.conf')
        self.copyConfig("rootdir/etc/systemd/system/shutdown.service")
        self.copyConfig("rootdir/etc/systemd/system/xorg.service")
        self.runCmd('systemctl enable shutdown.service xorg.service')
        for service in self.getDisableServices():
            self.runCmd('systemctl disable ' + service)

        ### Install Wine
        self.runCmd('dpkg --add-architecture i386 && apt update')
        self.runCmd('apt install -y wine32 winetricks --no-install-recommends --no-install-suggests')
        self.runCmd('dpkg --remove-architecture i386')
        self.runCmd('/usr/lib/wine/wine cmd /c ver')
        self.runCmd('/usr/bin/winetricks fakejapanese_ipamona')

        ### Copy Files
        self.runLocalCmd('mkdir -p rootdir/app')
        self.runLocalCmd('cp -r ' + self.folder + '/* rootdir/app')

    def buildISO(self):
        self.runLocalCmd('mkdir -p isoroot/boot isoroot/isolinux')
        if not os.path.exists('syslinux-6.03.tar.gz'):
            self.runLocalCmd('curl -LO https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.tar.gz')
        self.runLocalCmd('tar -xzf syslinux-6.03.tar.gz')
        
        self.runLocalCmd('cp -a syslinux-6.03/bios/core/isolinux.bin isoroot/isolinux/isolinux.bin')
        self.runLocalCmd('cp syslinux-6.03/bios/com32/elflink/ldlinux/ldlinux.c32 isoroot/isolinux/ldlinux.c32')
        self.copyConfig('isoroot/isolinux/isolinux.cfg', {"{{CDLABEL}}": self.name})
        self.runCmd('apt install -y dracut xz-utils --no-install-recommends --no-install-suggests')
        self.runCmd('dracut --xz --force --add "dmsquash-live convertfs pollcdrom" --omit plymouth --no-hostonly --no-early-microcode /boot/initrd.img `ls /lib/modules`')
        self.runCmd('apt remove -y lvm2 xz-utils')
        self.runLocalCmd('cp rootdir/boot/initrd.img isoroot/boot/initrd.img')
        self.runLocalCmd('cp rootdir/boot/vmlinuz isoroot/boot/vmlinuz')
        self.runCmd('rm -rf /boot/initrd.img /boot/vmlinuz')
        self.cleanRootFS()
        self.runLocalCmd('mkdir -p squashfsroot/LiveOS')
        self.runLocalCmd('mv rootfs.img squashfsroot/LiveOS/rootfs.img')
        self.runLocalCmd('mksquashfs squashfsroot squashfs.img')
        self.runLocalCmd('mkdir -p isoroot/LiveOS')
        self.runLocalCmd('mv squashfs.img isoroot/LiveOS/squashfs.img')
        self.runLocalCmd(f'cd isoroot && mkisofs -o {self.output} -R -J -T -V {self.name} -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table .')

    def build(self):
        try:
            ### Setup ISO
            if os.path.exists('isoroot'):
                self.runLocalCmd('rm -rf isoroot')
            self.runLocalCmd('mkdir -p isoroot')
            if os.path.exists('rootdir'):
                self.runLocalCmd('rm -rf rootdir')
            self.runLocalCmd('mkdir -p rootdir')
            self.buildRootFS()
            self.buildISO()
        except:
            self.cleanRootFS()
            sys.exit(1)

if __name__ == '__main__':
    builder = LinuxWineIsoBuilder()
    builder.build()
