# Vriksha-Chaya

### Automated Daily Indian Folk-Horror Novel Generator

**Vriksha-Chaya** is an autonomous long-form horror-writing system that generates and publishes a new chapter of an Indian folk-horror novel every day at 9:00 AM IST. The project combines Google’s Gemini model, Google ADK multi-agent workflows, Python, and GitHub Actions to produce and release a continuous, serialized narrative.

The system is fully automated: it writes, critiques, refines, titles, and publishes each chapter to this repository without manual intervention.

---

## Project Concept

At the centre of the narrative is **The Vriksha-Pishach**, a banyan-root-limbed entity drawn from Indian folk-horror traditions. A cursed mantra triggers its attention, and the story progresses through psychological dread, supernatural consequences, and a deepening mythology. The setting moves from the familiar world of NIT Trichy’s engineering hostels to isolated rural Odisha, combining realism with folklore.

The project aims to explore how autonomous AI systems can sustain long-form, stylistically consistent storytelling while maintaining tension, coherence, and narrative escalation.

---

## How the System Works

### 1. Scheduled Execution

A GitHub Actions workflow triggers a Python script once every 24 hours (at 9:00 AM IST). This ensures the novel grows by one chapter each day.

### 2. Multi-Agent Story Generation (Google ADK)

The pipeline uses an agent-based workflow:

1. **Writer Agent**
   Generates a long chapter (minimum 1,000 words) using atmospheric horror, psychological tension, sensory detail, and a structured slow-burn style.

2. **Critic Agent**
   Assesses the chapter for pacing, tone, narrative escalation and cliffhanger strength. It returns either “APPROVED” or a set of short improvement points.

3. **Refiner Agent**
   If not approved, the refiner rewrites the chapter according to the critique.
   This loop runs for up to three iterations.

4. **Publisher Agent**
   Creates an appropriate title and publishes the final chapter as a Markdown file to the repository using the GitHub API.

### 3. Publishing

Each chapter is committed as a new file:

```
Chapter_XX_<Title>.md
```

The repository becomes the continuously updated novel archive.

---

## Repository Structure

```
The-Vriksha-Chaya/
│
├── vriksha_chaya_main.py        # Main executable script run by GitHub Actions
├── .github/
│   └── workflows/
│       └── vriksha_chaya.yml    # Scheduler and execution workflow
│
├── Chapter_01_<Title>.md        # Auto-generated chapter files (daily)
├── Chapter_02_<Title>.md
└── ...
```

---

## Technology Stack

* **Google Gemini 2.5 Flash Lite** – Core generation model
* **Google ADK (Agents Framework)** – Writer/Critic/Refiner/Publisher workflow
* **Python** – Agent orchestration and GitHub publishing
* **PyGithub** – GitHub API wrapper
* **GitHub Actions** – Daily automated execution
* **Markdown file publishing** – Each chapter stored as versioned content

---

## Daily Automation (GitHub Actions)

The workflow file `.github/workflows/vriksha_chaya.yml`:

* Runs once a day at 9:00 AM IST (scheduled through UTC cron)
* Installs dependencies
* Executes the main script
* Publishes the generated chapter

Secrets used by the workflow:

* `GOOGLE_API_KEY` – Gemini API key
* `VRIKSHA_GH_TOKEN` – GitHub PAT with contents:write permission

---

## Goals and Intent

The project explores:

* Whether an AI system can sustain a cohesive, evolving long-form narrative
* How multi-agent refinement loops improve literary consistency
* How folklore elements can be encoded and maintained across multi-chapter storytelling
* How automated creative pipelines can produce serialized writing without human intervention

---

## Extending the Project

Potential extensions include:

* Adding memory retention between chapters for long-term continuity
* Generating weekly summaries
* Adding character arcs or branching storylines
* Incorporating reader-driven directions
* Publishing to additional platforms (website, RSS feed, etc.)
* Maintaining a mythology index as the novel grows

---

## Status

The system is active, and a new chapter is automatically added each day.

If you'd like, I can also generate:

* A versioned changelog
* A FAQ section
* A contribution guide
* A visual architecture diagram
* A website page for public reading of chapters


