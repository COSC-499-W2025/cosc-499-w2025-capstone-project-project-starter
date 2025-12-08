import os
import platform
import subprocess
import sys
from shutil import which

INSTALL_SCRIPT = "https://ollama.com/install.sh"

def run(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def is_installed():
    return which("ollama") is not None

def install_mac_linux():
    print("Detected macOS/Linux. Installing Ollama...")
    run(f"curl -fsSL {INSTALL_SCRIPT} | sh")

def install_windows():
    print("Detected Windows/WSL environment.")
    print("Downloading Ollama MSI installer...")

    url = "https://ollama.com/download/OllamaSetup.exe"
    output = "OllamaSetup.exe"

    run(f"curl -L {url} -o {output}")
    print(f"Running MSI installer: {output}")
    run(output)

def pull_default_model(model="llama3.1"):
    print(f"Pulling model: {model}")
    run(f"ollama pull {model}")

def main():
    system = platform.system().lower()

    if is_installed():
        print("Ollama is already installed.")
    else:
        if system == "darwin":
            install_mac_linux()
        elif system == "linux":
            install_mac_linux()
        elif system == "windows":
            install_windows()
        else:
            print(f"Unsupported system: {system}")
            sys.exit(1)

    print("Starting Ollama server...")
    try:
        run("ollama serve &")
    except Exception:
        print("Failed to start Ollama server automatically.")
        print("Try running manually: ollama serve")

    # Pull a model automatically
    pull_default_model()

    print("\nOllama setup complete!")

if __name__ == "__main__":
    main()
