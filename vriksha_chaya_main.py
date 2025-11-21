import os
import asyncio
from datetime import datetime
import re

from github import Github, Auth
from github.GithubException import GithubException

from google.genai import types
from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool


GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

REPO_NAME = "AnkanMoh/The-Vriksha-Chaya"
MIN_WORDS = 1000
APP_NAME = "Vriksha-Chaya-App"

STORY_BIBLE = """
Genre: Indian Folk Horror / Psychological Thriller.

Central Entity:
- The Vriksha-Pishach: a faceless, banyan-root-limbed tree demon.
- It is tied to an old banyan and can extend itself through roots, shadows, and reflections.

Summoning Mechanic:
- A cursed mantra spoken exactly at twilight (around 6 PM) calls its attention.
- Once summoned, it does not simply appear; it seeps slowly into the edges of reality.

The Cost – Prana-Vinimaya (Life Exchange):
- A life must be exchanged within 24 hours of the summoning.
- If the summoner does not sacrifice another, the curse begins consuming them and those around them.

Setting:
- Starts in NIT Trichy's engineering hostels and library stacks.
- Expands to a haunted village in Odisha, with old temples, abandoned houses, and banyan groves.

Tone:
- Dark, grounded, slow-burn dread.
- Emphasis on psychological fear, guilt, and superstition, not jump-scare comedy.
- No Bollywood-style masala or cringe romance.
"""

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503],
)



def get_story_context_from_github(max_chapters: int = 3):
    """
    Reads existing Chapter_XX_*.md files from the repo, finds the highest chapter
    number, and returns:
        - next_chapter_num (int)
        - story_so_far (str with the last `max_chapters` chapters)
    If no chapters exist, returns (1, "").
    """
    g = Github(auth=Auth.Token(GITHUB_TOKEN))
    repo = g.get_repo(REPO_NAME)

    contents = repo.get_contents("")  
    chapter_files = []

    for file in contents:
        if file.type == "file" and file.name.startswith("Chapter_") and file.name.endswith(".md"):
            match = re.match(r"Chapter_(\d+)_", file.name)
            if match:
                chapter_num = int(match.group(1))
                chapter_files.append((chapter_num, file))

    if not chapter_files:
        return 1, ""

    chapter_files.sort(key=lambda x: x[0])
    last_chapter_num = chapter_files[-1][0]

    recent = chapter_files[-max_chapters:]
    story_parts = []

    for num, file in recent:
        try:
            content = file.decoded_content.decode("utf-8", errors="ignore")
        except Exception:
            content = ""
        story_parts.append(f"=== Chapter {num}: {file.name} ===\n{content}\n")

    story_so_far = "\n\n".join(story_parts)

    return last_chapter_num + 1, story_so_far


def publish_chapter_to_github(chapter_title: str, content: str, chapter_number: int):
    """
    Publishes the finished chapter to the GitHub repository as a Markdown file.

    The file name format is:
        Chapter_XX_<Title>.md
    """
    try:
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = g.get_repo(REPO_NAME)

        safe_title = chapter_title.replace(" ", "_").replace(":", "").replace("/", "_")
        file_path = f"Chapter_{chapter_number:02d}_{safe_title}.md"
        commit_message = f"The Vriksha-Pishach writes Chapter {chapter_number}"

        full_content = (
            f"# {chapter_title}\n\n"
            f"*Published: {datetime.utcnow().isoformat()} UTC*\n\n"
            f"---\n\n"
            f"{content}"
        )

        repo.create_file(file_path, commit_message, full_content)
        return f"Published {file_path} successfully."
    except GithubException as e:
        return f"GitHub error ({e.status}): {e.data}"
    except Exception as e:
        return f"Failed to publish chapter: {str(e)}"


github_tool = FunctionTool(publish_chapter_to_github)


def exit_loop():
    """Simple signal to indicate that refinement can stop."""
    return "Story Approved."


exit_loop_tool = FunctionTool(exit_loop)


writer_agent = Agent(
    name="HorrorWriter",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=(
        "You are a master Indian folk-horror novelist.\n\n"
        f"{STORY_BIBLE}\n\n"
        "You are writing a long-form novel one chapter at a time.\n"
        "Every time you are called, you must continue the story from where it last left off.\n\n"
        "Style and tone:\n"
        "- Extremely atmospheric, slow-burning dread.\n"
        "- Use vivid sensory details: sounds, smells, textures, temperature, and body sensations.\n"
        "- Combine psychological horror (guilt, paranoia, memory) with ritual folk horror.\n"
        "- Avoid comedy, meta-humour, or filmi melodrama.\n\n"
        "Chapter requirements:\n"
        f"- Minimum length: {MIN_WORDS} words.\n"
        "- The first few paragraphs should feel grounded and almost normal, with something slightly off.\n"
        "- The middle should escalate tension and reveal or hint at deeper aspects of the curse.\n"
        "- The final paragraphs must deliver a strong, visual, memorable cliffhanger.\n\n"
        "You will receive:\n"
        "- Recent chapters as context\n"
        "- A high-level outline for what this chapter should do\n\n"
        "Your job is to write the full next chapter, maintaining continuity with previous events, "
        "characters, and lore. Do NOT restart the story or reintroduce the premise as if it is Chapter 1."
    ),
    output_key="draft_story",
)

critic_agent = Agent(
    name="Critic",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=(
        "Review the draft chapter provided in {draft_story}.\n\n"
        "Evaluate:\n"
        "- Does it maintain continuity with earlier chapters (if context suggests ongoing story)?\n"
        "- Is the horror tone consistent, atmospheric, and rooted in Indian folk-horror?\n"
        "- Is the pacing tight (no long, flat sections without tension)?\n"
        "- Does it end on a strong, visual cliffhanger that makes sense in context?\n\n"
        "If the chapter is excellent (8/10 or better) and ready to publish, reply with exactly:\n"
        "APPROVED\n\n"
        "Otherwise, reply with 3–5 very short bullet points describing what should be improved.\n"
    ),
    output_key="critique",
)

refiner_agent = Agent(
    name="Refiner",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=(
        "You are refining a horror chapter.\n\n"
        "Draft:\n"
        "{draft_story}\n\n"
        "Critique:\n"
        "{critique}\n\n"
        "If the critique is exactly the single word:\n"
        "APPROVED\n\n"
        "then call the `exit_loop` tool and return the original draft unchanged.\n\n"
        "Otherwise, rewrite the draft to address all critique points while preserving:\n"
        "- The core events\n"
        "- The characters\n"
        "- The existing lore and continuity\n"
        "- The general shape of the cliffhanger (you may sharpen it)\n\n"
        "Your output should be a complete, polished chapter suitable for direct publishing."
    ),
    tools=[exit_loop_tool],
    output_key="draft_story",
)

publisher_agent = Agent(
    name="Publisher",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=(
        "The final, refined horror chapter is ready in {draft_story}.\n\n"
        "Your tasks:\n"
        "1. Create a short, atmospheric, horror-appropriate title for this chapter.\n"
        "2. Call the `publish_chapter_to_github` tool with:\n"
        "   - chapter_title: the title you just created\n"
        "   - content: the full chapter text from draft_story\n"
        "   - chapter_number: the chapter number that has been provided in the overall context "
        "(this run is specifically for that chapter).\n\n"
        "Do not include extra commentary; let the tool handle the publishing result."
    ),
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

async def run_story_cycle(
    runner: InMemoryRunner,
    chapter_num: int,
    outline_text: str,
    story_so_far: str,
):
    """
    Runs one full cycle: writer -> critic/refiner loop -> publisher,
    with continuity-aware context and a known chapter number.
    """
    user_id = "vriksha_chaya_cron_user"

    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
    )
    session_id = session.id

    session.state["chapter_num"] = chapter_num

    if story_so_far.strip():
        context_block = (
            "Recent chapters from the novel so far:\n"
            f"{story_so_far}\n\n"
            "You must continue directly from these events. "
            "Assume the reader has read all previous chapters."
        )
    else:
        context_block = (
            "There are no previous chapters yet. This will be Chapter 1. "
            "You are establishing the world, the curse, and the first incident."
        )

    prompt_text = (
        "You are continuing an ongoing Indian folk-horror novel.\n\n"
        f"{context_block}\n\n"
        f"This run is for Chapter {chapter_num}.\n\n"
        "High-level direction for this chapter:\n"
        f"{outline_text}\n\n"
        "Remember:\n"
        "- Do not restart the story from the beginning.\n"
        "- Do not re-explain the premise as if the reader is new.\n"
        "- Maintain continuity of characters, locations, and events.\n"
    )

    message_obj = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)],
    )

   
    for _event in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=message_obj,
    ):
        pass


async def main():
    """
    Entry point for the daily run.
    1. Looks at the repo to determine the next chapter number and recent context.
    2. Builds a high-level outline for the next chapter.
    3. Runs the full story pipeline once.
    """
    runner = InMemoryRunner(agent=story_pipeline, app_name=APP_NAME)

    next_chapter_num, story_so_far = get_story_context_from_github(max_chapters=3)

    outline = (
        "Continue directly from the last published chapter. Resolve or escalate any "
        "immediate cliffhanger, push the stakes one level higher, and introduce one new "
        "reveal about either the Vriksha-Pishach, the Prana-Vinimaya curse, or the deeper "
        "history connecting NIT Trichy and the Odisha village. Keep the tone dark, "
        "psychological, and grounded in Indian folk horror, and end on a fresh, strong "
        "cliffhanger."
    )

    await run_story_cycle(
        runner=runner,
        chapter_num=next_chapter_num,
        outline_text=outline,
        story_so_far=story_so_far,
    )


if __name__ == "__main__":
    asyncio.run(main())
