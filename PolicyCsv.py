import requests
import csv
import json
import os
from typing import Any, Dict, List, Tuple, Set


def _display_name(obj: Dict[str, Any], *, fallbacks: Tuple[str, ...] = ("name", "email", "id")) -> str:
    """Return a human-friendly display name given a dict with name/email/id."""
    if not isinstance(obj, dict):
        return str(obj)
    for key in fallbacks:
        val = obj.get(key)
        if val:
            return str(val)
    return "Unknown"


def _fmt_address(a: Any) -> str:
    """Format an address item that might be a string or dict."""
    if isinstance(a, str):
        return a
    if isinstance(a, dict):
        # Common shapes: {"address": "0x.."} or {"hex_repr": "..."} or {"value": "..."}
        return a.get("address") or a.get("hex_repr") or a.get("value") or json.dumps(a)
    return str(a)


def _fmt_contact(contact: Dict[str, Any]) -> str:
    """Format an address book contact as 'Name <address> (ChainLabel)' where possible."""
    name = _display_name(contact, fallbacks=("name", "id"))
    addr_ref = (contact.get("address_ref") or {})
    address = addr_ref.get("address") or ""
    chain_label = addr_ref.get("chain_type") or ""
    chains = addr_ref.get("chains") or []
    if not chain_label and isinstance(chains, list) and chains:
        chain_names = []
        for ch in chains:
            if isinstance(ch, dict):
                chain_names.append(ch.get("name") or ch.get("unique_id") or ch.get("chain_type") or "")
            else:
                chain_names.append(str(ch))
        chain_label = ", ".join([c for c in chain_names if c]) or chain_label

    if chain_label and address:
        return f"{name} <{address}> ({chain_label})"
    if address:
        return f"{name} <{address}>"
    return name


def _label_any_all(cond_type: str, noun_plural: str) -> str:
    """Create a human label for any/all conditions."""
    cond_type = (cond_type or "").lower()
    if cond_type == "all":
        return f"All {noun_plural}"
    if cond_type == "any":
        return f"Any {noun_plural}"
    return ""


def extract_transaction_assets(assets_data: Any) -> str:
    """Return 'Name (ChainName)' for each asset in rule_conditions.transaction_assets."""
    if not assets_data:
        return ""
    items: List[str] = []
    for item in assets_data:
        ai = {}
        if isinstance(item, dict):
            ai = item.get("asset_info", {})
            if not ai and any(k in item for k in ("asset_identifier", "name", "symbol")):
                ai = item
        name = ai.get("name") or ai.get("symbol") or "Unknown"
        chain_name = (
            (ai.get("asset_identifier") or {}).get("chain", {}).get("name")
            or (ai.get("chain") or {}).get("name")
            or (ai.get("asset_identifier") or {}).get("details", {}).get("chain")
            or "N/A"
        )
        items.append(f"{name} ({chain_name})")
    return " | ".join(items)


def extract_initiators(initiators: Any) -> Dict[str, str]:
    """
    Parse transaction_initiators into:
      - initiator_users         (names or emails)
      - initiator_user_groups   (group names)
    Supports:
      Flat: users / user_refs / user_groups / user_group_refs
      Conditional: users_conditions / initiators_conditions with type 'any'|'all'|'custom'
    """
    out_users: Set[str] = set()
    out_groups: Set[str] = set()

    if not isinstance(initiators, dict):
        return {}

    def _add_users(items: Any):
        if isinstance(items, list):
            for u in items:
                out_users.add(_display_name(u, fallbacks=("name", "email", "id")))

    def _add_groups(items: Any):
        if isinstance(items, list):
            for g in items:
                out_groups.add(_display_name(g, fallbacks=("name", "id")))

    # Flat
    _add_users(initiators.get("users"))
    _add_users(initiators.get("user_refs"))
    _add_groups(initiators.get("user_groups"))
    _add_groups(initiators.get("user_group_refs"))

    # Conditional
    cond = (
        (initiators.get("users_conditions") or {}).get("condition")
        or (initiators.get("initiators_conditions") or {}).get("condition")
    )
    if isinstance(cond, dict):
        ctype = (cond.get("type") or "").lower()
        if ctype in ("all", "any"):
            label = _label_any_all(ctype, "users")
            if label:
                out_users.add(label)
        else:
            _add_users(cond.get("users"))
            _add_users(cond.get("user_refs"))
            _add_groups(cond.get("user_groups"))
            _add_groups(cond.get("user_group_refs"))

    out: Dict[str, str] = {}
    if out_users:
        out["initiator_users"] = ", ".join(sorted(out_users))
    if out_groups:
        out["initiator_user_groups"] = ", ".join(sorted(out_groups))
    return out


def extract_origins(origins: Any) -> Dict[str, str]:
    """
    Parse origins into:
      - origin_vaults
      - origin_vault_groups
    Supports flat keys and vaults_conditions.condition with type 'any'|'all'|'custom'.
    """
    out_vaults: Set[str] = set()
    out_groups: Set[str] = set()

    if not isinstance(origins, dict):
        return {}

    def _add_vaults(items: Any):
        if isinstance(items, list):
            for v in items:
                out_vaults.add(_display_name(v, fallbacks=("name", "id")))

    def _add_groups(items: Any):
        if isinstance(items, list):
            for g in items:
                out_groups.add(_display_name(g, fallbacks=("name", "id")))

    # Flat (if API ever sends these at top-level)
    _add_vaults(origins.get("vaults"))
    _add_vaults(origins.get("vault_refs"))
    _add_groups(origins.get("vault_groups"))
    _add_groups(origins.get("vault_group_refs"))

    # Conditional
    vc = (origins.get("vaults_conditions") or {}).get("condition")
    if isinstance(vc, dict):
        ctype = (vc.get("type") or "").lower()
        if ctype in ("all", "any"):
            label = _label_any_all(ctype, "vaults")
            if label:
                out_vaults.add(label)
        else:
            _add_vaults(vc.get("vaults"))
            _add_vaults(vc.get("vault_refs"))
            _add_groups(vc.get("vault_groups"))
            _add_groups(vc.get("vault_group_refs"))

    out: Dict[str, str] = {}
    if out_vaults:
        out["origin_vaults"] = ", ".join(sorted(out_vaults))
    if out_groups:
        out["origin_vault_groups"] = ", ".join(sorted(out_groups))
    return out


def extract_recipients(recipients: Any) -> Dict[str, str]:
    """
    Parse recipients, accounting for:
      - addresses (flat) + addresses_conditions (any/all/custom with addresses/address_groups)
      - addressbook_contacts_conditions (any/all/custom with address_book_contacts/address_book_groups)
      - dapps (flat) + dapps_conditions
      - vaults_conditions under recipients (any/all/custom with vaults/vault_groups)
    Produces:
      - recipient_addresses
      - recipient_address_groups
      - recipient_contacts
      - recipient_contact_groups
      - recipient_dapps
      - recipient_vaults
      - recipient_vault_groups
    """
    out: Dict[str, str] = {}
    if not isinstance(recipients, dict):
        return out

    # --- DAPPS ---
    dapps_parts: List[str] = []
    dapps_flat = recipients.get("dapps")
    if isinstance(dapps_flat, list) and dapps_flat:
        dapp_info = []
        for d in dapps_flat:
            name = (d or {}).get("name", "Unknown")
            did = (d or {}).get("id", "N/A")
            chain_name = ((d or {}).get("chain") or {}).get("name", "N/A")
            dapp_info.append(f"{name} (ID: {did}, Chain: {chain_name})")
        if dapp_info:
            dapps_parts.append(" | ".join(dapp_info))
    dapps_cond = (recipients.get("dapps_conditions") or {}).get("condition")
    if isinstance(dapps_cond, dict):
        ctype = (dapps_cond.get("type") or "").lower()
        if ctype in ("all", "any"):
            label = _label_any_all(ctype, "dapps")
            if label:
                dapps_parts.append(label)
        else:
            dapps_list = dapps_cond.get("dapps")
            if isinstance(dapps_list, list) and dapps_list:
                info = []
                for d in dapps_list:
                    name = (d or {}).get("name", "Unknown")
                    did = (d or {}).get("id", "N/A")
                    chain_name = ((d or {}).get("chain") or {}).get("name", "N/A")
                    info.append(f"{name} (ID: {did}, Chain: {chain_name})")
                if info:
                    dapps_parts.append(" | ".join(info))
    if dapps_parts:
        out["recipient_dapps"] = " | ".join([p for p in dapps_parts if p])

    # --- ADDRESSES ---
    addr_set: Set[str] = set()
    flat_addrs = recipients.get("addresses")
    if isinstance(flat_addrs, list):
        for a in flat_addrs:
            addr_set.add(_fmt_address(a))

    addrs_cond = (recipients.get("addresses_conditions") or {}).get("condition")
    if isinstance(addrs_cond, dict):
        ctype = (addrs_cond.get("type") or "").lower()
        if ctype in ("all", "any"):
            addr_set.add(_label_any_all(ctype, "addresses"))
        else:
            for a in (addrs_cond.get("addresses") or []):
                addr_set.add(_fmt_address(a))
            groups = addrs_cond.get("address_groups") or []
            if groups:
                out["recipient_address_groups"] = ", ".join(
                    sorted({_display_name(g, fallbacks=("name", "id")) for g in groups})
                )

    if addr_set:
        out["recipient_addresses"] = " | ".join(sorted(addr_set))

    # --- ADDRESS BOOK CONTACTS / GROUPS ---
    ab_cond = (recipients.get("addressbook_contacts_conditions") or {}).get("condition")
    contacts: Set[str] = set()
    if isinstance(ab_cond, dict):
        ctype = (ab_cond.get("type") or "").lower()
        if ctype in ("all", "any"):
            contacts.add(_label_any_all(ctype, "contacts"))
        else:
            for c in (ab_cond.get("address_book_contacts") or []):
                contacts.add(_fmt_contact(c))
            ab_groups = ab_cond.get("address_book_groups") or []
            if ab_groups:
                out["recipient_contact_groups"] = ", ".join(
                    sorted({_display_name(g) for g in ab_groups})
                )
    if contacts:
        out["recipient_contacts"] = " | ".join(sorted(contacts))

    # --- RECIPIENT VAULTS / GROUPS (from recipients.vaults_conditions) ---
    rv_cond = (recipients.get("vaults_conditions") or {}).get("condition")
    rv_vaults: Set[str] = set()
    rv_groups: Set[str] = set()
    if isinstance(rv_cond, dict):
        ctype = (rv_cond.get("type") or "").lower()
        if ctype in ("all", "any"):
            rv_vaults.add(_label_any_all(ctype, "vaults"))
        else:
            for v in (rv_cond.get("vaults") or []):
                rv_vaults.add(_display_name(v, fallbacks=("name", "id")))
            for g in (rv_cond.get("vault_groups") or []):
                rv_groups.add(_display_name(g, fallbacks=("name", "id")))
    if rv_vaults:
        out["recipient_vaults"] = ", ".join(sorted(rv_vaults))
    if rv_groups:
        out["recipient_vault_groups"] = ", ".join(sorted(rv_groups))

    return out


def extract_rule_data(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract essential rule data from the API response."""
    rules = response_data.get('rules', [])
    extracted_rules: List[Dict[str, Any]] = []

    for rule in rules:
        rule_data: Dict[str, Any] = {
            'rule_id': rule.get('id'),
            'rule_name': rule.get('name'),
            'rule_action': (rule.get('rule_action') or {}).get('type'),
            'created_at': rule.get('created_at'),
            'modified_at': rule.get('modified_at'),
            'modified_by': (rule.get('modified_by') or {}).get('name'),
        }

        conditions = (rule.get('rule_conditions') or {})

        # Transaction types
        tx_types = conditions.get('transaction_types') or []
        if tx_types:
            rule_data['transaction_types'] = ", ".join([str(t) for t in tx_types])

        # Initiators (users + groups, flat + conditional)
        rule_data.update(extract_initiators(conditions.get('transaction_initiators') or {}))

        # Origins (vaults + groups, flat + conditional)
        rule_data.update(extract_origins(conditions.get('origins') or {}))

        # Recipients (all variants incl. recipients.vaults_conditions)
        rule_data.update(extract_recipients(conditions.get('recipients') or {}))

        # ABI methods
        abi_methods = conditions.get('abi_methods') or []
        if abi_methods:
            rule_data['abi_methods'] = ", ".join([str(m) for m in abi_methods])

        # Assets
        assets_str = extract_transaction_assets(conditions.get('transaction_assets'))
        if assets_str:
            rule_data['transaction_assets'] = assets_str

        # Amount limit
        amount_limit = conditions.get('amount_limit') or {}
        if amount_limit:
            amount = amount_limit.get('amount')
            currency = (amount_limit.get('currency') or 'N/A').upper()
            is_net = amount_limit.get('is_net_amount', False)
            if amount is not None:
                rule_data['amount_limit'] = f"{amount} {currency} (Net: {is_net})"
            else:
                rule_data['amount_limit'] = f"(No numeric amount) {currency} (Net: {is_net})"

        # EIP712
        eip712 = conditions.get('eip712_message') or {}
        if eip712:
            domains = eip712.get('domains') or []
            primary_types = eip712.get('primary_types') or []
            if domains:
                rule_data['eip712_domains'] = ", ".join(domains)
            if primary_types:
                rule_data['eip712_primary_types'] = ", ".join(primary_types)

        # Approval groups
        if rule_data.get('rule_action') == 'require_approval':
            approval_groups = (rule.get('rule_action') or {}).get('approval_groups', [])
            if approval_groups:
                parts = []
                for g in approval_groups:
                    threshold = g.get('threshold', 'N/A')
                    ugr = g.get('user_group_refs') or []
                    ur = g.get('user_refs') or []
                    g_names = ", ".join([_display_name(x) for x in ugr]) if ugr else ""
                    u_names = ", ".join([_display_name(x) for x in ur]) if ur else ""
                    segment = [f"Threshold: {threshold}"]
                    if g_names:
                        segment.append(f"Groups: {g_names}")
                    if u_names:
                        segment.append(f"Users: {u_names}")
                    parts.append(", ".join(segment))
                if parts:
                    rule_data['approval_groups'] = " | ".join(parts)

        extracted_rules.append(rule_data)

    return extracted_rules


def convert_to_csv(data: List[Dict[str, Any]], output_file: str = 'rules_output.csv'):
    """Convert extracted data to CSV."""
    if not data:
        print("No data to write to CSV")
        return

    column_order = [
        'rule_name',
        'rule_id',
        'rule_action',
        'transaction_types',
        'initiator_users',
        'initiator_user_groups',
        'origin_vaults',
        'origin_vault_groups',
        'recipient_dapps',
        'recipient_addresses',
        'recipient_address_groups',
        'recipient_contacts',
        'recipient_contact_groups',
        'recipient_vaults',         # NEW for recipients.vaults_conditions
        'recipient_vault_groups',   # NEW for recipients.vaults_conditions
        'abi_methods',
        'transaction_assets',
        'amount_limit',
        'eip712_domains',
        'eip712_primary_types',
        'approval_groups',
        'created_at',
        'modified_at',
        'modified_by'
    ]

    all_keys = set()
    for rule in data:
        all_keys.update(rule.keys())

    fieldnames = [col for col in column_order if col in all_keys]
    additional_keys = sorted(all_keys - set(fieldnames))
    fieldnames.extend(additional_keys)

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"CSV file created: {output_file}")
    print(f"Number of rules: {len(data)}")
    print(f"Number of columns: {len(fieldnames)}")


def main():
    API_URL = "https://api.fordefi.com/api/v1/policies/transactions"
    API_TOKEN = "{TOKEN HERE}"  # Replace with your actual API token

    HEADERS = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        print(f"Calling API: {API_URL}")
        response = requests.get(API_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        extracted_rules = extract_rule_data(data)
        convert_to_csv(extracted_rules)
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()