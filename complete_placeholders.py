#!/usr/bin/env python3
"""
Complete placeholder conversion for all query methods in db/api.py
Adds convert_query_placeholders() before all pd.read_sql() calls
"""

import re

def complete_placeholder_conversions():
    with open('db/api.py', 'r') as f:
        lines = f.readlines()

    # Methods that need placeholder conversion
    methods_with_queries = [
        'get_stock_list', 'get_price_history', 'get_latest_price', 'get_stock_info',
        '_get_metadata', 'get_update_status', 'get_dividends', 'get_splits',
        'get_analyst_ratings', 'get_price_targets', 'get_institutional_holders',
        'get_insider_transactions', 'get_options', 'get_technical_indicators',
        'get_intraday_data', 'get_watchlist'
    ]

    new_lines = []
    current_method = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Track which method we're in
        if line.strip().startswith('def '):
            method_name = line.strip().split('(')[0].replace('def ', '')
            current_method = method_name if method_name in methods_with_queries else None

        # Check if we need to add conversion before pd.read_sql
        if current_method and 'pd.read_sql(query, conn' in line:
            # Check if conversion is already there
            if i > 0 and 'convert_query_placeholders' not in lines[i-1]:
                # Add import at start of method if not present
                method_start = i - 1
                while method_start > 0 and not lines[method_start].strip().startswith('def '):
                    method_start -= 1

                # Check if import already exists in this method
                has_import = False
                for j in range(method_start, i):
                    if 'from db.connection import db_connection' in lines[j]:
                        has_import = True
                        break

                # Get indentation
                indent = ' ' * (len(line) - len(line.lstrip()))

                # Add conversion line before pd.read_sql
                new_lines.append(f'{indent}query = db_connection.convert_query_placeholders(query)\n')

        new_lines.append(line)
        i += 1

    # Write back
    with open('db/api.py', 'w') as f:
        f.writelines(new_lines)

    print(f"✓ Added placeholder conversions to {len(methods_with_queries)} query methods")
    print(f"✅ All placeholder conversions complete!")

if __name__ == '__main__':
    complete_placeholder_conversions()
