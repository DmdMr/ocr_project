import subprocess
import platform
import psutil

def run_command(cmd):
    """Run shell command and return output"""
    try:
        return subprocess.check_output(cmd, shell=True).decode().strip()
    except:
        return "Unknown"

def get_mac_model():
    return run_command("system_profiler SPHardwareDataType | grep 'Model Name' | awk -F': ' '{print $2}'")

def get_chip():
    return run_command("system_profiler SPHardwareDataType | grep 'Chip' | awk -F': ' '{print $2}'")

def get_ram():
    return run_command("system_profiler SPHardwareDataType | grep 'Memory' | awk -F': ' '{print $2}'")

def get_serial():
    return run_command("system_profiler SPHardwareDataType | grep 'Serial Number' | awk -F': ' '{print $2}'")

def get_storage():
    disk = psutil.disk_usage('/')
    return f"{disk.total // (1024**3)} GB total, {disk.free // (1024**3)} GB free"

def get_cpu():
    return platform.processor()

def main():
    print("=== Laptop Specs ===")
    print(f"Model: {get_mac_model()}")
    print(f"Chip: {get_chip()}")
    print(f"CPU: {get_cpu()}")
    print(f"RAM: {get_ram()}")
    print(f"Storage: {get_storage()}")
    print(f"Serial: {get_serial()}")
    print(f"macOS Version: {platform.mac_ver()[0]}")

if __name__ == "__main__":
    main()
