import sys

def replace_non_ascii(text):
    return text.encode('ascii', 'ignore').decode('ascii')

with open('src/views/connect_accounts/index.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace specific ones with equivalents
content = content.replace('──', '--')
content = content.replace('──────────────────────────────────────────────', '----------------------------------------------')
content = content.replace('▾', 'v')

# General cleanup
clean_content = "".join(i if ord(i) < 128 else " " for i in content)

with open('src/views/connect_accounts/index.jsx', 'w', encoding='utf-8') as f:
    f.write(clean_content)

print("Cleaned index.jsx")
