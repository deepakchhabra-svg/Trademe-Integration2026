"""
Fix main() function structure - remove orphaned code inside render_operations_tab
"""

def fix_main_function():
    file_path = r"C:/Users/deepak.chhabra/OneDrive - Datacom/Documents/Trademe Integration/Trademe Integration V2/retail_os/dashboard/app.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove lines 1334-1357 (orphaned tab code inside render_operations_tab)
    # These lines should be in main(), not in render_operations_tab
    print(f"[INFO] Total lines before: {len(lines)}")
    print(f"[INFO] Removing orphaned lines 1334-1357")
    
    # Keep everything before line 1333 and after line 1357
    new_lines = lines[:1333] + lines[1357:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"[SUCCESS] Fixed! Total lines after: {len(new_lines)}")
    print("[INFO] Removed orphaned tab rendering code from inside render_operations_tab")

if __name__ == "__main__":
    fix_main_function()
