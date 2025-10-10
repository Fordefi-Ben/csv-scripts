import requests
import csv
from datetime import datetime
from typing import List, Dict, Any
import sys

# Configuration
API_BASE_URL = "https://api.fordefi.com/api/v1"
API_TOKEN = "eyJhbGciOiJFZERTQSIsImtpZCI6ImZ3MFc3aVpocUc0SUEzaXV4ZmhQIiwidHlwIjoiSldUIn0.eyJpc3MiOiJodHRwczovL2FwaS5mb3JkZWZpLmNvbS8iLCJzdWIiOiI2YTlhMTIxZi01YmZiLTRjZWYtYmY3Mi01NWJjMGNiYzQ4MDVAZm9yZGVmaSIsImF1ZCI6WyJodHRwczovL2FwaS5mb3JkZWZpLmNvbS9hcGkvIl0sImV4cCI6MjA3NTQ3MTQwOCwiaWF0IjoxNzYwMTExNDA4LCJqdGkiOiIzODA2YmJiYi0xZDE3LTRmOWMtYjA4Mi03ODBkZWJlMWM2NTQifQ.HNZ4a5IRl9xt6GnRdwLOHBaZnoOJXs2ISmq8CRduS3fztx7qeCDWM7ls3yg4FKjIBMuMZmjX33WBfAULpG_1CA"  # Replace with your actual API token

def get_transactions(page: int = 1, size: int = 50) -> Dict[str, Any]:
    """
    Fetch transactions from the Fordefi API.
    
    Args:
        page: Page number to retrieve
        size: Number of transactions per page
    
    Returns:
        JSON response containing transactions
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    params = {
        "page": page,
        "size": size
    }
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/transactions",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching transactions: {e}")
        sys.exit(1)

def extract_transaction_data(transaction: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract relevant fields from a transaction object.
    
    Args:
        transaction: Transaction dictionary from API response
    
    Returns:
        Dictionary with extracted fields for CSV
    """
    # Transaction ID
    tx_id = transaction.get("id", "")
    
    # Transaction Network (chain name)
    chain = transaction.get("chain", {})
    network = chain.get("name", "")
    
    # Transaction Type
    tx_type = transaction.get("type", "")
    
    # Created At
    created_at = transaction.get("created_at", "")
    
    # Initiator (created by name)
    managed_data = transaction.get("managed_transaction_data", {})
    created_by = managed_data.get("created_by", {})
    initiator = created_by.get("name", "")
    
    # Origin Vault (vault name)
    vault = transaction.get("vault", {})
    origin_vault = vault.get("name", "")
    
    # Policy Match details
    policy_match = managed_data.get("policy_match", {})
    is_default = str(policy_match.get("is_default", "")).lower()
    rule_name = policy_match.get("rule_name", "")
    action_type = policy_match.get("action_type", "")
    
    # Direction
    direction = transaction.get("direction", "")
    
    # Approvers (if approval was required)
    approvers = []
    approval_request = managed_data.get("approval_request", {})
    if approval_request:
        approvers_list = approval_request.get("approvers", [])
        for approver in approvers_list:
            user = approver.get("user", {})
            approver_name = user.get("name", "")
            decision = approver.get("decision", "")
            state = approver.get("state", "")
            if approver_name:
                approvers.append(f"{approver_name} ({state})")
    
    approvers_str = "; ".join(approvers) if approvers else ""
    
    return {
        "Transaction ID": tx_id,
        "Transaction Network": network,
        "Transaction Type": tx_type,
        "Created At": created_at,
        "Initiator": initiator,
        "Origin Vault": origin_vault,
        "Policy Match - Is Default": is_default,
        "Policy Match - Rule Name": rule_name,
        "Policy Match - Action Type": action_type,
        "Direction": direction,
        "Approvers": approvers_str
    }

def export_to_csv(transactions: List[Dict[str, str]], filename: str = "fordefi_transactions.csv"):
    """
    Export transaction data to CSV file.
    
    Args:
        transactions: List of transaction dictionaries
        filename: Output CSV filename
    """
    if not transactions:
        print("No transactions to export.")
        return
    
    fieldnames = [
        "Transaction ID",
        "Transaction Network",
        "Transaction Type",
        "Created At",
        "Initiator",
        "Origin Vault",
        "Policy Match - Is Default",
        "Policy Match - Rule Name",
        "Policy Match - Action Type",
        "Direction",
        "Approvers"
    ]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(transactions)
        
        print(f"Successfully exported {len(transactions)} transactions to {filename}")
    except IOError as e:
        print(f"Error writing to CSV file: {e}")
        sys.exit(1)

def main():
    """
    Main function to fetch all transactions and export to CSV.
    """
    print("Fetching transactions from Fordefi API...")
    
    all_transactions = []
    page = 1
    size = 50
    
    while True:
        print(f"Fetching page {page}...")
        response = get_transactions(page=page, size=size)
        
        transactions = response.get("transactions", [])
        if not transactions:
            break
        
        # Extract data from each transaction
        for tx in transactions:
            tx_data = extract_transaction_data(tx)
            all_transactions.append(tx_data)
        
        # Check if there are more pages
        total = response.get("total", 0)
        fetched = page * size
        
        if fetched >= total:
            break
        
        page += 1
    
    print(f"Total transactions fetched: {len(all_transactions)}")
    
    # Export to CSV
    export_to_csv(all_transactions)

if __name__ == "__main__":
    main()