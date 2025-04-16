# -----------------------------
# Function: Format Markdown Recursively
# -----------------------------

def generate_markdown_from_tree(messages, title):
    def recurse(msgs, level=0):
        md = ""
        indent = ">" * level
        for msg in msgs:
            persona = msg["persona"]
            text = msg["text"].strip()
            if indent:
                md += f"{indent} **{persona}**:\n\n{indent} {text}\n\n"
            else:
                md += f"**{persona}**:\n\n{text}\n\n"
            if msg.get("children"):
                md += recurse(msg["children"], level + 1)
        return md

    return f"## Discussion: {title}\n\n" + recurse(messages)
