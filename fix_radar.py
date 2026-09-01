import sys

with open('Frontend/src/pages/EligibilityRadar.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# We only want to modify the part inside the Radar Timeline section.
parts = content.split('      {/* Radar Timeline */}')
if len(parts) == 2:
    header = parts[0]
    timeline = parts[1]
    
    # 1. Timeline View Text
    timeline = timeline.replace('text-primary font-medium', 'text-white font-medium')
    
    # 2. Search input
    timeline = timeline.replace('bg-secondary/50 border border-border rounded pl-9 pr-3 py-1.5 text-sm text-primary', 'bg-white/10 border border-white/20 rounded pl-9 pr-3 py-1.5 text-sm text-white placeholder:text-zinc-400')
    timeline = timeline.replace('text-muted-foreground', 'text-zinc-400')
    
    # 3. Filter select
    timeline = timeline.replace('bg-secondary/50 border border-border text-primary text-xs rounded', 'bg-white/10 border border-white/20 text-white text-xs rounded')
    
    # 4. Text primary inside timeline
    timeline = timeline.replace('text-primary', 'text-white')
    
    # 5. Backgrounds of the cards in the list
    timeline = timeline.replace('border-border bg-muted', 'border-white/20 bg-white/10')
    timeline = timeline.replace('border-border bg-card/70', 'border-white/10 bg-white/5')
    timeline = timeline.replace('border-border bg-card shadow-sm', 'border-white/10 bg-white/5 shadow-sm')
    
    # 6. Secondary button
    timeline = timeline.replace('bg-secondary/50 hover:bg-secondary', 'bg-white/10 hover:bg-white/20')
    
    # 7. No cases message
    timeline = timeline.replace('bg-card shadow-sm rounded border border-border', 'bg-white/5 shadow-sm rounded border border-white/10 text-zinc-400')
    
    with open('Frontend/src/pages/EligibilityRadar.tsx', 'w', encoding='utf-8') as f:
        f.write(header + '      {/* Radar Timeline */}' + timeline)
    print('Updated successfully')
else:
    print('Could not split file')
