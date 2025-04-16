# -----------------------------
# Function: Format JSON tree Pretty
# -----------------------------

def generate_tree_from_tree(messages):
    def recurse(msgs, level=0):
        tree = ""
        indent = "  " * level
        for msg in msgs:
            snippet = msg["text"][:60].replace('\n', ' ') + "..."
            tree += f"{indent}- {msg['persona']} (Round {msg['round']}): {snippet}\n"
            if msg.get("children"):
                tree += recurse(msg["children"], level + 1)
        return tree

    return recurse(messages)
