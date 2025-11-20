# vriksha_chaya_main.py

import os
import asyncio
from datetime import datetime

from github import Github, Auth
from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

# --- ENVIRONMENT VARIABLES ---
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

REPO_NAME = "AnkanMoh/The-Vriksha-Chaya"
MIN_WORDS = 1000
APP_NAME = "Vriksha-Chaya-App"

STORY_BIBLE = """
Genre: Indian Folk Horror / Thriller.
Entity: 'The Vriksha-Pishach' (The Tree Demon). Tall, faceless, limbs like banyan roots.
Mechanic: Summoned by a mantra at 6 PM (Twilight).
The Cost: "Prana-Vinimaya" (Life Exchange). To survive the summoning, a sacrifice must be made within 24 hours.
Setting: Starts in a modern engineering college (NIT Trichy architecture), moves to a haunted village in Odisha.
Tone: Dark, psychological, gritty. No bollywood masala.
"""

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503],
)

# --- TOOLS ---

def publish_chapter_to_github(chapter_title: str, content: str, chapter_number: int):
    from github import Github, Auth
    from github.GithubException import GithubException

    try:
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = g.get_repo(REPO_NAME)

        safe_title = chapter_title.replace(" ", "_").replace(":", "")
        file_path = f"Chapter_{chapter_number:02d}_{safe_title}.md"
        commit_message = f"The Pishach writes Chapter {chapter_number}"

        full_content = (
            f"# {chapter_title}\n\n"
            f"*Published: {datetime.now()}*\n\n"
            f"---\n\n"
            f"{content}"
        )

        repo.create_file(file_path, commit_message, full_content)
        return f"✅ Published {file_path} successfully!"
    except GithubException as e:
        return f"❌ GitHub error ({e.status}): {e.data}"
    except Exception as e:
        return f"❌ Failed to publish: {str(e)}"

github_tool = FunctionTool(publish_chapter_to_github)

def exit_loop():
    return "Story Approved."

exit_loop_tool = FunctionTool(exit_loop)

# --- AGENTS (same as updated Cell 5) ---

writer_agent = Agent(
    name="HorrorWriter",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=f"""
You are a master Indian folk horror novelist.

{STORY_BIBLE}

Your job:
- Continue building a long-form horror novel one chapter at a time,
  based on the user's outline and the existing lore.

STYLE & TONE:
- Extremely atmospheric, slow-burn dread.
- Mix psychological horror with folk ritual horror.
- Use vivid sensory details: sounds (whispers, creaks), smells (damp soil, incense, rot),
  textures (bark, blood, coarse jute), temperature (humid heat, cold drafts), and body sensations
  (goosebumps, tight chest, nausea, trembling hands).
- Focus on internal fear and guilt as much as external scares.
- Avoid cheap jump scares and Bollywood-style melodrama.

STRUCTURE:
- Minimum words: {MIN_WORDS}.
- First 2–3 paragraphs: normalcy with subtle wrongness.
- Middle: escalating uncanny events + slow revelation of the curse.
- Final 2–3 paragraphs: high tension, with a concrete, visual horror moment.
- End on a sharp cliffhanger.

RULES:
- Show, don’t tell.
- No comedy relief, no cringe romance, no filmi dialogue.
""",
    output_key="draft_story",
)

critic_agent = Agent(
    name="Critic",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""
Review the draft: {draft_story}

If excellent (8/10+), reply ONLY:
APPROVED

Otherwise, give 3–5 very short bullet points of what to fix.
""",
    output_key="critique",
)

refiner_agent = Agent(
    name="Refiner",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""
Draft: {draft_story}
Critique: {critique}

If Critique == "APPROVED", call `exit_loop` and return the draft.

Else, rewrite the draft to fix all critique points while preserving
the characters, setting, and core horror beats.
""",
    tools=[exit_loop_tool],
    output_key="draft_story",
)

publisher_agent = Agent(
    name="Publisher",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""
The story is ready: {draft_story}

1. Create a terrifying, atmospheric title.
2. Call `publish_chapter_to_github` with:
   - chapter_title: your title
   - content: draft_story
   - chapter_number: use `chapter_num` from session state if present, else 1.
""",
    tools=[github_tool],
)

refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=3,
)

story_pipeline = SequentialAgent(
    name="NovelPipeline",
    sub_agents=[writer_agent, refinement_loop, publisher_agent],
)

# --- RUN HELPERS ---

async def run_story_cycle(runner: InMemoryRunner, chapter_num: int, outline_text: str):
    USER_ID = "cron_user"

    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=USER_ID,
    )
    session_id = session.id
    session.state["chapter_num"] = chapter_num

    prompt_text = f"Write Chapter {chapter_num}. Outline: {outline_text}"
    message_obj = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)],
    )

    for event in runner.run(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message_obj,
    ):
        pass  # we don't need to print in cron

async def main():
    runner = InMemoryRunner(agent=story_pipeline, app_name=APP_NAME)

    # simple example: chapter number = days since a fixed start date
    start_date = datetime(2025, 11, 20).date()
    today = datetime.utcnow().date()
    chapter_num = (today - start_date).days + 1
    if chapter_num < 1:
        chapter_num = 1

    outline = """
    Continue the main story of Arjun and the Vriksha-Pishach.
    Push the stak
