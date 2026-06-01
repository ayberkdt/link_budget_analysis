import json
import os

log_path = r'C:\Users\ayber\.gemini\antigravity\brain\6cfbdc55-fe48-4dd4-8875-426456ccbab3\.system_generated\logs\transcript.jsonl'
with open(log_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

content = None
for line in reversed(lines):
    data = json.loads(line)
    if data.get('type') == 'PLANNER_RESPONSE' and data.get('tool_calls'):
        for call in data['tool_calls']:
            if call['name'] == 'write_to_file' and 'gui.py' in call['args'].get('TargetFile', ''):
                content = call['args']['CodeContent']
                if 'THEME =' in content and 'ToggleSwitch' in content and 'SCENARIO_FILE' in content:
                    # Found the target one!
                    break
    if content and 'THEME =' in content and 'ToggleSwitch' in content:
        break

if content:
    if r'\n' in content and '\n' not in content:
        content = content.replace(r'\n', '\n').replace(r'\t', '\t').replace('\\"', '"')
    
    with open('src/gui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Restored the exact original gui.py. Length:', len(content))
else:
    print('Failed to find it.')
