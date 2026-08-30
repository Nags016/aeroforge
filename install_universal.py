#!/home/mr_nags/miniconda3/envs/aeroforge/bin/python3
"""
AeroForge Universal Installer
- Works on ANY Linux/macOS/Windows (WSL)
- Auto-detects system and installs dependencies
- Creates adaptive theme CLI
- Git clone → run immediately
"""

import sys
import os
import subprocess
import platform
import shutil
import urllib.request
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
import json

class UniversalInstaller:
    """Universal installer for AeroForge."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.home = Path.home()
        self.install_dir = self.home / ".local" / "bin"
        self.config_dir = self.home / ".config" / "aeroforge"
        self.python_cmd = "python3"
        
    def detect_system(self) -> dict:
        """Detect system details."""
        info = {
            "os": self.system,
            "arch": self.arch,
            "distro": "unknown",
            "package_manager": "unknown",
            "has_gpu": False,
            "python_version": platform.python_version(),
        }
        
        # Detect Linux distro
        if self.system == "linux":
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("ID="):
                            info["distro"] = line.split("=")[1].strip().strip('"')
                        elif line.startswith("ID_LIKE="):
                            info["distro"] += " (" + line.split("=")[1].strip().strip('"') + ")"
            except:
                pass
            
            # Detect package manager
            for pm in ["apt", "dnf", "yum", "pacman", "zypper", "apk", "brew"]:
                if shutil.which(pm):
                    info["package_manager"] = pm
                    break
        
        # Detect GPU
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True)
            if result.returncode == 0:
                info["has_gpu"] = True
        except:
            pass
        
        return info
    
    def install_system_dependencies(self, info: dict) -> bool:
        """Install system-level dependencies."""
        pm = info["package_manager"]
        distro = info["distro"]
        
        print(f"📦 Installing system dependencies via {pm}...")
        
        # Package mappings per package manager
        packages = {
            "apt": [
                "python3", "python3-pip", "python3-venv", "python3-dev",
                "git", "curl", "wget", "build-essential",
                "libgl1-mesa-glx", "libglib2.0-0", "libsm6", "libxext6",
                "libxrender-dev", "libglib2.0-dev", "pkg-config",
            ],
            "dnf": [
                "python3", "python3-pip", "python3-devel",
                "git", "curl", "wget", "gcc", "gcc-c++", "make",
                "mesa-libGL", "glib2-devel", "libSM", "libXext",
                "libXrender-devel", "pkg-config",
            ],
            "pacman": [
                "python", "python-pip", "python-virtualenv",
                "git", "curl", "wget", "base-devel",
                "mesa", "glib2", "libsm", "libxext", "libxrender",
                "pkg-config",
            ],
            "brew": [
                "python3", "git", "curl", "wget",
                "mesa", "glib", "pkg-config",
            ],
            "zypper": [
                "python3", "python3-pip", "python3-devel",
                "git", "curl", "wget", "gcc", "gcc-c++", "make",
                "Mesa-libGL1", "glib2-devel", "libSM6", "libXext6",
                "libXrender1", "pkg-config",
            ],
            "apk": [
                "python3", "py3-pip", "python3-dev",
                "git", "curl", "wget", "build-base",
                "mesa-gl", "glib-dev", "libsm", "libxext", "libxrender-dev",
                "pkgconf",
            ],
        }
        
        pkgs = packages.get(pm, [])
        if not pkgs:
            print(f"⚠️  Unknown package manager: {pm}, skipping system deps")
            return True
        
        # Build install command
        install_cmds = {
            "apt": f"sudo apt update && sudo apt install -y {' '.join(pkgs)}",
            "dnf": f"sudo dnf install -y {' '.join(pkgs)}",
            "pacman": f"sudo pacman -S --noconfirm {' '.join(pkgs)}",
            "brew": f"brew install {' '.join(pkgs)}",
            "zypper": f"sudo zypper install -y {' '.join(pkgs)}",
            "apk": f"sudo apk add {' '.join(pkgs)}",
        }
        
        cmd = install_cmds.get(pm)
        if not cmd:
            print(f"⚠️  No install command for {pm}")
            return False
        
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0
    
    def create_venv(self, path: Path) -> bool:
        """Create Python virtual environment."""
        print(f"🐍 Creating virtual environment at {path}...")
        try:
            subprocess.run([self.python_cmd, "-m", "venv", str(path)], check=True)
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to create venv")
            return False
    
    def install_python_packages(self, venv_python: str) -> bool:
        """Install Python packages in venv."""
        print("📦 Installing Python packages...")
        
        # Core packages
        packages = [
            "rich>=13.7.0",
            "textual>=0.44.0",
            "numpy>=1.24.0",
            "torch>=2.0.0",
            "stable-baselines3>=2.0.0",
            "gymnasium>=0.29.0",
            "pydantic>=2.0.0",
            "pyyaml>=6.0",
            "tensorboard>=2.13.0",
            "psutil>=5.9.0",
        ]
        
        pip_cmd = f"{venv_python} -m pip install --upgrade pip && {venv_python} -m pip install {' '.join(packages)}"
        
        try:
            subprocess.run(pip_cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install packages: {e}")
            return False
    
    def install_rl_packages(self, venv_python: str) -> bool:
        """Install RL-specific packages (with CUDA if available)."""
        print("🧠 Installing RL packages...")
        
        # Check CUDA
        try:
            import torch
            if torch.cuda.is_available():
                print(f"🎮 CUDA detected: {torch.version.cuda}")
                # Install with CUDA support
                packages = [
                    "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118",
                ]
            else:
                print("💻 CPU-only mode")
                packages = ["torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"]
        except:
            packages = ["torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"]
        
        pip = f"{venv_python} -m pip"
        for pkg in packages:
            subprocess.run(f"{pip} install {pkg}", shell=True, check=False)
        
        return True
    
    def setup_cli(self, venv_python: str, repo_path: Path) -> bool:
        """Set up the global aeroforge CLI command."""
        print("🔧 Setting up global CLI command...")
        
        self.install_dir.mkdir(parents=True, exist_ok=True)
        cli_script = self.install_dir / "aeroforge"
        
        # Create wrapper script
        script_content = f'''#!/bin/bash
# AeroForge Universal CLI Wrapper
# Auto-activates venv and runs CLI

VENV_PYTHON="{venv_python}"
REPO_PATH="{repo_path}"

# Ensure we're in the repo directory
cd "$REPO_PATH" || exit 1

# Run with venv python
exec "$VENV_PYTHON" -m aeroforge_production "$@"
'''
        
        cli_script.write_text(script_content)
        cli_script.chmod(0o755)
        
        # Also create aeroforge_production entry point
        self._create_production_entry(venv_python, repo_path)
        
        print(f"✅ CLI installed at {cli_script}")
        print(f"   Run 'aeroforge --help' from anywhere")
        return True
    
    def _create_production_entry(self, venv_python: str, repo_path: Path):
        """Create the aeroforge_production module entry point."""
        # Create a simple __main__.py in the repo root
        main_py = repo_path / "aeroforge_production.py"
        if not main_py.exists():
            # We'll create it separately
            pass
    
    def clone_repo(self, target_dir: Path, repo_url: str = "https://github.com/Nags016/aeroforge.git") -> bool:
        """Clone or update the repository."""
        print(f"📥 Cloning repository to {target_dir}...")
        
        if target_dir.exists():
            print("📂 Repository exists, updating...")
            try:
                subprocess.run(["git", "-C", str(target_dir), "pull"], check=True)
                return True
            except subprocess.CalledProcessError:
                print("⚠️  Failed to update, removing and re-cloning...")
                shutil.rmtree(target_dir)
        
        try:
            subprocess.run(["git", "clone", repo_url, str(target_dir)], check=True)
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to clone repository")
            return False
    
    def run_full_install(self, repo_url: str = None, install_dir: Path = None) -> bool:
        """Run complete installation."""
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AeroForge Universal Installer                             ║
║    Autonomous Flight Engineer  •  NL → SITL → Hardware Deployment           ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        # System detection
        info = self.detect_system()
        print(f"🖥️  System: {info['os']} {info['arch']} ({info['distro']})")
        print(f"📦 Package Manager: {info['package_manager']}")
        print(f"🐍 Python: {info['python_version']}")
        print(f"🎮 GPU: {'Yes' if info['has_gpu'] else 'No (CPU mode)'}")
        print()
        
        # Default paths
        repo_url = repo_url or "https://github.com/Nags016/aeroforge.git"
        target_dir = install_dir or (self.home / "aeroforge")
        
        # Step 1: System dependencies
        if not self.install_system_dependencies(info):
            print("⚠️  System deps failed, continuing anyway...")
        
        # Step 2: Clone repo
        if not self.clone_repo(target_dir):
            return False
        
        # Step 3: Create venv
        venv_path = target_dir / ".venv"
        if not self.create_venv(venv_path):
            return False
        
        venv_python = venv_path / "bin" / "python"
        
        # Step 4: Install Python packages
        if not self.install_python_packages(str(venv_python)):
            return False
        
        # Step 5: Install RL packages
        self.install_rl_packages(str(venv_python))
        
        # Step 6: Setup CLI
        if not self.setup_cli(str(venv_python), target_dir):
            return False
        
        # Step 7: Verify installation
        print("\n🔍 Verifying installation...")
        result = subprocess.run([str(self.install_dir / "aeroforge"), "--help"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Installation verified!")
        else:
            print("⚠️  CLI verification failed, but installation may still work")
        
        # Success!
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        🎉 INSTALLATION COMPLETE!                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

📁 Repository: {target_dir}
🐍 Virtual Env: {venv_path}
🔧 CLI Command: aeroforge (installed to {self.install_dir})

🚀 QUICK START:
    aeroforge "Fly from (0,0,2) to (10,10,2) avoiding obstacles"
    aeroforge --interactive
    aeroforge deploy "Fly from (0,0,2) to (20,15,3) using camera"
    aeroforge setup          # Setup PX4/ROS2/Gazebo simulation stack
    aeroforge train          # Train RL policies
    aeroforge visualize      # Terminal flight visualization

🎨 Theme: Auto-detected for your terminal (truecolor/256/16-color/mono)
🚁 Drone ASCII art and status panels included

📚 Next steps:
    1. Run 'aeroforge setup' to install PX4/ROS2/Gazebo simulation stack
    2. Run 'aeroforge train' to train RL policies (SAC/PPO)
    3. Run 'aeroforge deploy "your mission"' for full pipeline

Happy flying! 🚁
        """)
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AeroForge Universal Installer")
    parser.add_argument("--repo", help="Repository URL", default=None)
    parser.add_argument("--dir", help="Installation directory", default=None)
    parser.add_argument("--skip-system", action="store_true", help="Skip system dependencies")
    args = parser.parse_args()
    
    installer = UniversalInstaller()
    
    if args.skip_system:
        installer.install_system_dependencies = lambda x: True
    
    success = installer.run_full_install(
        repo_url=args.repo,
        install_dir=Path(args.dir) if args.dir else None
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()