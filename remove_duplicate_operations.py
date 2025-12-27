"""
Remove duplicate Operations tab code
The new clean version was added but the old cluttered version wasn't removed
"""

def fix_duplicate_operations():
    file_path = r"C:/Users/deepak.chhabra/OneDrive - Datacom/Documents/Trademe Integration/Trademe Integration V2/retail_os/dashboard/app.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the second render_operations_tab definition (the old one)
    first_def = None
    second_def = None
    
    for i, line in enumerate(lines):
        if 'def render_operations_tab' in line:
            if first_def is None:
                first_def = i
                print(f"[INFO] First render_operations_tab at line {i+1}")
            else:
                second_def = i
                print(f"[INFO] Second render_operations_tab at line {i+1} (OLD CODE - will remove)")
                break
    
    if second_def:
        # Find the next function definition after the second one
        next_func = None
        for i in range(second_def + 1, len(lines)):
            if lines[i].startswith('def ') and 'render_operations_tab' not in lines[i]:
                next_func = i
                print(f"[INFO] Next function starts at line {i+1}")
                break
        
        if next_func:
            # Remove lines from second_def to next_func
            print(f"[ACTION] Removing lines {second_def+1} to {next_func}")
            new_lines = lines[:second_def] + lines[next_func:]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            print(f"[SUCCESS] Removed {next_func - second_def} lines of old Operations code")
        else:
            print("[ERROR] Could not find next function")
    else:
        print("[INFO] No duplicate found - only one render_operations_tab exists")

if __name__ == "__main__":
    fix_duplicate_operations()
