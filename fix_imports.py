import sys

with open(r"C:\Development\ISyCo Git\MALDOOM\tests\test_epoch_transparency_v2.py", 'r', encoding='utf-8') as f:
    content = f.read()

# Insert sys.path after the initial imports
old = 'import hashlib\nimport json\nimport sys\nfrom dataclasses'
new = '''import hashlib
import json
import sys
sys.path.insert(0, r"C:\\Development\\ISyCo Git\\Walbolge")
sys.path.insert(0, r"C:\\Development\\ISyCo Git\\Malbolge-Translator")
from dataclasses'''

content = content.replace(old, new)

with open(r"C:\Development\ISyCo Git\MALDOOM\tests\test_epoch_transparency_v2.py", 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed')