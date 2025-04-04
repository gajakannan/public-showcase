setup python


```

mkdir multiagent-convo
cd multiagent-convo

python3 -m venv .venv

# macos/linux
source .venv/bin/activate

# windows
.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt


# On macOS/Linux:
export OPENAI_API_KEY=sk-...

# On PowerShell (Windows):
$env:OPENAI_API_KEY="sk-..."


```





```bash
python main.py \
   --prompt "Which is the good front end technology to develop web applications" \
   --rounds 5 \
   --personas '[{"name": "html developer", "llm": "ChatGPT", "engagement": 0.7}, {"name": "react developer", "llm": "ChatGPT", "engagement": 0.8}, {"name": "astrojs developer", "llm": "Gemini", "engagement": 0.6}, {"name": "angular developer", "llm": "Deepseek", "engagement": 0.4}]' \
   --output html \
   --save-to "./output/discussion.html"

```

```powershell
python main.py `
   --prompt "Which is the good front end technology to develop web applications" `
   --rounds 5 `
   --personas '[{"name": "html developer", "llm": "ChatGPT", "engagement": 0.7}, {"name": "react developer", "llm": "ChatGPT", "engagement": 0.8}, {"name": "astrojs developer", "llm": "Gemini", "engagement": 0.6}, {"name": "angular developer", "llm": "Deepseek", "engagement": 0.4}]' `
   --output html `
   --save-to "./output/discussion.html"

```