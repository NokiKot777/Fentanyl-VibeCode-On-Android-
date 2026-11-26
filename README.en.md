# fentanyl BETA — the complete guide from A to Z

🇷🇺 **Русская версия: [README.md](README.md)** · 🇬🇧 English version — this file.

A console AI assistant for programming (a replacement for Codex / Claude Code).
Creator: **SlimeCat** · made with **Claude** (Anthropic).

> Version **BETA**: bugs are possible. Tested on Linux with Python 3.12. Android (Termux), Windows and macOS
> were not specifically tested — if something is off, see “If something does not work”.

---

## 1. What it can do

- Chat with an AI in the terminal; the reply is typed out as it arrives, code is shown in frames.
- **Agent**: the AI proposes creating/editing files and running commands; you confirm with `y` / `n` / `a`.
- Works **in the folder you choose** (not the disk root), with a projects menu.
- **Auto-check**: after the AI finishes, the program runs the project, reads console errors and either warns you or fixes them itself.
- **Preview window**: program output (Python / Node / sh) or an HTML page in the browser.
- Works with cloud AIs (Anthropic, OpenAI, OpenRouter) and local ones (Ollama, LM Studio, built-in GGUF).
- **Two interface languages: English and Russian** (chosen on first launch, changed any time with `/lang`).
- Your name, a time-of-day greeting, themes, animations, a cat, settings reset.

---

## 2. What to download and install

### Required
| What | Why | Where to get it |
|---|---|---|
| **Python 3.8 or newer** (tested on 3.12) | to run the program | python.org (Windows/macOS), `pkg install python` (Termux), `sudo apt install python3` (Linux) |
| **This `fentanyl` folder** | the program itself | unzip it anywhere |

Nothing else is needed: the program uses only the Python standard library (no `pip install`).

### You need one AI option (pick any)
| Option | You need | Internet |
|---|---|---|
| **Anthropic / OpenAI / OpenRouter** | an API key | required |
| **Ollama** | the Ollama app + a downloaded model | only to download |
| **LM Studio** | the LM Studio app + a model | only to download |
| **GGUF (built-in)** | `llama-server` (from llama.cpp) + a `.gguf` model file | only to download |

### Optional
| What | Why |
|---|---|
| **Node.js** | checking and running `.js` projects |
| **Git** | the `/git` command |
| **Termux:API** (app) + `pkg install termux-api` | notifications and battery saver on Android |

---

## 3. Installation by platform

### Android (Termux)
```bash
pkg update
pkg install python
# unzip fentanyl.zip (for example into ~/fentanyl) and go to the folder:
cd ~/fentanyl
python fentanyl.py
```
To run a local model on the phone, see section 5, “GGUF”.

### Windows
1. Install Python from python.org (tick **Add Python to PATH**).
2. Unzip the archive.
3. Open **Windows Terminal** (or PowerShell) in the `fentanyl` folder and run:
```powershell
python fentanyl.py
```
The old `cmd` window may render colors and frames badly — prefer Windows Terminal.

### macOS / Linux
```bash
cd fentanyl
python3 fentanyl.py
```

---

## 4. First launch — step by step

1. **Boot screen** with the logo (~3 seconds), then it disappears.
2. **Choose your language** (the very first screen, in English): `1` — English, `2` — Русский. The whole interface then uses it. You can change it any time with `/lang`.
3. The header with the logo in the corner appears.
4. **AI connection** (first launch only): pick a provider number (section 5).
5. **What should I call you?** — type a name or nickname. Enter — skip.
6. **Project folder** — choose where the AI will work:
   - `Enter` — the first line (the last used one or the current folder);
   - a number — one of the listed items;
   - `b` — browse folders;
   - or just type a path.
7. A **greeting** with your name (animated), and you can type your request.

You can also pass the folder at launch: `python fentanyl.py path/to/project`.

---

## 5. Connecting an AI

You can change it any time with `/setup`. Settings are stored in `~/.fentanyl.json`.

### Anthropic (Claude)
1. Sign up at console.anthropic.com and create an API key.
2. In `/setup` choose **1**, paste the key (it is not echoed), keep the default address and model (Enter).

### OpenAI
1. Key: platform.openai.com → API keys.
2. In `/setup` choose **2**.

### OpenRouter (many models with one key)
1. Key: openrouter.ai → Keys.
2. In `/setup` choose **3**; give the model as `vendor/model`.

### Ollama (local, free)
1. Install Ollama from ollama.com.
2. Download a model: `ollama pull qwen2.5-coder`.
3. In `/setup` choose **4**. Default address: `http://127.0.0.1:11434/v1`.

### LM Studio (local, with a window)
1. Install LM Studio, download a model, start the **Local Server** (port 1234).
2. In `/setup` choose **5**.

### GGUF (built-in, the program starts the server itself)
1. You need **`llama-server`** from the llama.cpp project:
   - Termux: `pkg install llama-cpp`;
   - other systems: download a ready build of llama.cpp from github.com/ggml-org/llama.cpp (Releases) or build it yourself, and put `llama-server` on your `PATH`.
2. You need a `.gguf` model file. The easiest way is inside the program: the **`/models`** command → pick a model from the catalog (Qwen2.5-Coder 0.5B / 1.5B / 3B / 7B, Llama 3.2 1B / 3B) — it downloads into `~/models`. Or put your own `.gguf` into `~/models` or your downloads folder, or download by link: `/download <link>`.
3. In `/setup` choose **6** and a model number (or a file path). The server then starts and stops by itself.

Hardware guide: 0.5B–1.5B — weak phones; 3B — from 6 GB of memory; 7B — from 8 GB.

### AI on a computer, program on a phone
On a phone, `127.0.0.1` is the phone itself. Use your computer's Wi-Fi IP instead (for example `http://192.168.1.50:11434/v1`). On the computer, the server must accept connections from the network (for Ollama set `OLLAMA_HOST=0.0.0.0`; for LM Studio enable access from the local network).

---

## 6. How to work

**Just type in plain text.** Examples:
```
create a business-card website in HTML and CSS
add error handling to @main.py
explain what @src does
```

- **`@path`** attaches a file or folder to the message. You can attach several. Paths are relative to the project folder (absolute paths work too).
- A line ending with `\` continues the input. Many lines at once: `/paste` (finish with a line `END`).
- **Ctrl+C during a reply** stops it. **Ctrl+C on an empty prompt** shows a warning; a second press within 2 seconds quits.

### Agent and confirmations
The AI proposes actions, you answer:
- `y` — yes, `n` — no, `a` — always (until the end of the session).
- Before an edit, a diff is shown (what was → what will be).
- **`/undo`** reverts the last file edit.
- `/auto edit` and `/auto run` — stop asking for confirmation (`/auto off` brings it back). Dangerous commands (for example deletion) **always** ask.
- `/agent off` — plain chat without actions.
- Manual commands: `/run command` or `!command`, `/ls`, `/grep`, `/read file`, `/git`.

### Comments (`/comments on|off`, on by default)
Before acting, the AI briefly says what it is about to do; for a new project — a plan with the file list, then it creates the files. Short comments appear in the code. Before execution, the list of actions is shown.

### Reasoning (`/think on|off`, off by default)
On — the AI “thinks aloud”, shown in gray. Off — reasoning is hidden (also for models that reason on their own).

---

## 7. Project folder and projects menu

The AI works only in the chosen folder: files are created and edited there, commands run there.

| Command | What it does |
|---|---|
| `/pwd` | which folder the AI is working in |
| `/cd` | browse folders (number — enter, `0` — up, `n name` — create, Enter — pick) |
| `/cd path` | go to a folder; `/cd -` — go back |
| `/projects` (or `/p`) | **projects menu**: up to 9 recent ones; number — open, `d 2` — remove from the list, `a` — add the current one, `b` — browse |

When you change the folder, the program offers to start a new chat. On the disk root and in the home folder it asks for confirmation.

To give the AI project rules, create a `FENTANYL.md` (or `CLAUDE.md`, or `AGENTS.md`) file in the folder — its beginning (up to 8000 characters) is added to the instructions.

---

## 8. Auto-check and preview

### Auto-check (`/check off|warn|fix`)
After the AI creates or changes files, the program runs the project itself and reads the console.

| Mode | What happens on an error |
|---|---|
| **warn** (default) | shows the error and asks “Ask the AI to fix it?” (Enter = yes) |
| **fix** | sends the error to the AI by itself; it fixes it and the project is re-checked (up to 2 attempts) |
| **off** | runs nothing |

What is checked: Python and Node (syntax + running), shell scripts, HTML (broken links to files).
Not treated as errors: the program runs longer than 8 seconds (a server/game — it is stopped), waits for keyboard input, or needs a graphical screen.

**Safety:** code runs only with your consent — the first time it asks `y` (once), `a` (always) or `n`. The running program does not get environment variables containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD` (for example your API key). Run time and output size are limited.

### Preview window (`/preview`)
- `/preview` — show the project now; `/preview file` — a specific file; `/preview off|on` — turn the automatic preview off/on.
- Python / Node / sh — a frame with the program's output and the result (✓ or ✗, time).
- HTML — opens in the browser through a local server (`127.0.0.1` only; hidden files such as `.env` are not served). Press Enter to close. If the browser did not open by itself (for example in Termux), open the shown address manually.

---

## 9. Look and small things

| Command | What it does |
|---|---|
| `/lang [en\|ru]` | **interface language** (no argument — a choice menu) |
| `/theme [name]` | color theme: `mint`, `sunset`, `ocean`, `grape`, `mono` |
| `/anim on\|off` | animations (or start with `--no-anim`) |
| `/clear` | clear the screen (the chat is kept) |
| `/name [name\|-]` | change your name, `-` removes it |
| `/idle <sec>` | when the cat falls asleep (0 — off), `/cat` — show it |
| `/notify on\|off` | notification for long replies |
| `/battery on\|off` | battery saver (Termux:API) |
| `/credits` | about the program |
| `/reset` | **reset settings**: 1 — look and modes (language, name, theme, projects…), 2 — everything, including key and model. After a reset it asks for the language and name again |

---

## 10. All commands

**Chat:** `/new` · `/paste` · `/file <path>` · `@path` · `/save <path>` (save the last code block) · `/compact` (compress history) · `/ctx [n]`
**Agent:** `/agent on|off` · `/auto edit|run|off` · `/undo` · `/run <cmd>` · `!cmd` · `/ls [path]` · `/grep <regex> [path]` · `/read <file> [from-to]` · `/git [diff|log|commit]`
**Project:** `/projects` · `/cd [path|-]` · `/pwd`
**Checking:** `/check off|warn|fix` · `/preview [file|on|off]`
**Sessions:** `/save-chat [name]` · `/resume [name|#|last]`
**Model:** `/models` · `/download <url>` · `/gguf [path]` · `/server [stop|restart]` · `/model <name>` · `/setup` · `/sys <text>` · `/battery`
**Look:** `/lang` · `/clear` · `/think` · `/comments` · `/theme` · `/anim` · `/idle` · `/cat` · `/notify` · `/name` · `/credits` · `/reset`
**Other:** `/help` · `/exit`

---

## 11. Launch options

| What | Why |
|---|---|
| `python fentanyl.py path` | open this project folder right away |
| `--plain` | no colors (if the terminal does not support them) |
| `--no-anim` | no animations |
| `FENTANYL_ANIM=0` | the same via an environment variable |
| `FENTANYL_IDLE=seconds` | when the cat falls asleep |
| `FENTANYL_ASK=0` | do not ask for the folder at launch (uses the last one) |

---

## 12. Where things are stored

| File / folder | What |
|---|---|
| `~/.fentanyl.json` | settings (including the **API key in plain text** — never share this file) |
| `~/.fentanyl_sessions/` | saved chats |
| `~/models/` | downloaded `.gguf` models |
| `~/.fentanyl_server.log` | log of the built-in server |
| `~/.fentanyl_catalog.json` | optional: your own models for the `/models` catalog |

To remove everything, delete these files/folders (or `/reset` → 2).

---

## 13. If something does not work

| Problem | What to do |
|---|---|
| “llama-server not found” | install llama.cpp (section 5, GGUF) or pick another option in `/setup` |
| Reply / key / address error | run `/setup` and check the key, address, model; for local ones — is the server running |
| “Connection refused” to Ollama / LM Studio | start the app and its server; on a phone use the computer's IP instead of `127.0.0.1` |
| Garbled text, broken frames | use a modern terminal (Windows Terminal, Termux, iTerm); or `--plain` |
| Lag from animations | `/anim off` |
| Terminal looks odd after a crash | type `reset` and press Enter |
| The AI only writes code instead of creating files | the model may be too weak for the agent — use a bigger one or `/agent on`; you can save code with `/save path` |
| “context almost full” | `/compact` or `/new` |
| The browser did not open for the preview | open the address from the frame manually |
| Auto-check does not run the code | agree to the question (`y` / `a`) or set `/check warn` |
| I want another language | `/lang en` or `/lang ru` |
| I want to start from scratch | `/reset` |

---

## 14. What the program consists of

```
fentanyl/
├── fentanyl.py        entry point
└── fcore/
    ├── term.py        colors, themes, frames
    ├── anim.py        logo, animations, header, greeting
    ├── render.py      printing the AI reply (word wrap, markdown)
    ├── workdir.py     folder choice, projects menu
    ├── greet.py       language, name, greetings
    ├── i18n.py        translations: tr()
    ├── lang_en.py     English interface texts
    ├── checker.py     auto-check and preview
    ├── config.py      settings and connection
    ├── api.py         requests to the AI
    ├── server.py      built-in GGUF server
    ├── models.py      model catalog and downloads
    ├── agent.py       AI actions (create/edit/run)
    ├── tools.py       files, search, diff, confirmations
    ├── session.py     context, @-files, saving chats
    ├── chat.py        conversation flow, help, status
    ├── commands.py    all /commands
    ├── cat.py         the cat
    ├── sysutil.py     notifications, battery, git
    └── app.py         input and the main loop
```
Found a bug: in a command — `commands.py`; in the AI reply — `api.py` / `render.py`; in file edits — `agent.py` / `tools.py`; in checking — `checker.py`; a wrong or missing translation — `lang_en.py`.

### Adding or fixing a translation
Interface texts are Russian in the code and are translated through `tr("Russian text")`. English versions live in `fcore/lang_en.py` as `"Russian text": "English text"`. Keep placeholders such as `{0}` and `{1}` unchanged. A text without a translation is shown in Russian.

---

## 15. Safety in short

- The AI changes files and runs commands **only after your confirmation** (except `/auto` modes and auto-check, which you turn on yourself).
- Auto-check runs code only with your consent, without your keys in the environment.
- Do not enable `/auto run` on folders with important data and do not pick the disk root as the project folder.
- Back up important projects (or use git): `/undo` reverts only edits made within the current session.

Happy coding! 🚀
