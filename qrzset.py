#!/usr/bin/python3

# python3 qrzset.py "{query}"
# Saves QRZ username and password to the macOS Keychain.
# Expected input: "USERNAME PASSWORD"

import sys
from workflow import Workflow

log = None


def main(wf):
    if not wf.args or not wf.args[0].strip():
        print("Usage: qrzset USERNAME PASSWORD", file=sys.stderr)
        return 1

    parts = wf.args[0].strip().split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        print("Please provide both username and password: qrzset USERNAME PASSWORD",
              file=sys.stderr)
        return 1

    username = parts[0].upper()
    password = parts[1]

    wf.save_password('qrz_username', username)
    wf.save_password('qrz_password', password)

    print(f"QRZ credentials saved for {username}")
    return 0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
