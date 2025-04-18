from datetime import datetime
from collections import defaultdict

def get_round_class(round_value):
    base = "round-badge"
    if isinstance(round_value, str) and round_value.lower().startswith("goal"):
        return base + " goal-badge"
    return base

def format_round_label(round_value):
    if isinstance(round_value, str) and round_value.lower().startswith("goal"):
        return f"🟣 {round_value}"
    return f"Round {round_value}"

def render_node(node, persona_colors):
    color = persona_colors.get(node["persona"], "#000")
    content = f"""
        <details open>
            <summary>
                <span class="persona" style="color: {color};">{node['persona']}</span>
                <span class="{get_round_class(node['round'])}">{format_round_label(node['round'])}</span>
                <span class="timestamp-badge">{node['timestamp']}</span>
            </summary>
            <div class="message">
                {node['text']}
                {"<div style='font-size: 0.8em; color: #6b7280; margin-top: 0.5em;'>RAG Score: " + (str(node['rag_score']) if node['rag_score'] is not None else "Not Applicable") + "</div>" if "rag_score" in node else ""}
            </div>
    """
    for child in node.get("children", []):
        content += f'<div class="thread">{render_node(child, persona_colors)}</div>\n'
    content += "</details>\n"
    return content

# -----------------------------
# Function: HTML Template with Styles
# -----------------------------
def generate_html_with_styles(
        tree, 
        title, 
        timestamp, 
        summary_lines, 
        persona_colors, 
        engagement_score, 
        total_comments, 
        cli_command,
        runtime_log,
        discussion_summary=None):
    #     state):
    # cli_command = state["cli_command"]
    # runtime_log = state["runtime_log"]

    html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f9f9f9;
                    color: #333;
                    margin: 2em;
                }}
                h1 {{ color: #222; }}
                .timestamp {{
                    font-size: 0.9em;
                    color: #555;
                    margin-bottom: 1em;
                }}
                .meta-bar {{
                    background-color: #0f172a;
                    color: white;
                    padding: 12px 16px;
                    border-radius: 8px;
                    display: flex;
                    gap: 1.5em;
                    font-size: 0.9em;
                    margin-bottom: 1.5em;
                }}
                .meta-bar span {{
                    display: flex;
                    align-items: center;
                    gap: 0.4em;
                }}
                .message {{
                    background-color: white;
                    line-height: 1.45;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    padding: 0.50em 1em;
                    margin: 0.5em 0;
                }}
                .persona {{
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 6px;
                    background-color: rgba(255, 255, 255, 0.15);
                    color: white;
                }}
                .round-badge {{
                    background-color: #334155;
                    color: #f1f5f9;
                    border-radius: 12px;
                    padding: 2px 8px;
                    font-size: 0.8em;
                    margin-left: 10px;
                }}
                .goal-badge {{
                    background-color: #9333ea;
                    color: white;
                }}
                .timestamp-badge {{
                    font-size: 0.75em;
                    color: #cbd5e1;
                    margin-left: 12px;
                }}
                .thread {{
                    margin-left: 1em;
                    border-left: 2px solid #ccc;
                    padding-left: .5em;
                }}
                details {{
                    margin: 0.25em 0;
                    background: linear-gradient(to right, #1e1b4b, #312e81);
                    padding: 1em;
                    border-radius: 8px;
                }}
                summary {{
                    font-weight: bold;
                    cursor: pointer;
                    color: white;
                }}
                .extra-meta {{
                    margin-top: 2em;
                }}
                .extra-meta details {{
                    background: #0f172a;
                    color: #f8fafc;
                    padding: 1em;
                    margin-bottom: 1em;
                    border-radius: 8px;
                    font-family: 'Fira Mono', monospace;
                }}
                .extra-meta summary {{
                    font-weight: bold;
                    font-size: 1em;
                    cursor: pointer;
                    color: #f8fafc;
                }}
                .extra-meta pre {{
                    background-color: #1e293b;
                    color: #f1f5f9;
                    padding: 0.75em;
                    margin-top: 0.5em;
                    border-radius: 6px;
                    overflow-x: auto;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
        <h1>Discussion: {title}</h1>
        <div class="timestamp">Generated on <em>{timestamp}</em></div>

        <div class="meta-bar">
            <span>🔥 Engagement Level: {engagement_score:.0%}</span>
            <span>💬 Comments: {total_comments}</span>
        </div>
        """

    # Split discussion vs goal round nodes
    normal_nodes = [n for n in tree if not (isinstance(n["round"], str) and n["round"].lower().startswith("goal"))]
    goal_nodes = [n for n in tree if isinstance(n["round"], str) and n["round"].lower().startswith("goal")]

    for node in normal_nodes:
        html += render_node(node, persona_colors)

    if goal_nodes:
        html += "<h2 style='margin-top: 2em; color: #9333ea;'>🟣 Goal Round</h2>\n"
        for node in goal_nodes:
            html += render_node(node, persona_colors)

    html += """
    <details open>
    <summary>📝 Discussion Summary</summary>
    """

    if discussion_summary:
        html += f"""
        <div style='margin-bottom: 1em; color: white;'>
            <p><strong>Case Summary:</strong> {discussion_summary}</p>
        </div>
        """

    html += "<ul>\n"
    for line in summary_lines:
        html += f"<li style='color: white'>{line}</li>\n"
    html += "</ul></details>"

    html += f"""
        <div class="extra-meta">
        <details open>
        <summary>💻 CLI Command</summary>
        <div style="background-color: #1e293b; border-radius: 6px; padding: 0.5em 0.75em; margin-bottom: 1em;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25em;">
                <span style="color: #f1f5f9; font-size: 0.9em;">Copy this command:</span>
                <button onclick="copyToClipboard('cli-command')" style="background-color: #334155; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer;">📋 Copy</button>
            </div>
            <pre style="margin: 0;"><code id="cli-command" style="color: #f1f5f9;">{cli_command}</code></pre>
        </div>
        </details>

        <details>
        <summary>📜 Run Log</summary>
        <pre><code>{chr(10).join(runtime_log)}</code></pre>
        </details>
        </div>

        <script>
        function copyToClipboard(id) {{
            const text = document.getElementById(id).innerText;
            const button = event.target;
            navigator.clipboard.writeText(text).then(() => {{
                const originalText = button.innerText;
                button.innerText = "✅ Copied";
                button.disabled = true;
                setTimeout(() => {{
                    button.innerText = originalText;
                    button.disabled = false;
                }}, 2000);
            }}).catch(err => {{
                alert("Failed to copy: " + err);
            }});
        }}
        </script>

        """

    html += "</body></html>"

    return html
