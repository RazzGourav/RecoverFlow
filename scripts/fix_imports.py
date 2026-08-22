import os

def fix_imports_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = content.replace("from apps.api.db.models import", "from db.models import")
    new_content = new_content.replace("from apps.api.db.database import", "from db.database import")
    
    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

def main():
    dirs_to_check = ['domain', 'integrations', 'workers']
    
    for d in dirs_to_check:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py"):
                    fix_imports_in_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
