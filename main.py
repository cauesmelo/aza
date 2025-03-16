#!/usr/bin/env python
import sys
import argparse
import subprocess
import os

def update_user(resource_group, vm_name):
    ssh_key_pub = os.path.expanduser("~/.ssh/melocaue_bcg_az_key.pub")

    try:
        with open(ssh_key_pub, "r") as f:
            public_key = f.read().strip()
    except Exception as e:
        print(f"Error reading SSH public key from {ssh_key_pub}: {e}")
        sys.exit(1)
    
    command = [
        "az", "vm", "user", "update",
        "--resource-group", resource_group,
        "--name", vm_name,
        "--username", "melo.caue@bcg.com",
        "--ssh-key-value", public_key
    ]
    print("Running command:")
    print(" ".join(command))
    subprocess.run(command)

def ssh_into_vm(resource_group, vm_name):
    command = [
        "az", "ssh", "vm",
        "--resource-group", resource_group,
        "--name", vm_name,
        "--ssh-key-file", os.path.expanduser("~/.ssh/melocaue_bcg_az_key")
    ]
    print("Running command:")
    print(" ".join(command))
    subprocess.run(command)

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    setuser_parser = subparsers.add_parser("setuser")
    setuser_parser.add_argument("-rg", required=True)
    setuser_parser.add_argument("-vm", required=True)
    
    ssh_parser = subparsers.add_parser("ssh")
    ssh_parser.add_argument("-rg", required=True)
    ssh_parser.add_argument("-vm", required=True)
    
    args = parser.parse_args()
    
    if args.command == "setuser":
        update_user(args.resource_group, args.vm_name)
    elif args.command == "ssh":
        ssh_into_vm(args.resource_group, args.vm_name)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
