"""Build script for creating a standalone Collection Analyzer executable."""

import subprocess
import sys


def main():
    # Check PyInstaller is installed
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} found.")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CollectionAnalyzer",
        "--onedir",
        "--noconfirm",
        "--clean",
        # Add all data files Flask needs
        "--add-data", "templates:templates",
        "--add-data", "static:static",
        "--add-data", "data:data",
        "--add-data", "sample_data:sample_data",
        # Hidden imports that PyInstaller might miss
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "flask",
        "--hidden-import", "jinja2",
        "--hidden-import", "jinja2.ext",
        # Collect all pandas/openpyxl submodules
        "--collect-submodules", "pandas",
        "--collect-submodules", "openpyxl",
        # Entry point
        "cat_launcher.py",
    ]

    print()
    print("Building Collection Analyzer...")
    print(f"Command: {' '.join(cmd)}")
    print()

    subprocess.check_call(cmd)

    print()
    print("=" * 50)
    print("Build complete!")
    print()
    print("Your app is in: dist/CollectionAnalyzer/")
    print("Run it with:    dist/CollectionAnalyzer/CollectionAnalyzer")
    print()
    print("To distribute:")
    print("  1. Zip the dist/CollectionAnalyzer/ folder")
    print("  2. Share the zip file")
    print("  3. Recipients unzip and double-click CollectionAnalyzer")
    print("=" * 50)


if __name__ == "__main__":
    main()
