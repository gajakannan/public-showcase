import json
import random
import click
from rich import print
from datetime import datetime
from collections import defaultdict
from jsonschema import validate, ValidationError
from init import get_openai_client, load_persona_schema
from persona_utils import enrich_personas_with_file_references, summarize_discussion
from exporter_html import generate_html_with_styles
from exporter_markdown import generate_markdown_from_tree
from exporter_json import generate_json_from_tree
from exporter_tree import generate_tree_from_tree
import re
from agent_log import setup_prompt_logger, log_prompt


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
def agent_reply(persona, target_text, round_num, client, prompt_logger):

    is_goal_round = str(round_num).lower().startswith("goal")
    is_decision_round = is_goal_round and "decision" in round_num.lower()

    system_prompt = f"You are a {persona['name']}."

    # print(f"[dim]{is_goal_round}, {is_decision_round}, {persona.get('round_awareness')}[/dim]")

    if is_goal_round:
        goal_label = round_num.split("-")[-1].strip().capitalize()  # e.g., "decision"
        system_prompt += f"You are now in the round labeled: Goal - {goal_label}. "
    else:
        system_prompt += "You are in a regular discussion round."

    # Add the persona's prompt
    if is_goal_round and "goal_prompt" in persona:
        system_prompt += " " + persona["goal_prompt"]
    elif not is_goal_round and "regular_prompt" in persona:
        system_prompt += " " + persona["regular_prompt"]
    else:
        system_prompt += " Provide thoughtful insights on the following:"

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
        if prompt_logger:
            # Log system and user prompts
            log_prompt(prompt_logger, persona['name'], "system", system_prompt)
            log_prompt(prompt_logger, persona['name'], "user", user_prompt)
        response = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            model=persona.get("model", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        reply = response.choices[0].message.content.strip()

        # ✅ Suggestion #2: Log the assistant reply
        if prompt_logger:
            log_prompt(prompt_logger, persona['name'], "assistant", reply)

        return reply

    except Exception as e:
        print(f"[red]Failed to get response from OpenAI for {persona['name']}[/red]")
        print(f"[dim]{str(e)}[/dim]")
        return f"[ERROR] Round {round_num}: Unable to generate reply."

# -----------------------------
# Function: Run the Conversation
# -----------------------------
def run_conversation(state, client, prompt_logger, goal_round="optional"):
    state["runtime_log"] = []

    def log_line(line):
        state["runtime_log"].append(line)
        print(line)

    while state["currentRound"] <= state["rounds"]:
        log_line(f"\n--- Round {state['currentRound']} ---")

        for persona in state["personas"]:
            supplied_engagement_rate = persona.get("engagement", 0.7)
            engagement_rate = supplied_engagement_rate
            will_reply = random.random() < engagement_rate
            if not will_reply:
                log_line(f"{persona['name']} chose to sit out this round.")
                continue

            if "resolved_qdrant_titles" in persona:
                log_line(f"[dim]{persona['name']} Qdrant matches:[/dim] {persona['resolved_qdrant_titles']}")

            target = state["prompt"] if state["currentRound"] == 1 else pick_random_message(state)
            target_text = target if isinstance(target, str) else get_thread_context(state, target)

            parent_id = None if isinstance(target, str) else target["id"]

            reply_text = agent_reply(persona, target_text, state["currentRound"], client, prompt_logger)
            message_id = f"msg-{state['currentRound']}-{persona['name']}"

            state["conversationHistory"].append({
                "id": message_id,
                "round": state["currentRound"],
                "persona": persona["name"],
                "llm": persona["llm"],
                "parentId": parent_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": reply_text,
                "rag_score": score_rag_effectiveness(reply_text, persona) 
            })

            log_line(f"{persona['name']} replied → {message_id}")

        state["currentRound"] += 1

    # Goal round handling (only once, after all normal rounds)
    if goal_round != "optional":
        log_line(f"\n[bold magenta]--- Goal Round: {goal_round.upper()} ---[/bold magenta]")

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

            goal_label = f"Goal - {goal_round.capitalize()}"
            reply_text = agent_reply(persona, target_text, goal_label, client, prompt_logger)
            # reply_text = agent_reply(persona, target_text, state["currentRound"], client, prompt_logger)
            message_id = f"msg-{state['currentRound']}-{persona['name']}"

            state["conversationHistory"].append({
                "id": message_id,
                "round": "Goal - " + goal_round,
                "persona": persona["name"],
                "llm": persona["llm"],
                "parentId": parent_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": reply_text,
                "rag_score": score_rag_effectiveness(reply_text, persona) 
            })

            log_line(f"{persona['name']} replied → {message_id}")

        state["currentRound"] += 1

# -----------------------------
# Function: Rag Effectiveness Score
# -----------------------------
def score_rag_effectiveness(reply_text, persona):
    if not persona.get("resolved_qdrant_titles"):
        return None

    score = 0.0

    # 1. Check if any Qdrant chunk titles appear in the reply
    titles = persona.get("resolved_qdrant_titles", [])
    if any(title.replace("[Qdrant match: ", "").replace("]", "") in reply_text for title in titles):
        score += 0.4

    # 2. Check for use of numbers, surcharges, JSON-like elements
    if re.search(r"\$?\d{2,4}", reply_text):  # e.g., "$500", "550"
        score += 0.2
    if "%" in reply_text or "discount" in reply_text.lower() or "surcharge" in reply_text.lower():
        score += 0.1
    if "deductible" in reply_text.lower():
        score += 0.1

    # 3. JSON block present?
    if "{" in reply_text and "}" in reply_text and "decision" in reply_text:
        score += 0.2

    return round(min(score, 1.0), 2)


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
# different goals for the last round
# (optional, consensus, summary, rebuttal, reflection, decision)
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
    elif goal_type == "decision":
        return (
            base +
            "you must now make a clear decision or recommendation based on the discussion. "
            "Be specific, concise, and explain your reasoning clearly. Avoid summarizing."
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
@click.option('--goal-round', default='optional', type=click.Choice(['optional', 'consensus', 'decision' , 'summary', 'rebuttal', 'reflection']),
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
    session_id = state["generatedAt"].replace(" ", "T").replace(":", "-")
    prompt_logger = setup_prompt_logger(session_id)


    cli_command = f"python main.py --prompt \"{prompt}\" --rounds {rounds} --personas-file '{personas_file}' --output {output}"

    if save_to:
        cli_command += f" --save-to \"{save_to}\""
    state["cli_command"] = cli_command

    run_conversation(state, client, prompt_logger ,goal_round)
    thread_tree = build_thread_tree(state["conversationHistory"])

    if output == 'markdown':
        # result = f"## Discussion: {state['prompt']}\n\n"
        # result += format_markdown_from_tree(thread_tree)
        result = generate_markdown_from_tree(thread_tree, state["prompt"])
    elif output == 'json':
        # result = json.dumps(thread_tree, indent=2)
        result = generate_json_from_tree(thread_tree)
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

        state["discussionSummary"] = summarize_discussion(
            state["conversationHistory"], client, model="gpt-4o")

        result = generate_html_with_styles(
            tree=thread_tree,
            title=state["prompt"],
            timestamp=state["generatedAt"],
            summary_lines=summary_lines,
            persona_colors=state["personaColors"],
            engagement_score=engagement_score,
            total_comments=total_comments,
            cli_command=state["cli_command"],
            runtime_log=state["runtime_log"],
            discussion_summary=state["discussionSummary"]
        )
    elif output == 'tree':
        # result = format_json_tree_pretty(thread_tree)
        result = generate_tree_from_tree(thread_tree)
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
