import os

def get_function_str(filepath, func_name):
    if not os.path.exists(filepath):
        return f"File not found: {filepath}\n"
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    start = -1
    indent = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith(f"def {func_name}("):
            start = idx
            indent = len(line) - len(line.lstrip())
            break
            
    if start == -1:
        return f"Function {func_name} not found in {filepath}\n"
        
    out = []
    out.append(f"--- {func_name} in {filepath} ---\n")
    for idx in range(start, len(lines)):
        line = lines[idx]
        if idx > start and line.strip() and not line.startswith(" " * (indent + 1)) and not line.strip().startswith("#") and not line.strip().startswith(")") and not line.strip().startswith("def "):
            break
        out.append(line)
    out.append("\n" + "="*50 + "\n")
    return "".join(out)

output = []
output.append(get_function_str("C:/Users/user/Desktop/kontrolyeni-v6vip-main/app_core/instagram_api.py", "fetch_liker_usernames"))
output.append(get_function_str("c:/Users/user/Desktop/kontrolv10-fix-main/app_core/instagram_api.py", "fetch_liker_usernames"))

output.append(get_function_str("C:/Users/user/Desktop/kontrolyeni-v6vip-main/app_core/token_service.py", "fetch_likers_with_failover"))
output.append(get_function_str("c:/Users/user/Desktop/kontrolv10-fix-main/app_core/token_service.py", "fetch_likers_with_failover"))

output.append(get_function_str("C:/Users/user/Desktop/kontrolyeni-v6vip-main/app_core/instagram_api.py", "build_auth_headers"))
output.append(get_function_str("c:/Users/user/Desktop/kontrolv10-fix-main/app_core/instagram_api.py", "build_auth_headers"))

with open("scratch/compare_output.txt", "w", encoding="utf-8") as f:
    f.write("".join(output))
print("Saved comparison to scratch/compare_output.txt")
