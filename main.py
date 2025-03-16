#!/Users/melocaue/devpy/aza/.venv/bin/python
import sys
import argparse
import subprocess
import os
import json
from rich.table import Table
from rich.console import Console

console = Console()


def patched_run(*args, **kwargs):
    if args and isinstance(args[0], list):
        cmd = args[0]
        console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]")
    return _original_run(*args, **kwargs)


_original_run = subprocess.run
subprocess.run = patched_run


def clear():
    clear_command = "cls" if os.name == "nt" else "clear"
    os.system(clear_command)


def set_user(resource_group, vm_name):
    if resource_group is None or vm_name is None:
        resource_group, vm_name = select_vm()

    ssh_key_pub = os.path.expanduser("~/.ssh/melocaue_bcg_az_key.pub")

    try:
        with open(ssh_key_pub, "r") as f:
            public_key = f.read().strip()
    except Exception as e:
        print(f"Error reading SSH public key from {ssh_key_pub}: {e}")
        sys.exit(1)

    command = [
        "az",
        "vm",
        "user",
        "update",
        "--resource-group",
        resource_group,
        "--name",
        vm_name,
        "--username",
        "melo.caue@bcg.com",
        "--ssh-key-value",
        public_key,
    ]
    print(
        f"Setting user melo.caue@bcg.com and SSH key for VM {vm_name} in RG {resource_group}"
    )
    subprocess.run(command, check=True)
    print("User and SSH key updated successfully.")


def list_vms():
    list_command = ["az", "vm", "list", "-o", "json"]
    print("Loading VMs, please wait...")
    result = subprocess.run(list_command, capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed to list VMs. Check your Azure CLI login/status.")
        sys.exit(1)

    try:
        vms = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Failed to parse JSON output from `az vm list`.")
        sys.exit(1)

    if not vms:
        print("No VMs found in your subscription.")
        sys.exit(0)

    return vms


def select_vm():
    vms = list_vms()

    clear()

    table = Table(title="[bold green]Available VMs[/bold green]", show_lines=True)
    table.add_column("Index", justify="right", style="cyan", no_wrap=True)
    table.add_column("VM Name", style="magenta")
    table.add_column("Resource Group", style="green")

    for i, vm in enumerate(vms, start=0):
        vm_name = vm.get("name", "UnknownName")
        vm_rg = vm.get("resourceGroup", "UnknownRG")
        table.add_row(str(i), vm_name, vm_rg)

    console.print(table)

    try:
        selected_index = int(input("VM Index to ssh: ").strip())
        if selected_index < 0 or selected_index >= len(vms):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        sys.exit(1)

    clear()
    selected_vm = vms[selected_index]
    selected_rg = selected_vm["resourceGroup"]
    selected_name = selected_vm["name"]
    print(f"\nSelected VM: {selected_name} (RG: {selected_rg})")
    return selected_rg, selected_name


def ssh_into_vm(resource_group, vm_name):
    if resource_group is None or vm_name is None:
        resource_group, vm_name = select_vm()

    command = [
        "az",
        "ssh",
        "vm",
        "--resource-group",
        resource_group,
        "--name",
        vm_name,
        "--private-key-file",
        os.path.expanduser("~/.ssh/melocaue_bcg_az_key"),
        "--",
        "-o PasswordAuthentication=no",
        "-o BatchMode=yes",
    ]
    print("SSHing into VM...")
    subprocess.run(
        command,
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    setuser_parser = subparsers.add_parser("setuser")
    setuser_parser.add_argument("-rg", dest="resource_group")
    setuser_parser.add_argument("-vm", dest="vm_name")

    ssh_parser = subparsers.add_parser("ssh")
    ssh_parser.add_argument("-rg", dest="resource_group")
    ssh_parser.add_argument("-vm", dest="vm_name")

    args = parser.parse_args()

    if args.command == "setuser":
        set_user(args.resource_group, args.vm_name)
    elif args.command == "ssh":
        ssh_into_vm(args.resource_group, args.vm_name)
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
