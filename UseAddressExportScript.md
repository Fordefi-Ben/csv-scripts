# Fordefi Vault Address Exporter

A Python script to export all vault addresses from your Fordefi organization(s) to a CSV file.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Generate Fordefi API Keys](#generate-fordefi-api-keys)
3. [Setup Python Environment](#setup-python-environment)
4. [Configure the Script](#configure-the-script)
5. [Run the Script](#run-the-script)
6. [Understanding the Output](#understanding-the-output)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, make sure you have:
- Access to a Fordefi organization with appropriate permissions
- Python 3.7 or higher installed on your computer
- Administrator or appropriate role to create API users in Fordefi

**To check your Python version:**
```bash
python --version
# or
python3 --version
```

If Python is not installed, download it from [python.org](https://www.python.org/downloads/)

---

## Generate Fordefi API Keys

### Step 1: Log into Fordefi
1. Go to [app.fordefi.com](https://app.fordefi.com) 
2. Sign in with your credentials

### Step 2: Navigate to API Users
1. Click on **User Management**  in the left sidebar
2. Select **API Users** from the settings menu

### Step 3: Create a New API User
1. Full steps [here](https://docs.fordefi.com/developers/getting-started/create-an-api-user)

### Step 4: Generate and Save the API Key
1. After creating the API user, you'll see a modal with the API credentials
2. **IMPORTANT**: Copy the **Bearer Token** immediately
   - This token will only be shown once
   - It's a long string starting with something like `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
3. Save this token securely (you'll need it in Step 4)

### Step 5: Repeat for Multiple Organizations (Optional)
If you have multiple Fordefi organizations:
1. Switch to each organization
2. Repeat Steps 2-4 to create an API user in each
3. Save each Bearer Token separately

---

## Setup Python Environment

### Step 1: Create a Project Folder
```bash
mkdir fordefi-vault-export
cd fordefi-vault-export
```

### Step 2: Download the Script
1. Save the Python script as `export_vaults.py` in your project folder

### Step 3: Install Required Package
The script requires the `requests` library:

```bash
pip install requests
# or
pip3 install requests
```

**Verify installation:**
```bash
pip show requests
```

---

## Configure the Script

### Step 1: Open the Script
Open `export_vaults.py` in your favorite text editor (VS Code, Sublime Text, Notepad++, etc.)

### Step 2: Add Your API Keys
Find the `API_KEYS` configuration at the top of the file (around line 11):

```python
API_KEYS = [
    "PASTE_YOUR_FIRST_API_KEY_HERE",
    "PASTE_YOUR_SECOND_API_KEY_HERE",
    # Add more API keys as needed
]
```

Replace the placeholder text with your actual Bearer Tokens:

```python
API_KEYS = [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkw...",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODc2NTQzMjEw...",
]
```

**Tips:**
- Remove extra keys if you only have one organization
- Each key should be in quotes and separated by commas
- You can add as many keys as you need

### Step 3: Save the File
Save your changes to `export_vaults.py`

---

## Run the Script

### Step 1: Navigate to Your Project Folder
```bash
cd /path/to/fordefi-vault-export
```

### Step 2: Run the Script
```bash
python export_vaults.py
# or
python3 export_vaults.py
```

### Step 3: Monitor the Progress
You'll see output like this:

```
🔑 Found 2 valid API key(s)

📂 Loaded 0 existing addresses from vault_addresses.csv

==========================================================
🔑 Processing API Key 1/2
==========================================================

🔄 Starting to fetch vaults...
📡 Fetching vaults page 1... ✅ Success
   📊 Retrieved 91 vaults (total so far: 91)
✨ All pages fetched! (Total: 91 vaults)

🎉 Total vaults fetched: 91

🔍 Processing vaults and fetching addresses where needed...

[1/91] APT #1 (black_box) - fetching addresses... ⚠️  No addresses found
[2/91] ATL_fd_DEFI_doxxed_1_COSMOS (cosmos) ✅ Found 5 chain address(es)
[3/91] ATL_fd_Arb_contract_undoxxed_1_EVM (evm) ✅
...
[91/91] fd_11_ARB_doxxed_BTC (utxo) - fetching addresses... ✅ Found 1 address(es)

📝 Created new CSV: vault_addresses.csv
✅ Wrote 120 unique rows to vault_addresses.csv

==========================================================
🔑 Processing API Key 2/2
==========================================================
...
```

### Step 4: Check the Output
Once complete, you'll find a file named `vault_addresses.csv` in the same folder.

---

## Understanding the Output

### CSV Structure
The CSV file has three columns:

| Column | Description | Example |
|--------|-------------|---------|
| Vault Name | Name of the vault (with chain for Cosmos) | `ATL_fd_DEFI_doxxed_1_EVM` |
| Vault Type | Type of blockchain | `evm`, `solana`, `cosmos`, `utxo` |
| Vault Address | The actual blockchain address | `0xEf5276B4291Af759808B4289B757D57a37a31995` |

### Multiple Addresses
Some vaults may have multiple addresses:
- **Cosmos vaults**: One row per supported chain
  - Example: `ATL_fd_DEFI_doxxed_1_COSMOS (cosmos_osmosis-1)`
- **UTXO vaults**: May have multiple Bitcoin addresses

### Running Multiple Times
- The script **appends** to the existing CSV
- **Duplicate addresses are automatically skipped**
- You can safely run it multiple times with different API keys

### Blank Addresses
Some vault types may have blank addresses if:
- The vault hasn't been set up yet
- The vault type doesn't support addresses (e.g., black_box vaults)

---

## Clean Up

### Remove API Users After Use

Once you've successfully exported your vault addresses, it's good security practice to remove the API users you created:

### Step 1: Log into Fordefi
1. Go to [app.fordefi.com](https://app.fordefi.com)
2. Sign in with your credentials

### Step 2: Navigate to API Users
1. Click on **Settings** (gear icon) in the left sidebar
2. Select **API Users** from the settings menu

### Step 3: Delete the API User
1. Find the API user you created (e.g., "Vault Export Script")
2. Click the **three dots menu** (⋯) next to the API user
3. Select **Delete** or **Remove**
4. Confirm the deletion

### Step 4: Repeat for Each Organization
If you created API users in multiple organizations, repeat steps 1-3 in each organization.

### Step 5: Clear API Keys from Script
1. Open `export_vaults.py`
2. Remove or replace the API keys with placeholder text:
   ```python
   API_KEYS = [
       "PASTE_YOUR_FIRST_API_KEY_HERE",
   ]
   ```
3. Save the file

This ensures that:
- No unused API credentials remain active
- Your exported data remains secure
- You follow security best practices
