import os
import re

files_to_fix = [
    r'c:\Users\sathw\Downloads\Nyaya_Mitra\Frontend\src\pages\EligibilityRadar.tsx',
    r'c:\Users\sathw\Downloads\Nyaya_Mitra\Frontend\src\pages\CasesPage.tsx',
    r'c:\Users\sathw\Downloads\Nyaya_Mitra\Frontend\src\pages\CaseIntelligence.tsx',
    r'c:\Users\sathw\Downloads\Nyaya_Mitra\Frontend\src\components\CommandPalette.tsx'
]

for fp in files_to_fix:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove the import line
    content = re.sub(r'import\s+{\s*MOCK_CASES\s*}\s+from\s+"@/data/mock";\s*\n', '', content)
    
    # Also we should replace occurrences of MOCK_CASES with an empty array if used statically,
    # but looking at the grep, they might be used as fallbacks. Let's just remove the import
    # and change MOCK_CASES to []
    content = content.replace('MOCK_CASES', '[]')
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed {fp}')

try:
    os.remove(r'c:\Users\sathw\Downloads\Nyaya_Mitra\Frontend\src\data\mock.ts')
    print('Deleted mock.ts')
except FileNotFoundError:
    pass
