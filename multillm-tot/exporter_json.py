import json

def generate_json_from_tree(messages):
    return json.dumps(messages, indent=2)
