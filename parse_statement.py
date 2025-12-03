import re
from datetime import datetime

def is_number(value):
    try:
        float(value.replace(",", ""))
        return True
    except (ValueError, AttributeError):
        return False


def parse_statement(lines):
    statement_metadata = {}
    statement_summarydata = {}
    transactions = []

    print(f"\n=== PARSING STARTED ===")

        # First pass: get metadata
    for i, line in enumerate(lines[:50]):  # Only check first 50 lines
        line = line.strip()
        if line.startswith("From:"):
            date = line.replace("From:", "").strip()
            parsed = datetime.strptime(date, "%d %b %y")
            formattedDate = parsed.strftime("%Y-%m-%d")

            statement_metadata["period_from"] = formattedDate

        elif line.startswith("To:"):
            date = line.replace("To:", "").strip()
            parsed = datetime.strptime(date, "%d %b %y")
            formattedDate = parsed.strftime("%Y-%m-%d")

            statement_metadata["period_to"] = formattedDate
            statement_metadata["statement_date"] = statement_metadata["period_to"]

    
    for i, line in enumerate(lines):
        if re.match(r"^\d{2} [A-Za-z]{3}( \d{2})?$", line):
            date = line
            parsed = datetime.strptime(date, "%d %b %y")
            formattedDate = parsed.strftime("%Y-%m-%d")

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

            balance = numberStorage[-1]

            transactions.append({
                "date": formattedDate,
                "description": description,
                "debit": debit,
                "credit": credit,
                "raw_balance": balance
            })

    for i, line in enumerate(lines[-20:]):
        if line.startswith("Statement Summary"):
            next_index = i + 1
            if next_index < len(lines[-20:]):
                statement_summarydata["Payments"] = float(lines[-20:][next_index + 1]
                        .strip()
                        .replace(",", "")
                        .replace("R", "")
                )

                statement_summarydata["Deposits"] = float(lines[-20:][next_index + 3]
                        .strip()
                        .replace(",", "")
                        .replace("R", "")
                )

   
    
    print(f"\n=== PARSING COMPLETE ===")



    print(f"Total transactions found: {len(transactions)}")

    return {
        "statement_metadata": statement_metadata,
        "transactions": transactions,
        "statement_summarydata": statement_summarydata
    }