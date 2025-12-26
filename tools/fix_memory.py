#!/usr/bin/env python3
"""
Fix corrupted trade memory JSON file.

Attempts to recover as much data as possible from a corrupted JSON file.
"""
import json
import sys
from pathlib import Path

def fix_memory_file(filepath: Path):
    """Attempt to fix a corrupted memory file."""
    print(f"Attempting to fix {filepath}...")
    
    if not filepath.exists():
        print(f"File {filepath} does not exist")
        return False
    
    # Try to read line by line and reconstruct
    trades = []
    current_trade = {}
    in_trade = False
    brace_count = 0
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Try to find the last valid JSON structure
        # Look for the last complete trade entry
        lines = content.split('\n')
        valid_json = []
        
        for i, line in enumerate(lines):
            valid_json.append(line)
            # Try to parse what we have so far
            try:
                test_content = '\n'.join(valid_json)
                # Try to close it properly
                if test_content.count('{') > test_content.count('}'):
                    # Add closing braces
                    test_content += '}' * (test_content.count('{') - test_content.count('}'))
                if not test_content.strip().endswith('}'):
                    test_content += '\n}'
                
                # Try to parse
                data = json.loads(test_content)
                if 'trades' in data:
                    print(f"✅ Found valid JSON up to line {i+1}")
                    return data
            except:
                # If this line breaks it, remove it and try previous
                if i > 0:
                    valid_json.pop()
                    try:
                        test_content = '\n'.join(valid_json)
                        if test_content.count('{') > test_content.count('}'):
                            test_content += '}' * (test_content.count('{') - test_content.count('}'))
                        if not test_content.strip().endswith('}'):
                            test_content += '\n}'
                        data = json.loads(test_content)
                        if 'trades' in data:
                            print(f"✅ Found valid JSON up to line {i}")
                            return data
                    except:
                        pass
                continue
        
        # If we get here, try a simpler approach: backup and create new
        print("⚠️ Could not recover JSON structure. Creating backup and new file...")
        backup_path = filepath.with_suffix('.json.backup')
        filepath.rename(backup_path)
        print(f"✅ Backed up corrupted file to {backup_path}")
        
        # Create new empty file
        new_data = {
            "trades": [],
            "last_updated": None
        }
        with open(filepath, 'w') as f:
            json.dump(new_data, f, indent=2)
        print(f"✅ Created new empty memory file")
        return new_data
        
    except Exception as e:
        print(f"❌ Error fixing file: {e}")
        return None


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    memory_file = project_root / "data" / "trade_memory.json"
    
    result = fix_memory_file(memory_file)
    
    if result:
        print(f"\n✅ Memory file fixed!")
        print(f"   Trades recovered: {len(result.get('trades', []))}")
    else:
        print("\n❌ Could not fix memory file")
        sys.exit(1)








