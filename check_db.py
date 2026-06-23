import re
with open('bim-viewer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find("const db = {")
end = content.find("// Ruler is always active", start)
db_section = content[start:end]

keys_to_check = [
    'RetainingWalls_Left_South', 'RetainingWalls_Left_North',
    'RetainingWalls_Right_South', 'RetainingWalls_Right_North',
    'PCC_Left', 'PCC_Right', 'Footings_Left', 'Footings_Right',
    'BedBlocks_Left', 'BedBlocks_Right',
    'Backwalls_Left', 'Backwalls_Right',
    'ApproachSlabs_South', 'ApproachSlabs_North',
    'Handrails_Left', 'Handrails_Right',
    'Bearings_South', 'Bearings_North',
    'ProtectionWalls_South', 'ProtectionWalls_North',
    'EarthFill_South', 'EarthFill_North',
    'GuardStones_South', 'GuardStones_North',
    'Drainage_South', 'Drainage_North',
    'ExpansionJoints_South', 'ExpansionJoints_North',
    'NameBoard'
]
for key in keys_to_check:
    if f"'{key}'" in db_section:
        print(f'OK: {key}')
    else:
        print(f'MISSING: {key}')
