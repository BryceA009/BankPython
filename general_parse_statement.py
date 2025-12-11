import re
from datetime import datetime
import statistics
from collections import Counter

# regex patterns for common date formats
DATE_PATTERNS = [
    r"^\d{1,2}/\d{1,2}/\d{2,4}$",            # 07/12/2025 or 7/12/25
    r"^\d{1,2}[a-z]{2}\s+[A-Za-z]{3,9}\s+\d{2,4}$",  # 7th December 2025 or 7th Dec 24
    r"^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}$",          # 7 December 2025 or 13 Nov 24
]

def is_valid_date(text):
    text = text.strip()
    for pattern in DATE_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    return False

def is_number(value):
    try:
        float(value.replace(",", ""))
        return True
    except (ValueError, AttributeError):
        return False

def detect_two_tables(transactions):
    total_with_date2 = 0
    mismatches = 0

    for row in transactions:
        d1 = row.get("date1")
        d2 = row.get("date2")

        if d2:
            total_with_date2 += 1
            if d1 != d2:
                mismatches += 1

    if total_with_date2 == 0:
        return False

    ratio = mismatches / total_with_date2

    return ratio > 0.7

def split_if_two_tables(transactions):
    if not detect_two_tables(transactions):
        return transactions

    final = []

    for row in transactions:
        left = {}
        right = {}

        for key, value in row.items():
            if key.endswith("1"):
                left[key[:-1]] = value
            elif key.endswith("2"):
                right[key[:-1]] = value

        # Add left (if meaningful)
        if any(v for v in left.values()):
            final.append(left)

        # Add right (if meaningful)
        if any(v for v in right.values()):
            final.append(right)

    return final

def expand_wrapped_headers(header_info, items, y_tol=6, x_tol=12):
    """
    After finding main header row, check nearby y-coordinates for wrapped text
    and merge them into the headers.
    """
    header_y = header_info["y"]
    header_items = header_info["headings"]

    # Find items near the header row (excluding already merged items)
    nearby_items = [
        i for i in items
        if abs(i["y"] - header_y) <= y_tol
        and i not in header_items
    ]

    if not nearby_items:
        return header_info  # nothing extra found

    # Combine old header items + nearby ones
    combined_items = header_items + nearby_items

    # Merge wrapped headers again
    merged = merge_wrapped_headers(combined_items, y_tol=y_tol, x_tol=x_tol)

    # Update header info
    header_info["headings"] = merged
    return header_info

def detect_and_merge_headers(items, y_tol=6, x_tol=12, min_cols=3):

    items = [i for i in items if i["text"].strip()]  

    # --- Step 1: Filter out margin/outlier rows ---
    ys = [i["y"] for i in items]
    median_y = statistics.median(ys)
    items = [i for i in items if abs(i["y"] - median_y) < 800]

    if not items:
        items = [i for i in items if i["text"].strip()]

    # --- Step 2: Group items by approximate Y to form rows ---
    rows = []
    for it in sorted(items, key=lambda i: i["y"]):
        for row in rows:
            if abs(row["y"] - it["y"]) <= y_tol:
                row["items"].append(it)
                break
        else:
            rows.append({"y": it["y"], "items": [it]})

    # --- Step 3: Merge rows that are very close vertically ---
    merged_rows = []
    i = 0
    while i < len(rows):
        curr = rows[i]
        if i + 1 < len(rows) and abs(rows[i + 1]["y"] - curr["y"]) <= y_tol:
            combined = curr["items"] + rows[i + 1]["items"]
            merged_rows.append({"y": curr["y"], "items": combined})
            i += 2
        else:
            merged_rows.append(curr)
            i += 1

    # --- Step 4: Score rows based on header keywords ---
    HEADER_KEYWORDS = [
        "date", "posting date", "transaction", "description",
        "money in", "money out", "balance", "payments",
        "deposits", "credit", "debit", "amount", "post date"
    ]

    scored = []
    for row in merged_rows:
        txt = " ".join(it["text"].lower() for it in row["items"])
        hits = sum(1 for k in HEADER_KEYWORDS if k in txt)
        spread = max(it["x"] for it in row["items"]) - min(it["x"] for it in row["items"])
        scored.append({
            "row": row,
            "hits": hits,
            "spread": spread,
            "word_count": len(txt.split()),
            "cols": len(row["items"])
        })

    # Keep only the best candidate rows
    max_hits = max(s["hits"] for s in scored)
    candidates = [s for s in scored if s["hits"] == max_hits and s["cols"] >= min_cols]

    if not candidates:
        return None

    # Sort by hits and spread
    candidates.sort(key=lambda s: (s["hits"], s["spread"]), reverse=True)
    best_row = candidates[0]["row"]
    best_y = best_row["y"]

    # --- Step 5: Look for wrapped text above/below the main header row ---
    nearby_items = [
        i for i in items
        if abs(i["y"] - best_y) <= y_tol * 2  # extend tolerance
        and i not in best_row["items"]
    ]

    all_header_items = best_row["items"] + nearby_items

    # --- Step 6: Merge all nearby/column-wrapped items ---
    final_headers = merge_wrapped_headers(all_header_items, y_tol=y_tol, x_tol=x_tol)

    return {
        "y": best_y,
        "headings": final_headers
    }

def group_items_by_page(items):
    pages = {}
    for it in items:
        pg = it["page_number"]
        if pg not in pages:
            pages[pg] = []
        pages[pg].append(it)
    return pages

def merge_wrapped_headers(row_items, y_tol=6, x_tol=12):
    """
    Merge pieces of header text that are close in both X and Y.
    This handles multi-line/wrapped header labels.
    """

    # Sort by X then Y
    items = sorted(row_items, key=lambda i: (i["x"], i["y"]))

    merged = []
    current = {"x": items[0]["x"], "text": items[0]["text"], "y": items[0]["y"]}

    for it in items[1:]:
        x_close = abs(it["x"] - current["x"]) <= x_tol
        y_close = abs(it["y"] - current["y"]) <= y_tol

        if x_close:
            # Same column, multi-line header
            current["text"] += " " + it["text"]
            current["y"] = min(current["y"], it["y"])
        else:
            # New column
            merged.append(current)
            current = {"x": it["x"], "text": it["text"], "y": it["y"]}

    merged.append(current)
    return merged

def parse_page(items, chunk_size=3000):
    header_info = find_heading_row(items, chunk_size=chunk_size)
    if not header_info or not header_info.get("headings"):
        return []  # page with no transactions
    return extract_transactions_with_dates(items, header_info)

def detect_headings(items, y_tol=10, x_merge_tol=8, min_cols=3):
  
    items = [i for i in items if i["text"].strip()]  
    for i in items[0:50]:
        print(f"Item: x={i['x']:.1f} y={i['y']:.1f} text='{i['text']}'")
    # Hard filter weird outlier rows (usually margin trash)
    ys = [i["y"] for i in items]
    median_y = statistics.median(ys)
    items = [i for i in items if abs(i["y"] - median_y) < 800]


    y_counts = Counter(round(i["y"], 1) for i in items)
    valid_y = {y for y, c in y_counts.items() if c >= 2}  

    items = [i for i in items if round(i["y"], 1) in valid_y]

    # If filtering nuked everything, fall back to original list (rare)
    if not items:
        items = [i for i in items if i["text"].strip()]


    items_sorted = sorted(items, key=lambda i: i["y"])
    rows = []

    for item in items_sorted:
        for row in rows:
            if abs(row["y"] - item["y"]) <= y_tol:
                row["items"].append(item)
                break
        else:
            rows.append({"y": item["y"], "items": [item]})

    merged_rows = []
    i = 0

    while i < len(rows):
        curr = rows[i]
        if i + 1 < len(rows) and abs(rows[i + 1]["y"] - curr["y"]) <= y_tol:
            nxt = rows[i + 1]
            # merge
            combined = curr["items"] + nxt["items"]
            merged_rows.append({"y": curr["y"], "items": combined})
            i += 2
        else:
            merged_rows.append(curr)
            i += 1


    HEADER_KEYWORDS = [
        "date", "posting date", "transaction", "transaction date", "description",
        "money in", "money out", "balance", "payments",
        "deposits", "credit", "debit", "amount", "post date"
    ]

    scored = []
    for row in merged_rows:
        txt = " ".join(it["text"].lower() for it in row["items"])
        hits = sum(1 for k in HEADER_KEYWORDS if k in txt)
        spread = (
            max(it["x"] for it in row["items"])
            - min(it["x"] for it in row["items"])
        )

        scored.append({
            "row": row,
            "hits": hits,
            "spread": spread,
            "word_count": len(txt.split()),
            "cols": len(row["items"])
        })

    max_hits = max(s["hits"] for s in scored)
    scored = [s for s in scored if s["hits"] == max_hits]

    candidates = [
        s for s in scored
        if s["cols"] >= min_cols and s["word_count"] <= 20
    ]

    print("Candidate row y-coordinates:")
    for c in candidates:
        print(c["row"]["y"])

    if not candidates:
        print("No valid header candidates found.")
        return None

    candidates.sort(key=lambda s: (s["hits"], s["spread"]), reverse=True)
    best = candidates[0]["row"]

    print(f"Selected heading row at y={best['y']}")

    merged = merge_wrapped_headers(best["items"])


    return {
    "y": best["y"],         
    "headings": merged      
    }

def find_heading_row(items, chunk_size=3000):

    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i : i + chunk_size])

    all_candidates = []

    HEADER_KEYWORDS = [
        "date", "posting date", "transaction", "description",
        "money in", "money out", "balance", "payments",
        "deposits", "credit", "debit", "amount", "post date"
    ]

    # store: chunk_index -> {"headings": [...], "y": y_value}
    chunk_headings = {}

    for idx, chunk in enumerate(chunks):
        print(f"\n--- Checking chunk {idx+1}/{len(chunks)} ---")

        result = detect_and_merge_headers(chunk)

        if not result:
            print("No headings found in this chunk.")
            continue

        y_val = result["y"]
        headings = result["headings"]

        chunk_headings[idx] = {
            "headings": headings,
            "y": y_val
        }

        # score each heading
        for h in headings:
            txt = h["text"].lower()
            hits = sum(1 for k in HEADER_KEYWORDS if k in txt)
            spread = h["x"]

            all_candidates.append({
                "heading": h,
                "hits": hits,
                "spread": spread,
                "chunk_index": idx
            })

    if not all_candidates:
        print("No headings detected in any chunk.")
        return {
            "headings": None,
            "y": None
        }

    all_candidates.sort(key=lambda c: (c["hits"], c["spread"]), reverse=True)
    best = all_candidates[0]

    best_heading = best["heading"]
    best_chunk = best["chunk_index"]

    print("Headings found in best chunk:")
    for h in chunk_headings[best_chunk]["headings"]:
        print(f"    x={h['x']:.1f}  '{h['text']}'")

    best_y = chunk_headings[best_chunk]["y"]
    print(f"Selected heading row y={best_y}")

    return {
        "headings": chunk_headings[best_chunk]["headings"],
        "y": best_y
    }

def extract_transactions_with_dates(items, header_info):
    if not header_info or not header_info.get("headings"):
        return []

    headings = header_info["headings"]
    header_y = header_info["y"]
    page_number = header_info["page_number"]

    DATE_KEYWORDS = ["date", "posting date", "post date", "value date"]
    DESC_KEYWORDS = ["description", "transaction", "details", "narrative"]
    AMT_KEYWORDS = ["amount", "debit", "credit", "money in", "money out", "payments", "deposits"]
    BAL_KEYWORDS = ["balance", "available balance", "account balance"]

    # Identify date columns and description columns
    date_columns = []
    desc_columns = []
    amount_columns = []
    balance_columns = []

    for h in headings:
        txt = h["text"].lower()
        if any(k in txt for k in DATE_KEYWORDS):
            date_columns.append(h["x"])
        elif any(k in txt for k in DESC_KEYWORDS):
            desc_columns.append(h["x"])
        elif any(k in txt for k in AMT_KEYWORDS):
            amount_columns.append(h["x"])
        elif any(k in txt for k in BAL_KEYWORDS):
            balance_columns.append(h["x"])

    if not date_columns:
        print("No date columns found in header")
        return []

    x_tol = 50

    # Filter page items below the header row
    data_items = [
        i for i in items
        if i["page_number"] == page_number and i["y"] > header_y
    ]

    # Group items into rows by Y coordinate
    rows = {}
    for it in data_items:
        y_rounded = round(it["y"], 1)
        rows.setdefault(y_rounded, []).append(it)

    transactions = []

    for y, row_items in sorted(rows.items()):
        row_data = {}

        # Extract dates
        has_date = False
        for idx, x_col in enumerate(date_columns, start=1):
            col_key = f"date{idx}"
            row_data[col_key] = None
            for it in row_items:
                if abs(it["x"] - x_col) <= x_tol and is_valid_date(it["text"]):
                    row_data[col_key] = it["text"].strip()
                    has_date = True
                    break

        # Skip row if no valid date
        if not has_date:
            continue

        # Extract descriptions
        for idx, x_col in enumerate(desc_columns, start=1):
            col_key = f"description{idx}"
            row_data[col_key] = None
            for it in row_items:
                if abs(it["x"] - x_col) <= x_tol:
                    row_data[col_key] = it["text"].strip()
                    break

        for idx, x_col in enumerate(amount_columns, start=1):
            col_key = f"amount{idx}"
            row_data[col_key] = None
            for it in row_items:
                if 0 <= (it["x"] - x_col) <= x_tol:
                    row_data[col_key] = it["text"].strip()
                    break
        
        for idx, x_col in enumerate(balance_columns, start=1):
            col_key = f"balance{idx}"
            row_data[col_key] = None
            for it in row_items:
                if abs(it["x"] - x_col) <= x_tol:
                    row_data[col_key] = it["text"].strip()
                    break

        transactions.append(row_data)
        
    transactions = split_if_two_tables(transactions)
    return transactions

def general_parse_statement(items, chunk_size=3000):
    print("\n=== PARSING STARTED ===")

    pages = group_items_by_page(items)
    all_transactions = []
    all_headings = {}

    for pg, page_items in sorted(pages.items()):
        print(f"\n--- Parsing page {pg} ---")
        header_info = find_heading_row(page_items, chunk_size=chunk_size)

        if not header_info:
            print(f"No headings on page {pg}, skipping.")
            continue

        # Add page_number to header_info for downstream use
        header_info["page_number"] = pg
        all_headings[pg] = header_info
        transactions = extract_transactions_with_dates(page_items, header_info)
        all_transactions.extend(transactions)

    print("\n=== PARSING COMPLETE ===")
    print(f"Total transactions found: {len(all_transactions)}")

    return {
        "transactions": all_transactions,
        "headings": all_headings,
    }
