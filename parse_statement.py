import re

def is_number(value):
    try:
        float(value.replace(",", ""))
        return True
    except (ValueError, AttributeError):
        return False

def parse_statement(lines):
    statement_metadata = {}
    transactions = []

    print(f"\n=== PARSING STARTED ===")

        # First pass: get metadata
    for i, line in enumerate(lines[:50]):  # Only check first 50 lines
        line = line.strip()
        if line.startswith("From:"):
            statement_metadata["period_from"] = line.replace("From:", "").strip()
        elif line.startswith("To:"):
            statement_metadata["period_to"] = line.replace("To:", "").strip()
            statement_metadata["statement_date"] = statement_metadata["period_to"]

    
    for i, line in enumerate(lines):


        # Detect date like "05 Oct"
        # if re.match(r"^\d{2} [A-Za-z]{3}$", line):
        if re.match(r"^\d{2} [A-Za-z]{3}( \d{2})?$", line):
            date = line
            description = lines[i + 1].strip()

            numberStorage = []
            debit = 0
            credit = 0
            
            for offset in range(3, 6):  # i+3, i+4, i+5
                candidate = lines[i + offset].strip().replace(",", "")
                if is_number(candidate):
                    numberStorage.append(float(candidate))
            
            for i in range(len(numberStorage)-1):
                if numberStorage[i] > 0:
                    credit = numberStorage[i]
                
                elif numberStorage[i] < 0:
                    debit = numberStorage[i]


            print(numberStorage)
            balance = numberStorage[-1]

            transactions.append({
                "date": date,
                "description": description,
                "debit": debit,
                "credit": credit,
                "raw_balance": balance
            })


            
    
    print(f"\n=== PARSING COMPLETE ===")



    print(f"Total transactions found: {len(transactions)}")

    return {
        "statement_metadata": statement_metadata,
        "transactions": transactions
    }