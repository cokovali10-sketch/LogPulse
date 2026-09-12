"""Build LogPulse EXE with PyInstaller."""
import subprocess, sys, os, shutil

def build():
    print("Building LogPulse EXE...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--name", "logpulse",
        "--hidden-import", "logpulse.cli",
        "--hidden-import", "logpulse.analyzer",
        "--hidden-import", "logpulse.parser",
        "--console",
        "logpulse/cli.py"
    ]
    subprocess.run(cmd, check=True)
    os.makedirs("dist", exist_ok=True)
    if os.path.exists("dist/logpulse.exe"):
        size = os.path.getsize("dist/logpulse.exe") // (1024*1024)
        print(f"OK: dist/logpulse.exe ({size} MB)")
    else:
        print("FAILED")

if __name__ == "__main__":
    build()
