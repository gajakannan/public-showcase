import json
import random
import click
from rich import print
from datetime import datetime
from collections import defaultdict
from jsonschema import validate, ValidationError
from init import get_openai_client, load_persona_schema
from persona_utils import enrich_personas_with_file_references
from html_exporter import generate_html_with_styles


# from file_utils import load_file_reference


COLOR_PALETTE = [
    "#f97316",  # vibrant orange
    "#e76f51",  # burnt orange
    "#d946ef",  # orchid magenta
    "#10b981",  # teal green
    "#dc2626",  # strong red
    "#0d9488",  # deep teal
    "#facc15",  # warm yellow
    "#a16207",  # dark mustard
    "#92400e",  # amber brown
    "#6b7280"   # neutral gray
]

# -----------------------------
# Function: Assign Colors To Personas
# -----------------------------
def assign_colors_to_personas(personas):
    persona_colors = {}
    for i, persona in enumerate(personas):
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
        persona_colors[persona["name"]] = color
    return persona_colors


# -----------------------------
# Function: Parse Personas JSON
# -----------------------------
def parse_personas(personas: list, schema):
    try:
        if not isinstance(personas, list):
            raise ValueError("Personas file must contain a JSON array.")
        for i, p in enumerate(personas):
            validate(instance=p, schema=schema)
            p.setdefault("engagement", 0.7)
        return personas

    except ValidationError as ve:
        raise click.BadParameter(f"Schema validation error in persona {i + 1}: {ve.message}")
    except Exception as e:
        raise click.BadParameter(f"Invalid personas structure: {e}")


# -----------------------------
# Function: Initialize State
# -----------------------------
def initialize_state(prompt: str, rounds: int, personas: list):
    return {
        "prompt": prompt,
        "rounds": rounds,
        "currentRound": 1,
        "conversationHistory": [],
        "personas": personas,
        "personaColors": assign_colors_to_personas(personas)
    }

# -----------------------------
# Function: Pick Random Message to Reply To
# -----------------------------
def pick_random_message(state):
    if not state["conversationHistory"]:
        return state["prompt"]
    return random.choice(state["conversationHistory"])


# -----------------------------
# Function: Get Thread Context (Parent, Grant Parent, Great-Grandparent, etc.)
# -----------------------------
def get_thread_context(state, message):
    context = []
    msg_map = {m["id"]: m for m in state["conversationHistory"]}
    while message:
        context.insert(0, f"{message['persona']}: {message['text']}")
        parent_id = message.get("parentId")
        message = msg_map.get(parent_id)
    return "\n".join(context)


# -----------------------------
# Function: Get Real LLM Reply (OpenAI)
# -----------------------------
def agent_reply(persona, target_text, round_num, client):
    system_prompt = f"You are a {persona['name']}. Provide thoughtful insights on the following:"
    user_prompt = target_text

    # Inject preloaded file references if available
    preloaded_refs = persona.get("resolved_file_references", [])
    if preloaded_refs:
        ref_texts = [
            f"[File: {ref['path']}]\n\n{ref['content']}" for ref in preloaded_refs
        ]
        if ref_texts:
            user_prompt = (
                "The following content is provided as reference for your persona. "
                "Use it to inform your response:\n\n"
                + "\n\n".join(ref_texts)
                + "\n\n"
                + user_prompt
            )
        # user_prompt = "\n\n".join(ref_texts) + "\n\n" + user_prompt

    try:
        response = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            model=persona.get("model", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[red]Failed to get response from OpenAI for {persona['name']}[/red]")
        print(f"[dim]{str(e)}[/dim]")
        return f"[ERROR] Round {round_num}: Unable to generate reply."

# -----------------------------
# Function: Run the Conversation
# -----------------------------
def run_conversation(state, client, goal_round="optional"):
    state["runtime_log"] = []

    def log_line(line):
        state["runtime_log"].append(line)
        print(line)

    while state["currentRound"] <= state["rounds"]:
        # print(f"\n[bold cyan]--- Round {state['currentRound']} ---[/bold cyan]")
        log_line(f"--- Round {state['currentRound']} ---")

        for persona in state["personas"]:
            # engagement_rate = persona.get("engagement", 0.7)
            supplied_engagement_rate = persona.get("engagement", 0.7)
            engagement_rate = 0.75 if state["currentRound"] == 1 else supplied_engagement_rate
            will_reply = random.random() < engagement_rate
            if not will_reply:
                # print(f"[dim]{persona['name']} chose to sit out this round.[/dim]")
                log_line(f"{persona['name']} chose to sit out this round.")
                continue

            target = state["prompt"] if state["currentRound"] == 1 else pick_random_message(state)
            # target_text = target if isinstance(target, str) else target["text"]
            target_text = target if isinstance(target, str) else get_thread_context(state, target)

            parent_id = None if isinstance(target, str) else target["id"]

            reply_text = agent_reply(persona, target_text, state["currentRound"], client)
            message_id = f"msg-{state['currentRound']}-{persona['name']}"

            state["conversationHistory"].append({
                "id": message_id,
                "round": state["currentRound"],
                "persona": persona["name"],
                "llm": persona["llm"],
                "parentId": parent_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": reply_text
            })

            # print(f"[green]{persona['name']} replied → {message_id}[/green]")
            log_line(f"{persona['name']} replied → {message_id}")

        state["currentRound"] += 1

    # Goal round handling (only once, after all normal rounds)
    if goal_round != "optional":
        log_line(f"[bold magenta]--- Goal Round: {goal_round.upper()} ---[/bold magenta]")

        # target_text = build_goal_prompt(goal_round, state)
        full_history = flatten_conversation_history_with_threads(state)
        target_text = (
            "Here is the full conversation so far:\n\n"
            + full_history
            + "\n\n"
            + build_goal_prompt(goal_round, state)
        )

        parent_id = None

        for persona in state["personas"]:
            log_line(f"{persona['name']} is participating in the goal round.")

            reply_text = agent_reply(persona, target_text, state["currentRound"], client)
            message_id = f"msg-{state['currentRound']}-{persona['name']}"

            state["conversationHistory"].append({
                "id": message_id,
                "round": "Goal - " + goal_round,
                "persona": persona["name"],
                "llm": persona["llm"],
                "parentId": parent_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": reply_text
            })

            log_line(f"{persona['name']} replied → {message_id}")

        state["currentRound"] += 1

# -----------------------------
# Function: Build Nested Thread Tree
# -----------------------------
def build_thread_tree(conversation_history):
    message_map = {}
    roots = []

    for msg in conversation_history:
        msg["children"] = []
        message_map[msg["id"]] = msg

    for msg in conversation_history:
        parent_id = msg.get("parentId")
        if parent_id:
            parent = message_map.get(parent_id)
            if parent:
                parent["children"].append(msg)
            else:
                roots.append(msg)
        else:
            roots.append(msg)

    return roots

# -----------------------------
# Function: Format Markdown Recursively
# -----------------------------
def format_markdown_from_tree(messages, level=0):
    markdown = ""
    indent = ">" * level

    for msg in messages:
        persona = msg["persona"]
        text = msg["text"].strip()

        if indent:
            markdown += f"{indent} **{persona}**:\n\n{indent} {text}\n\n"
        else:
            markdown += f"**{persona}**:\n\n{text}\n\n"

        if msg.get("children"):
            markdown += format_markdown_from_tree(msg["children"], level + 1)

    return markdown

# -----------------------------
# Function: Format HTML tree Recursively
# -----------------------------
def format_html_from_tree(nodes, state, depth=0):
    html = ""
    
    for node in nodes:
        indent = depth * 20
        color = state["personaColors"].get(node["persona"], "#7f8c8d")

        timestamp = node.get("timestamp", "unknown time")

        html += f'''
            <details open>
            <summary>
                <span class="persona" style="color: {color};">{node["persona"]}</span>
                <span class="round-badge">Round {node["round"]}</span>
                <span class="timestamp">{timestamp}</span>
            </summary>
            <div class="node" style="margin-left: {indent}px;">
                {node["text"].strip()}
            </div>
            '''

        if node.get("children"):
            html += format_html_from_tree(node["children"], state, depth + 1)

        html += '</details>\n'
    return html


# # -----------------------------
# # Function: HTML Template with Styles
# # -----------------------------
# def generate_html_with_styles(tree, title, timestamp, summary_lines, persona_colors, engagement_score, total_comments, state):
#     html = f"""<!DOCTYPE html>
#         <html>
#         <head>
#             <meta charset="UTF-8">
#             <title>{title}</title>
#             <style>
#                 body {{
#                     font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
#                     background-color: #f9f9f9;
#                     color: #333;
#                     margin: 2em;
#                 }}
#                 h1 {{
#                     color: #222;
#                 }}
#                 .timestamp {{
#                     font-size: 0.9em;
#                     color: #555;
#                     margin-bottom: 1em;
#                 }}
#                 .meta-bar {{
#                     background-color: #0f172a;
#                     color: white;
#                     padding: 12px 16px;
#                     border-radius: 8px;
#                     display: flex;
#                     gap: 1.5em;
#                     font-size: 0.9em;
#                     margin-bottom: 1.5em;
#                 }}
#                 .meta-bar span {{
#                     display: flex;
#                     align-items: center;
#                     gap: 0.4em;
#                 }}
#                 .message {{
#                     background-color: white;
#                     line-height: 1.45;
#                     border: 1px solid #ccc;
#                     border-radius: 8px;
#                     padding: 0.50em 1em;
#                     margin: 0.5em 0;
#                 }}
#                 .persona {{
#                     font-weight: bold;
#                     padding: 2px 6px;
#                     border-radius: 6px;
#                     background-color: rgba(255, 255, 255, 0.15);
#                     color: white;
#                 }}
#                 .round-badge {{
#                     background-color: #334155; /* slate-700 */
#                     color: #f1f5f9;            /* slate-100 */
#                     border-radius: 12px;
#                     padding: 2px 8px;
#                     font-size: 0.8em;
#                     margin-left: 10px;
#                 }}
#                 .goal-badge {{
#                     background-color: #9333ea; /* purple */
#                     color: white;

#                 }}
#                 .timestamp-badge {{
#                     font-size: 0.75em;
#                     color: #cbd5e1;  /* slate-300 */
#                     margin-left: 12px;
#                 }}
#                 .thread {{
#                     margin-left: 1em;
#                     border-left: 2px solid #ccc;
#                     padding-left: .5em;
#                 }}
#                 details {{
#                     margin-top: 0.25em;
#                     margin-bottom: 0.25em;
#                     background: linear-gradient(to right, #1e1b4b, #312e81);
#                     padding: 1em;
#                     border-radius: 8px;
#                 }}
#                 summary {{
#                     font-weight: bold;
#                     cursor: pointer;
#                 }}
#                 details summary {{
#                     color: white;
#                     font-weight: bold;
#                 }}
#                 details ul, details li {{
#                     color: white;
#                 }}
#                 .extra-meta {{
#                     margin-top: 2em;
#                 }}
#                 .extra-meta details {{
#                     background: #0f172a;
#                     color: #f8fafc;
#                     padding: 1em;
#                     margin-bottom: 1em;
#                     border-radius: 8px;
#                     font-family: 'Fira Mono', monospace;
#                 }}
#                 .extra-meta summary {{
#                     font-weight: bold;
#                     font-size: 1em;
#                     cursor: pointer;
#                     color: #f8fafc;
#                 }}
#                 .extra-meta pre {{
#                     background-color: #1e293b;
#                     color: #f1f5f9;
#                     padding: 0.75em;
#                     margin-top: 0.5em;
#                     border-radius: 6px;
#                     overflow-x: auto;
#                     font-size: 0.9em;
#                 }}
#             </style>
#         </head>
#         <body>
#         <h1>Discussion: {title}</h1>
#         <div class="timestamp">Generated on <em>{timestamp}</em></div>

#         <div class="meta-bar">
#             <span>🔥 Engagement Level: {engagement_score:.0%}</span>
#             <span>💬 Comments: {total_comments}</span>
#         </div>
#         """

#     def get_round_class(round_value):
#         base = "round-badge"
#         if isinstance(round_value, str) and round_value.lower().startswith("goal"):
#             return base + " goal-badge"
#         return base

#     def format_round_label(round_value):
#         if isinstance(round_value, str) and round_value.lower().startswith("goal"):
#             return f"🟣 {round_value}"
#         return f"Round {round_value}"


#     def render_node(node):
#         color = persona_colors.get(node["persona"], "#000")
#         content = f"""
#             <details open>
#                 <summary>
#                     <span class="persona" style="color: {color};">{node['persona']}</span>
#                     <span class="{get_round_class(node['round'])}">{format_round_label(node['round'])}</span>
#                     <span class="timestamp-badge">{node['timestamp']}</span>
#                 </summary>
#                 <div class="message">{node['text']}</div>
#             """
#         for child in node.get("children", []):
#             content += f'<div class="thread">{render_node(child)}</div>\n'
#         content += "</details>\n"
#         return content

#     # Split normal vs goal nodes
#     normal_nodes = [n for n in tree if not (isinstance(n["round"], str) and n["round"].lower().startswith("goal"))]
#     goal_nodes = [n for n in tree if isinstance(n["round"], str) and n["round"].lower().startswith("goal")]

#     # Render normal discussion first
#     for node in normal_nodes:
#         html += render_node(node)

#     # Render grouped goal section (if any)
#     if goal_nodes:
#         html += "<h2 style='margin-top: 0.5em; color: #9333ea;'>🟣 Goal Round</h2>\n"
#         for node in goal_nodes:
#             html += render_node(node)

#     # for top_node in tree:
#     #     is_goal = isinstance(top_node["round"], str) and top_node["round"].lower().startswith("goal")

#     #     if is_goal:
#     #         html += f"<h2 style='margin-top: 2em; color: #9333ea;'>🟣 {top_node['round']}</h2>"
#     #     html += render_node(top_node)

#     # Summary section at the bottom
#     html += """
#         <details>
#             <summary>📝 Discussion Summary</summary>
#             <ul>
#         """
#     for line in summary_lines:
#         html += f"<li>{line}</li>\n"
#     html += "</ul></details></div>"


#     html += f"""
#         <div class="extra-meta">

#         <details open>
#         <summary>💻 CLI Command</summary>
#         <div style="background-color: #1e293b; border-radius: 6px; padding: 0.5em 0.75em; margin-bottom: 1em;">
#             <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25em;">
#             <span style="color: #f1f5f9; font-size: 0.9em;">Copy this command:</span>
#             <button onclick="copyToClipboard('cli-command')" style="background-color: #334155; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer;">📋 Copy</button>
#             </div>
#             <pre style="margin: 0;"><code id="cli-command" style="color: #f1f5f9;">{state['cli_command']}</code></pre>
#         </div>
#         </details>

#         <details>
#         <summary>📜 Run Log</summary>
#         <pre><code>{chr(10).join(state['runtime_log'])}</code></pre>
#         </details>

#         </div>

#         <script>
#         function copyToClipboard(id) {{
#             const text = document.getElementById(id).innerText;
#             const button = event.target;

#             navigator.clipboard.writeText(text).then(() => {{
#             const originalText = button.innerText;
#             button.innerText = "✅ Copied";
#             button.disabled = true;

#             setTimeout(() => {{
#                 button.innerText = originalText;
#                 button.disabled = false;
#             }}, 2000);
#             }}).catch(err => {{
#             alert("Failed to copy: " + err);
#             }});
#         }}
#         </script>

#         """


#     html += "</body></html>"
#     return html


# -----------------------------
# Function: Engagement Summary
# -----------------------------
def summarize_engagement(conversation, personas, total_rounds):
    per_round = defaultdict(set)
    per_persona = defaultdict(int)

    for msg in conversation:
        per_round[msg["round"]].add(msg["persona"])
        per_persona[msg["persona"]] += 1

    # Use safe sort for rounds with int + str
    round_summary = [
        f"{'Round ' + str(rnd) if isinstance(rnd, int) else rnd}: {len(personas)} responded"
        for rnd, personas in sorted(per_round.items(), key=lambda x: (0, x[0]) if isinstance(x[0], int) else (1, str(x[0])))
    ]

    # Correctly summarize by persona
    engagement_lookup = {p["name"]: p.get("engagement", 0.7) for p in personas}

    persona_summary = [
        f"{persona}: {count} response{'s' if count != 1 else ''} "
        f"(engagement: {engagement_lookup.get(persona, 0.7):.0%}, actual: {count / total_rounds:.0%})"
        for persona, count in per_persona.items()
    ]

    return round_summary, persona_summary


# -----------------------------
# Function: Format JSON tree Pretty
# -----------------------------
def format_json_tree_pretty(messages, level=0):
    tree = ""
    indent = "  " * level
    for msg in messages:
        tree += f"{indent}- {msg['persona']} (Round {msg['round']}): {msg['text'][:60]}...\n"
        if msg.get("children"):
            tree += format_json_tree_pretty(msg["children"], level + 1)
    return tree

# -----------------------------
# different goals for the last round
# (optional, consensus, summary, rebuttal, reflection)
# -----------------------------
def build_goal_prompt(goal_type, state):
    goal_type = goal_type.lower()
    base = "Based on the entire conversation so far, "

    if goal_type == "consensus":
        return (
            base +
            "work together to identify any shared agreements. "
            "If a consensus cannot be reached, explain the key points of disagreement and why."
        )

    elif goal_type == "summary":
        return (
            base +
            "summarize your own perspective in 2–3 sentences. "
            "Highlight what you found most important or insightful."
        )

    elif goal_type == "rebuttal":
        return (
            base +
            "critically respond to the most discussed thread. "
            "Present counterpoints or areas you believe were overlooked."
        )

    elif goal_type == "reflection":
        return (
            base +
            "reflect on how your point of view may have changed over the course of the discussion. "
            "What influenced your thinking the most?"
        )

    elif goal_type == "closing":
        return (
            base +
            "offer any final thoughts, questions, or follow-up ideas you want to share."
        )

    else:  # fallback or 'optional'
        return (
            base +
            "you may respond with any final comment or choose to sit out."
        )

# -----------------------------
# All the conversation history
# in a single string for Goal Round
# -----------------------------
def flatten_conversation_history_with_threads(state):
    def render_node(node, depth=0):
        indent = "  " * depth
        label = f"{node['persona']} (Round {node['round']})"
        text = node["text"].strip()
        return f"{indent}- {label}:\n{indent}  {text}"

    id_to_msg = {msg["id"]: msg for msg in state["conversationHistory"]}
    parent_to_children = defaultdict(list)

    for msg in state["conversationHistory"]:
        parent_to_children[msg.get("parentId")].append(msg)

    def walk_thread(parent_id=None, depth=0):
        lines = []
        for msg in parent_to_children.get(parent_id, []):
            lines.append(render_node(msg, depth))
            lines.extend(walk_thread(msg["id"], depth + 1))
        return lines

    return "\n".join(walk_thread())



# -----------------------------
# CLI Entrypoint
# -----------------------------
@click.command()
@click.option('--prompt', required=True, help='The central discussion prompt')
@click.option('--rounds', default=3, help='Number of conversation rounds')
@click.option('--personas-file', required=True, type=click.Path(exists=True), help='Path to a JSON file containing persona definitions')
@click.option('--save-to', default=None, help='Optional filename to save the final output')
@click.option('--output', default='markdown', type=click.Choice(['markdown', 'json', 'html', 'tree']), help='Output format')
@click.option('--goal-round', default='optional', type=click.Choice(['optional', 'consensus', 'summary', 'rebuttal', 'reflection']),
              help='Type of final round behavior (optional, consensus, summary, etc.)')

def run_cli(prompt, rounds, personas_file, output, save_to, goal_round):
    schema = load_persona_schema()
    client = get_openai_client()
    with open(personas_file, 'r', encoding='utf-8') as f:
        personas = json.load(f)
    parsed_personas = parse_personas(personas, schema)

    parsed_personas = enrich_personas_with_file_references(parsed_personas)

    state = initialize_state(prompt, rounds, parsed_personas)

    state["generatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cli_command = f"python main.py --prompt \"{prompt}\" --rounds {rounds} --personas-file '{personas_file}' --output {output}"

    if save_to:
        cli_command += f" --save-to \"{save_to}\""
    state["cli_command"] = cli_command

    run_conversation(state, client, goal_round)
    thread_tree = build_thread_tree(state["conversationHistory"])

    if output == 'markdown':
        result = f"## Discussion: {state['prompt']}\n\n"
        result += format_markdown_from_tree(thread_tree)
    elif output == 'json':
        result = json.dumps(thread_tree, indent=2)
    elif output == 'html':
        round_summary, persona_summary = summarize_engagement(
            state["conversationHistory"], 
            state["personas"],
            state["rounds"])
        summary_lines = round_summary + persona_summary

        # NEW calculations for top bar
        max_possible = state["rounds"] * len(state["personas"])
        actual_total = len(state["conversationHistory"])
        engagement_score = actual_total / max_possible if max_possible else 0
        total_comments = actual_total

        result = generate_html_with_styles(
            tree=thread_tree,
            title=state["prompt"],
            timestamp=state["generatedAt"],
            summary_lines=summary_lines,
            persona_colors=state["personaColors"],
            engagement_score=engagement_score,
            total_comments=total_comments,
            state=state
        )
    elif output == 'tree':
        result = format_json_tree_pretty(thread_tree)
    else:
        result = "[ERROR] Unsupported output format."

    print(result)

    if save_to:
        with open(save_to, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"[bold green]Output saved to:[/bold green] {save_to}")



# -----------------------------
# Run
# -----------------------------
if __name__ == '__main__':
    run_cli()
