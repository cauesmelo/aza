# aza

**AZ**ure **A**lias is a Python-based command line tool for managing Azure virtual machines with ease. It automates SSH key generation, user setup, and subscription configuration using Azure CLI integrations.

## Installation

1. You need Azure CLI installed and configured on your machine. Follow the instructions [here](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) to install it.

2. Clone the repository and navigate to the directory

```bash
git clone git@github.com:cauesmelo/aza.git && cd aza
```

3. Sync using uv

```bash
uv sync
```

4. Add the executable to your shell configuration

```bash
echo "alias aza=\"$(pwd)/bin\"" >> ~/.zshrc  # or ~/.bashrc
```

### Configuring

Edit the `config.cfg` if for changing the user that will be set on the VMs or the key location.

## Usage

Aza supports the following commands:

- **genkey:**  
  Generates an SSH key to be used for setting users and sshing into VMs.

  ```bash
  aza genkey
  ```

- **setuser:**  
  Updates or create the user on a VM with the key specified on main.py

  ```bash
  aza setuser
  ```

- **ssh:**  
  List VMs and SSH into the selected VM.

  ```bash
  aza ssh
  ```

- **setsub:**  
  List azure subscriptions for selection and set the active subscription.

  ```bash
  aza setsub
  ```

- **cp:**  
  Copy content from an Azure VM to you `~Downloads` folder
  ```bash
  aza cp /path/in/vm/
  ```
