import os
import re

def fix_imports_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Replace "from integrations.X" with "from integrations.integrations.X"
    # ONLY if X is in [factory, validation, base, mock, razorpay, provider]
    
    modules = ['factory', 'validation', 'base', 'mock', 'razorpay', 'provider']
    
    new_content = content
    for m in modules:
        # Match 'from integrations.m' or 'import integrations.m'
        # Do not match 'integrations.analytics' or 'integrations.integrations'
        
        # from integrations.m
        new_content = re.sub(rf"from integrations\.{m}\b", f"from integrations.integrations.{m}", new_content)
        # import integrations.m
        new_content = re.sub(rf"import integrations\.{m}\b", f"import integrations.integrations.{m}", new_content)

    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

def main():
    dirs_to_check = ['domain', 'integrations', 'workers', 'ai', 'apps', 'tests']
    
    for d in dirs_to_check:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py"):
                    fix_imports_in_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
