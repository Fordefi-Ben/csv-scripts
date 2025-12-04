#!/usr/bin/env python3
"""
Script to fetch all vaults from Fordefi API and save to CSV.
For vaults without a direct address, fetches addresses from the addresses endpoint.
Handles pagination and appends to existing CSV if present.
"""

import requests
import csv
import os
from typing import List, Dict

# Configuration
API_BASE_URL = "https://api.fordefi.com"  # Update if different
API_KEYS = [
    "PASTE_YOUR_FIRST_API_KEY_HERE",
    "PASTE_YOUR_SECOND_API_KEY_HERE",
    # Add more API keys as needed
]
CSV_FILENAME = "vault_addresses.csv"
CSV_HEADERS = ["Vault Name", "Vault Type", "Vault Address"]


def fetch_all_vaults(api_key: str) -> List[Dict]:
    """
    Fetch all vaults from the organization, handling pagination.
    
    Args:
        api_key: Bearer token for authentication
        
    Returns:
        List of vault dictionaries
    """
    all_vaults = []
    page = 1
    
    # Clean the API key
    api_key = api_key.strip()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("\n🔄 Starting to fetch vaults...")
    
    while True:
        url = f"{API_BASE_URL}/api/v1/vaults"
        params = {
            "page": page,
            "size": 100
        }
        
        print(f"📡 Fetching vaults page {page}...", end=" ", flush=True)
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            break
        
        print(f"✅ Success")
            
        data = response.json()
        vaults = data.get("vaults", [])
        
        if not vaults:
            print("📭 No more vaults found")
            break
            
        all_vaults.extend(vaults)
        print(f"   📊 Retrieved {len(vaults)} vaults (total so far: {len(all_vaults)})")
        
        # Check if there are more pages
        total = data.get("total", 0)
        fetched_so_far = page * data.get("size", 100)
        
        if fetched_so_far >= total:
            print(f"✨ All pages fetched! (Total: {total} vaults)")
            break
            
        page += 1
    
    print(f"\n🎉 Total vaults fetched: {len(all_vaults)}\n")
    return all_vaults


def fetch_vault_addresses(vault_id: str, api_key: str) -> List[str]:
    """
    Fetch addresses for a specific vault.
    
    Args:
        vault_id: The vault ID
        api_key: Bearer token for authentication
        
    Returns:
        List of address strings
    """
    addresses = []
    page = 1
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    while True:
        url = f"{API_BASE_URL}/api/v1/vaults/{vault_id}/addresses"
        params = {
            "page": page,
            "size": 100
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"      ⚠️  Failed to fetch addresses: {response.status_code}")
            break
            
        data = response.json()
        address_objs = data.get("addresses", [])
        
        if not address_objs:
            break
        
        # Extract the actual address strings
        for addr_obj in address_objs:
            address_data = addr_obj.get("address", {})
            addr_string = address_data.get("address", "")
            if addr_string:
                addresses.append(addr_string)
        
        # Check if there are more pages
        total = data.get("total", 0)
        fetched_so_far = page * data.get("size", 100)
        
        if fetched_so_far >= total:
            break
            
        page += 1
    
    return addresses


def extract_csv_data(vaults: List[Dict], api_key: str) -> List[Dict]:
    """
    Extract relevant fields for CSV from vault objects.
    For vaults without direct addresses, fetch from addresses endpoint or extract from vault object.
    
    Args:
        vaults: List of vault objects from API
        api_key: Bearer token for authentication
        
    Returns:
        List of dictionaries with CSV-ready data
    """
    csv_data = []
    
    print("🔍 Processing vaults and fetching addresses where needed...\n")
    
    for i, vault in enumerate(vaults, 1):
        vault_name = vault.get("name", "")
        vault_type = vault.get("type", "")
        vault_address = vault.get("address", "")
        vault_id = vault.get("id", "")
        
        print(f"[{i}/{len(vaults)}] {vault_name} ({vault_type})", end="")
        
        # Handle Cosmos vaults - addresses are in chains_addresses array
        if vault_type == "cosmos":
            chains_addresses = vault.get("chains_addresses", [])
            if chains_addresses:
                print(f" ✅ Found {len(chains_addresses)} chain address(es)")
                # Create a row for each chain address
                for chain_addr in chains_addresses:
                    chain = chain_addr.get("chain", "")
                    address = chain_addr.get("address", "")
                    row = {
                        "Vault Name": f"{vault_name} ({chain})",
                        "Vault Type": vault_type,
                        "Vault Address": address
                    }
                    csv_data.append(row)
            else:
                print(" ⚠️  No chain addresses found")
                row = {
                    "Vault Name": vault_name,
                    "Vault Type": vault_type,
                    "Vault Address": ""
                }
                csv_data.append(row)
        
        # Handle TON vaults - address is in raw_account field
        elif vault_type == "ton":
            raw_account = vault.get("raw_account", "")
            if raw_account:
                print(" ✅")
            else:
                print(" ⚠️  No raw_account found")
            row = {
                "Vault Name": vault_name,
                "Vault Type": vault_type,
                "Vault Address": raw_account
            }
            csv_data.append(row)
        
        # Handle UTXO vaults - need to fetch from addresses endpoint
        elif vault_type == "utxo" and not vault_address:
            print(" - fetching addresses...", end="", flush=True)
            addresses = fetch_vault_addresses(vault_id, api_key)
            
            if addresses:
                print(f" ✅ Found {len(addresses)} address(es)")
                # Create a row for each address found
                for addr in addresses:
                    row = {
                        "Vault Name": vault_name,
                        "Vault Type": vault_type,
                        "Vault Address": addr
                    }
                    csv_data.append(row)
            else:
                print(" ⚠️  No addresses found")
                row = {
                    "Vault Name": vault_name,
                    "Vault Type": vault_type,
                    "Vault Address": ""
                }
                csv_data.append(row)
        
        # Handle black_box vaults - try fetching from addresses endpoint
        elif vault_type == "black_box" and not vault_address:
            print(" - fetching addresses...", end="", flush=True)
            addresses = fetch_vault_addresses(vault_id, api_key)
            
            if addresses:
                print(f" ✅ Found {len(addresses)} address(es)")
                for addr in addresses:
                    row = {
                        "Vault Name": vault_name,
                        "Vault Type": vault_type,
                        "Vault Address": addr
                    }
                    csv_data.append(row)
            else:
                print(" ⚠️  No addresses found")
                row = {
                    "Vault Name": vault_name,
                    "Vault Type": vault_type,
                    "Vault Address": ""
                }
                csv_data.append(row)
        
        # Handle all other vaults with direct addresses
        else:
            if vault_address:
                print(" ✅")
            else:
                print(" (no address)")
            
            row = {
                "Vault Name": vault_name,
                "Vault Type": vault_type,
                "Vault Address": vault_address
            }
            csv_data.append(row)
    
    print()
    return csv_data


def write_to_csv(data: List[Dict], filename: str, seen_addresses: set):
    """
    Write data to CSV, appending if file exists, creating if it doesn't.
    Deduplicates based on addresses.
    
    Args:
        data: List of dictionaries to write
        filename: Name of the CSV file
        seen_addresses: Set of addresses already in the CSV
        
    Returns:
        Updated set of seen addresses
    """
    file_exists = os.path.exists(filename)
    mode = 'a' if file_exists else 'w'
    
    # Filter out duplicates
    unique_data = []
    duplicates_count = 0
    
    for row in data:
        address = row["Vault Address"]
        # Allow multiple entries with blank addresses (they're different vaults)
        if address == "":
            unique_data.append(row)
        elif address not in seen_addresses:
            unique_data.append(row)
            seen_addresses.add(address)
        else:
            duplicates_count += 1
    
    if duplicates_count > 0:
        print(f"⚠️  Skipped {duplicates_count} duplicate address(es)")
    
    with open(filename, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        
        # Write header only if creating new file
        if not file_exists:
            writer.writeheader()
            print(f"📝 Created new CSV: {filename}")
        else:
            print(f"📝 Appending to existing CSV: {filename}")
        
        writer.writerows(unique_data)
    
    print(f"✅ Wrote {len(unique_data)} unique rows to {filename}")
    return seen_addresses


def load_existing_addresses(filename: str) -> set:
    """
    Load existing addresses from CSV to prevent duplicates.
    
    Args:
        filename: Name of the CSV file
        
    Returns:
        Set of addresses already in the file
    """
    seen = set()
    if os.path.exists(filename):
        with open(filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                address = row.get("Vault Address", "")
                if address:  # Only track non-empty addresses
                    seen.add(address)
        print(f"📂 Loaded {len(seen)} existing addresses from {filename}\n")
    return seen


def main():
    """Main execution function."""
    # Validate API keys
    valid_keys = [key.strip() for key in API_KEYS if key and key != "PASTE_YOUR_FIRST_API_KEY_HERE" and key != "PASTE_YOUR_SECOND_API_KEY_HERE"]
    
    if not valid_keys:
        print("❌ Error: Please set at least one API_KEY in API_KEYS list!")
        return
    
    print(f"🔑 Found {len(valid_keys)} valid API key(s)\n")
    
    # Load existing addresses to prevent duplicates
    seen_addresses = load_existing_addresses(CSV_FILENAME)
    
    # Process each API key
    for key_index, api_key in enumerate(valid_keys, 1):
        print(f"{'='*60}")
        print(f"🔑 Processing API Key {key_index}/{len(valid_keys)}")
        print(f"{'='*60}\n")
        
        # Fetch all vaults with pagination
        vaults = fetch_all_vaults(api_key)
        
        if not vaults:
            print(f"⚠️  No vaults found for API key {key_index}\n")
            continue
        
        # Extract CSV data (will fetch addresses for certain vault types)
        csv_data = extract_csv_data(vaults, api_key)
        
        # Write to CSV with deduplication
        seen_addresses = write_to_csv(csv_data, CSV_FILENAME, seen_addresses)
        print()
    
    print(f"{'='*60}")
    print(f"✨ All done! Processed {len(valid_keys)} API key(s)")
    print(f"📊 Total unique addresses tracked: {len(seen_addresses)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
