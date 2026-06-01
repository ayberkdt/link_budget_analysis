import json

log_path = r'C:\Users\ayber\.gemini\antigravity\brain\6cfbdc55-fe48-4dd4-8875-426456ccbab3\.system_generated\logs\transcript.jsonl'
with open(log_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
count = 0
for line in reversed(lines):
    data = json.loads(line)
    if data.get('type') == 'PLANNER_RESPONSE' and data.get('tool_calls'):
        for call in data['tool_calls']:
            if call['name'] in ('write_to_file', 'replace_file_content'):
                args = call.get('args', {})
                if 'gui.py' in str(args):
                    count += 1
                    print(f'Found at step {data.get("step_index")}. Tool: {call["name"]}')
                    if 'CodeContent' in args:
                        print('Length:', len(args['CodeContent']))
                    elif 'ReplacementContent' in args:
                        print('Length:', len(args['ReplacementContent']))
