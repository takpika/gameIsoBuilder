# gameIsoBuilder README.md

## Overview
`gameIsoBuilder` is a powerful tool designed to create ISO images that enable the running of Windows software and games on various systems. This utility simplifies the process of packaging Windows-compatible environments into an ISO file, making it easier to deploy and run Windows applications on non-Windows systems.

## Features
- **ISO Creation**: Generate ISO images that can host Windows software and games.
- **Customization**: Include specific folders and execute custom commands upon startup.
- **Compatibility**: Supports both Linux and Windows as target operating systems.

## Prerequisites
Before using `gameIsoBuilder`, ensure that the following software is installed on your system:

- Python 3
- QEMU (with x86 support)
- SquashFS tools
- xorriso
- GRUB EFI for AMD64

To install these on a Debian-based system, you can use the following command:
```bash
sudo apt install python3 qemu-system-x86 squashfs-tools xorriso grub-efi-amd64-bin
```

## Installation
Clone the repository to your local machine using:
```bash
git clone https://github.com/your-username/gameIsoBuilder.git
```

## Usage
To create an ISO, run the following command:
```bash
sudo python main.py <iso_file_name> -f <folder_to_include_in_iso> -c <startup_command> -o <os_type>
```

- `<iso_file_name>`: Name of the ISO file to be created.
- `-f <folder_to_include_in_iso>`: Specify the folder to include in the ISO.
- `-c <startup_command>`: Command to execute on startup (Windows commands supported).
- `-o <os_type>`: The type of operating system; choose either `linux` or `windows`.

## Example
```bash
sudo python main.py windows-games.iso -f /path/to/games -c "start game.exe" -o windows
```

This command creates an ISO named `windows-games.iso`, including the contents of `/path/to/games`. Upon launching the ISO, it executes the command `start game.exe` in a Windows environment.

## Contribution
Contributions to `gameIsoBuilder` are welcome. Please ensure to follow the contribution guidelines stated in the repository.

## License
This project is licensed under takpika. Please refer to the `LICENSE` file for more details.

---

**Note**: `gameIsoBuilder` is a tool intended for legal and ethical usage only. Users are responsible for adhering to software licensing agreements and copyright laws.