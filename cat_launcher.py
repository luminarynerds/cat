"""Launcher for Collection Analyzer Tool — opens browser automatically."""

import os
import socket
import sys
import threading
import webbrowser


def get_base_path():
    """Get the base path for bundled resources (PyInstaller or normal)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port(start=5000, end=5050):
    """Find an available port starting from the preferred one."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def open_browser(port):
    """Open the default browser after a short delay."""
    import time
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    # Set working directory so Flask can find templates/static/data
    base = get_base_path()
    os.chdir(base)

    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)

    port = find_free_port()

    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   Library Collection Analyzer Tool        ║")
    print("  ║                                           ║")
    print("  ║   Opening in your browser...              ║")
    print("  ║   If it doesn't open, go to:              ║")
    print(f"  ║   http://127.0.0.1:{port:<21s}  ║")
    print("  ║                                           ║")
    print("  ║   Press Ctrl+C to quit                    ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    # Open browser in background thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Import and run Flask app
    from app import app
    app.run(debug=False, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
