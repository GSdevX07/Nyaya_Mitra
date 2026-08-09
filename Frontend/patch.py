import re

with open('Frontend/src/pages/DocumentsPage.tsx', 'r', encoding='utf-8') as f:
    new_doc = f.read()

with open('Frontend/src/pages/DocumentsPage.temp.tsx', 'r', encoding='utf-8') as f:
    old_doc = f.read()

# 1. Extract the old modal JSX
# Search for '{/* ' + anything + ' Upload Modal ' + anything + ' */}'
old_modal_pattern = r'\{/\*.*?Upload Modal.*?\*/\}(.*?)\Z'
old_modal_match = re.search(old_modal_pattern, old_doc, re.DOTALL)
if not old_modal_match:
    print("Could not find Upload Modal in old doc")
    exit(1)
old_modal = '{/* Upload Modal */}' + old_modal_match.group(1)

# Apply theme replacements to the old modal
old_modal = old_modal.replace('bg-white/5', 'bg-secondary/50')
old_modal = old_modal.replace('bg-white/[0.02]', 'bg-background')
old_modal = old_modal.replace('border-white/10', 'border-border')
old_modal = old_modal.replace('border-white/15', 'border-border')
old_modal = old_modal.replace('text-white', 'text-primary')
old_modal = old_modal.replace('bg-black/30', 'bg-background')
old_modal = old_modal.replace('bg-black/40', 'bg-background')

# 2. Replace the new modal JSX
new_modal_pattern = r'\{/\* Upload Modal \*/\}(.*?)\Z'
new_modal_match = re.search(new_modal_pattern, new_doc, re.DOTALL)
if not new_modal_match:
    print("Could not find Upload Modal in new doc")
    exit(1)

new_doc = re.sub(new_modal_pattern, old_modal, new_doc, flags=re.DOTALL)

# 3. Fix onClick={() => openModal(d.case_id, ...)} vs setShowUploadModal
new_doc = new_doc.replace('setShowUploadModal(true);', 'openModal(d.case_id, d.document_type.toLowerCase().replace(/ /g, "_"));')

with open('Frontend/src/pages/DocumentsPage.tsx', 'w', encoding='utf-8') as f:
    f.write(new_doc)
print("Done!")
