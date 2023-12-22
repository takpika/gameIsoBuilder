import argparse

class ArgumentParser:
    @staticmethod
    def parseArgs() -> argparse.Namespace:
        parser = argparse.ArgumentParser(description='Linux GUI ISO Builder')
        parser.add_argument('output', type=str, help='Output ISO file')
        parser.add_argument('-f', '--folder', type=str, help='Folder to include in ISO')
        parser.add_argument('-c', '--initCmd', type=str, help='Initial command to run')
        parser.add_argument('-n', '--name', type=str, help='ISO name', default='Game')
        parser.add_argument('--version', type=str, help='ISO version', default='1.0')
        parser.add_argument('-r', '--resolution', type=str, help='Screen Resolution', default='800x600')
        parser.add_argument('-o', '--os', type=str, help='OS', default='linux', choices=['linux', 'windows'])
        args = parser.parse_args()
        return args