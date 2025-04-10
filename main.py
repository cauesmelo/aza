import sys
import argparse
import subprocess
import os
import json
from rich.table import Table
from rich.console import Console
import configparser

console = Console()
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.cfg"))

SSH_KEY_PATH = config.get("SSH Key Settings", "SSH_KEY_PATH")
SSH_KEY_PUB_PATH = config.get("SSH Key Settings", "SSH_KEY_PUB_PATH")
AZ_USER = config.get("User Settings", "AZ_USER")


def exec_wait(message, *args, **kwargs):
    with console.status(f"[bold green]{message}, please wait...[/bold green]"):
        return subprocess.run(*args, **kwargs)


def clear():
    clear_command = "cls" if os.name == "nt" else "clear"
    os.system(clear_command)


def generate_key():
    key_path = os.path.expanduser(SSH_KEY_PATH)
    if os.path.exists(key_path):
        console.print(f"SSH key already exists at {key_path}.", style="yellow")
        return

    cmd = ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", key_path, "-N", ""]
    result = exec_wait("Generating SSH key", cmd, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"Error generating SSH key: {result.stderr}", style="red")
        sys.exit(1)

    chmod_result = exec_wait(
        "Setting permissions on private SSH key",
        ["chmod", "600", key_path],
        capture_output=True,
        text=True,
    )
    if chmod_result.returncode != 0:
        console.print(
            f"Error setting permissions on SSH key: {chmod_result.stderr}", style="red"
        )
        sys.exit(1)

    pub_key_path = os.path.expanduser(SSH_KEY_PUB_PATH)
    chmod_pub_result = exec_wait(
        "Setting permissions on public SSH key",
        ["chmod", "600", pub_key_path],
        capture_output=True,
        text=True,
    )
    if chmod_pub_result.returncode != 0:
        console.print(
            f"Error setting permissions on SSH public key: {chmod_pub_result.stderr}",
            style="red",
        )
        sys.exit(1)

    console.print("SSH key generated and permissions set successfully.", style="green")


def set_user(resource_group, vm_name):
    if resource_group is None or vm_name is None:
        resource_group, vm_name = select_vm()

    ssh_key_pub = os.path.expanduser(SSH_KEY_PUB_PATH)

    try:
        with open(ssh_key_pub, "r") as f:
            public_key = f.read().strip()
    except Exception as e:
        console.print(
            f"Error reading SSH public key from {ssh_key_pub}: {e}", style="red"
        )
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
        AZ_USER,
        "--ssh-key-value",
        public_key,
    ]
    exec_wait(
        f"Setting user {AZ_USER} and SSH key for VM {vm_name} in RG {resource_group}",
        command,
        check=True,
    )
    console.print("User and SSH key updated successfully.", style="green")


def list_subscriptions():
    list_command = ["az", "account", "list", "-o", "json"]

    result = exec_wait(
        "Listing subscriptions", list_command, capture_output=True, text=True
    )

    if result.returncode != 0:
        console.print(
            "Failed to list subscriptions. Check your Azure CLI login/status.",
            style="red",
        )
        sys.exit(1)
    try:
        subscriptions = json.loads(result.stdout)
    except json.JSONDecodeError:
        console.print("Failed to parse subscriptions JSON.", style="red")
        sys.exit(1)
    if not subscriptions:
        console.print("No subscriptions found in your account.", style="red")
        sys.exit(0)

    return subscriptions


def list_vms():
    list_command = ["az", "vm", "list", "-o", "json"]
    result = exec_wait("Listing VMs", list_command, capture_output=True, text=True)

    if result.returncode != 0:
        console.print(
            "Failed to list VMs. Check your Azure CLI login/status.", style="red"
        )
        sys.exit(1)

    try:
        vms = json.loads(result.stdout)
    except json.JSONDecodeError:
        console.print("Failed to parse JSON output from `az vm list`.", style="red")
        sys.exit(1)

    if not vms:
        console.print("No VMs found in your subscription.", style="red")
        sys.exit(0)

    return vms


def select_subscription():
    subscriptions = list_subscriptions()
    clear()

    table = Table(
        title="[bold green]Available Subscriptions[/bold green]",
        show_lines=True,
    )
    table.add_column("Index", justify="right", style="cyan")
    table.add_column("Subscription Name", style="magenta")
    table.add_column("Subscription ID", style="green")

    for i, sub in enumerate(subscriptions):
        sub_name = sub.get("name", "Unknown")
        sub_id = sub.get("id", "Unknown")
        table.add_row(str(i), sub_name, sub_id)

    console.print(table)

    try:
        console.print("[dim]Press Ctrl+C to cancel[/dim]\n")
        idx = int(input("Select subscription index: ").strip())
        if idx < 0 or idx >= len(subscriptions):
            raise ValueError
    except ValueError:
        console.print("Invalid selection.", style="red")
        sys.exit(1)

    clear()
    console.print(
        f"[blue]Selected subscription:[/blue] {subscriptions[idx].get('name')} ({subscriptions[idx].get('id')})"
    )
    return subscriptions[idx]


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
        console.print("[dim]Press Ctrl+C to cancel[/dim]\n")
        selected_index = int(input("VM Index to ssh: ").strip())
        if selected_index < 0 or selected_index >= len(vms):
            raise ValueError
    except ValueError:
        console.print("Invalid selection.", style="yellow")
        sys.exit(1)

    clear()
    selected_vm = vms[selected_index]
    selected_rg = selected_vm["resourceGroup"]
    selected_name = selected_vm["name"]
    console.print(f"\n[blue]Selected VM:[/blue] {selected_name} (RG: {selected_rg})")
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
        os.path.expanduser(SSH_KEY_PATH),
        "--local-user",
        AZ_USER,
        "--",
        "-o PasswordAuthentication=no",
        "-o BatchMode=yes",
        "-o StrictHostKeyChecking=no",
    ]

    console.print(f"[blue]Executing:[/blue] {' '.join(command)}")
    subprocess.run(
        command,
        check=True,
    )


def set_subscription():
    selected_sub = select_subscription()
    selected_id = selected_sub.get("id")
    command = ["az", "account", "set", "--subscription", selected_id]
    result = exec_wait(
        f"Setting subscription to: {selected_sub.get('name')} ({selected_id})",
        command,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"Failed to set subscription: {result.stderr}", style="red")
        sys.exit(1)
    console.print("Subscription set successfully.", style="green")


def copy_file(path):
    resource_group, vm_name = select_vm()

    cmd = [
        "az",
        "vm",
        "list-ip-addresses",
        "--name",
        vm_name,
        "--resource-group",
        resource_group,
        "-o",
        "json",
    ]
    result = exec_wait("Fetching VM IP address", cmd, capture_output=True, text=True)
    if result.returncode != 0:
        console.print("Failed to fetch VM IP address.", style="red")
        sys.exit(1)

    try:
        ip_info = json.loads(result.stdout)
        ip_address = ip_info[0]["virtualMachine"]["network"]["publicIpAddresses"][0][
            "ipAddress"
        ]
    except (IndexError, KeyError, json.JSONDecodeError):
        console.print("Could not parse VM IP address.", style="red")
        sys.exit(1)

    clear()

    destination = os.path.expanduser("~/Downloads/")
    scp_cmd = [
        "scp",
        "-i",
        os.path.expanduser(SSH_KEY_PATH),
        "-r",
        f"{AZ_USER}@{ip_address}:{path}",
        destination,
    ]
    console.print(f"[bold green]Copying '{path}', please wait...[/bold green]")
    subprocess.run(scp_cmd, check=True)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    setuser_parser = subparsers.add_parser("setuser")
    setuser_parser.add_argument("-rg", dest="resource_group")
    setuser_parser.add_argument("-vm", dest="vm_name")

    ssh_parser = subparsers.add_parser("ssh")
    ssh_parser.add_argument("-rg", dest="resource_group")
    ssh_parser.add_argument("-vm", dest="vm_name")

    scp_parser = subparsers.add_parser("cp")
    scp_parser.add_argument("path")

    subparsers.add_parser("genkey")
    subparsers.add_parser("setsub")

    subparsers.add_parser("help")

    args = parser.parse_args()

    if args.command == "setuser":
        set_user(args.resource_group, args.vm_name)
    elif args.command == "ssh":
        ssh_into_vm(args.resource_group, args.vm_name)
    elif args.command == "genkey":
        generate_key()
    elif args.command == "setsub":
        set_subscription()
    elif args.command == "cp":
        copy_file(args.path)
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\nCancelled.", style="red")
