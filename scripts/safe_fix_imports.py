import os

for root, dirs, files in os.walk('.'):
    if '.git' in root or 'node_modules' in root or '.venv' in root:
        continue
    for file in files:
        if file.endswith('.py') and file != 'safe_fix_imports.py':
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'integrations.integrations' in content:
                new_content = content.replace('integrations.integrations', 'integrations')
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Fixed {path}")
