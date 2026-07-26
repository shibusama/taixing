import re

path = r"D:\13191\Documents\workbuddyspace\2026-07-26-13-55-46\rocket-news\mega-projects.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Find everything from pt-groups opening to closing
start = c.find('<div class="pt-groups">')
end = c.find('</div>', start + 50)

# Find the actual closing div that matches pt-groups
# Count nested divs
i = start + len('<div class="pt-groups">')
depth = 0
while i < len(c):
    if c[i:i+5] == '<div ' or c[i:i+4] == '<div':
        depth += 1
        i += 1
    elif c[i:i+6] == '</div>':
        depth -= 1
        i += 6
        if depth == 0:
            end = i
            break
    else:
        i += 1

print(f"pt-groups: {start} to {end}")

# Extract the properly structured pt-groups
pt_content = c[start:end]
print(f"Length of pt-groups: {len(pt_content)}")

# Find the broken 浙江特高压环网 entry
if 'data-tab="tab-energy">浙江特高压环网' in pt_content:
    print("Found broken entry in pt-groups")
    # This is the broken raw text - we need to find the preceding structure
    # and replace the broken section with the correct HTML
    
    # Find the last proper pt-group before the broken part
    # The broken part starts after the last valid </div></div> before the raw text
    
    # Get everything before pt-groups
    before = c[:start]
    
    # The science entries and broken entry are the last part
    # Let's find all properly formed pt-groups by regex
    valid_groups = re.findall(r'<div class="pt-group">.*?</div></div>', pt_content, re.DOTALL)
    print(f"Found {len(valid_groups)} valid pt-groups")
    for g in valid_groups:
        name_match = re.search(r'<span class="pt-name[^>]*>([^<]+)</span>', g)
        if name_match:
            print(f"  - {name_match.group(1)}")

else:
    print("No broken entry found - checking full file for timeline structure")
    # Find all pt-groups
    valid_groups = re.findall(r'<div class="pt-group">.*?</div></div>', c, re.DOTALL)
    print(f"Found {len(valid_groups)} pt-groups total")
    for g in valid_groups:
        name_match = re.search(r'<span class="pt-name[^>]*>([^<]+)</span>', g)
        if name_match:
            print(f"  - {name_match.group(1)}")
        else:
            print(f"  - [MALFORMED: {g[:80]}...]")

print("\nFull section reconstruction approach needed.")
print("end of script")
