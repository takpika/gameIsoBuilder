from src.logic.argument import ArgumentParser
from src.builder.linux.builder import LinuxBuilder
from src.builder.windows.builder import WindowsBuilder

if __name__ == '__main__':
    args = ArgumentParser.parseArgs()
    if args.os == 'linux':
        builder = LinuxBuilder(args.output, args.folder, args.initCmd, args.name, args.version, args.resolution, args.debug)
    else:
        builder = WindowsBuilder(args.output, args.folder, args.initCmd, args.name, args.version, args.resolution, args.debug)
    builder.build()
