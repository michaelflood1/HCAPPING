#!/usr/bin/env python3
"""
Quiz Discord Bot
=================
Runs your presaved quizzes (same JSON files/format as quiz_app.py) as a
group activity in a Discord channel. Everyone in the channel answers by
clicking a reaction emoji; the bot reveals the answer after a timer and
prints everyone's score at the end.

Setup
-----
1. pip install -r requirements.txt
2. Create an application + bot at https://discord.com/developers/applications
   - Under "Bot", enable the "MESSAGE CONTENT INTENT" toggle.
   - Copy the bot token.
3. Invite the bot to your server with these permissions:
   View Channels, Send Messages, Embed Links, Add Reactions, Read Message History
4. Set the token as an environment variable and run:
     export DISCORD_BOT_TOKEN=your-token-here
     python3 bot.py

Restricting to one channel
---------------------------
By default the bot responds in any channel it can see. To lock it to a
single channel (e.g. #quizzes), set QUIZ_CHANNEL_NAME to that channel's
name (without the #) before running:
     export QUIZ_CHANNEL_NAME=quizzes
     python3 bot.py
Commands typed in any other channel are silently ignored - the bot won't
reply or explain itself there, to avoid cluttering unrelated channels.

Commands (default prefix "!")
------------------------------
  !quizlist                 - list available quizzes
  !quiz <name>               - start a quiz in the current channel (numeric order)
  !quiz <name> random         - start a quiz in random question order
  !quizstop                  - stop the quiz currently running in this channel

Quizzes live in the "quizzes/" folder next to this file.
Drop a JSON file in there, or copy one over, to make it available here too.
"""

import asyncio
import json
import os
import random

import discord
from discord.ext import commands

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Changed: quizzes folder is next to bot.py
QUIZ_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quizzes")

SECONDS_PER_QUESTION = 15 # how long people have to react before it locks in
COMMAND_PREFIX = "!"

# If set, the bot only responds in the channel with this exact name (no "#").
# Leave unset/empty to allow the bot to respond in any channel.
QUIZ_CHANNEL_NAME = os.environ.get("QUIZ_CHANNEL_NAME", "").strip().lstrip("#")

MC_EMOJIS = ["🇦", "🇧", "🇨", "🇩"]
MC_LETTERS = {"🇦": "a", "🇧": "b", "🇨": "c", "🇩": "d"}
TF_EMOJIS = {"✅": "true", "❌": "false"}

intents = discord.Intents.default()
intents.message_content = True  # required to read "!quiz ..." commands
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# channel_id -> True while a quiz is running there, so a second !quiz can't overlap
active_channels = set()


@bot.check
async def restrict_to_quiz_channel(ctx):
    """If QUIZ_CHANNEL_NAME is set, only let commands run in that channel.
    Returns False (silently, no error message) for every other channel so
    the bot doesn't clutter unrelated channels."""
    if not QUIZ_CHANNEL_NAME:
        return True
    channel_name = getattr(ctx.channel, "name", None)  # None in DMs
    return channel_name is not None and channel_name.lower() == QUIZ_CHANNEL_NAME.lower()


# ---------------------------------------------------------------------------
# Quiz loading (same JSON schema/folder as quiz_app.py)
# ---------------------------------------------------------------------------

def list_quiz_files():
    """Return {lowercased title: (filepath, title, question_count)}."""
    quizzes = {}

    print(f"[DEBUG] Looking for quizzes in: {QUIZ_DIR}")
    print(f"[DEBUG] Directory exists: {os.path.isdir(QUIZ_DIR)}")

    if not os.path.isdir(QUIZ_DIR):
        print("[DEBUG] Quiz directory does not exist!")
        return quizzes

    files = os.listdir(QUIZ_DIR)
    print(f"[DEBUG] Files found: {files}")

    for fname in sorted(files):
        if not fname.lower().endswith(".json"):
            print(f"[DEBUG] Skipping non-JSON: {fname}")
            continue

        fpath = os.path.join(QUIZ_DIR, fname)
        print(f"[DEBUG] Checking: {fpath}")

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            print(f"[DEBUG] JSON loaded successfully: {fname}")

            title = data.get("title", fname)
            questions = data.get("questions", [])

            print(
                f"[DEBUG] title={title!r}, "
                f"questions={len(questions) if isinstance(questions, list) else 'NOT A LIST'}"
            )

            if not questions:
                print(f"[DEBUG] SKIPPING {fname}: no questions")
                continue

            quizzes[title.lower()] = (fpath, title, len(questions))

        except json.JSONDecodeError as e:
            print(f"[DEBUG] INVALID JSON: {fname}: {e}")
        except OSError as e:
            print(f"[DEBUG] FILE ERROR: {fname}: {e}")

    print(f"[DEBUG] Final quizzes: {quizzes}")
    return quizzes


def load_quiz(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def find_quiz_by_name(name):
    """Case-insensitive match by title or JSON filename, with substring fallback."""
    quizzes = list_quiz_files()
    key = name.lower().strip()

    # Match the quiz title exactly
    if key in quizzes:
        return quizzes[key]

    # Match the filename exactly, e.g. "sample.json"
    for fpath, title, count in quizzes.values():
        if os.path.basename(fpath).lower() == key:
            return fpath, title, count

    # Match the filename without .json, e.g. "sample"
    if not key.endswith(".json"):
        filename_key = key + ".json"
        for fpath, title, count in quizzes.values():
            if os.path.basename(fpath).lower() == filename_key:
                return fpath, title, count

    # Fall back to a substring match against the title
    matches = [v for k, v in quizzes.items() if key in k]

    if len(matches) == 1:
        return matches[0]

    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})")
    if QUIZ_CHANNEL_NAME:
        print(f"Restricted to channel: #{QUIZ_CHANNEL_NAME}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return  # wrong channel - ignore quietly, as intended
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


@bot.command(name="quizlist")
async def quizlist(ctx):
    quizzes = list_quiz_files()
    if not quizzes:
        await ctx.send(f"No quizzes found in `{QUIZ_DIR}`. Add a JSON quiz file there first.")
        return
    lines = [f"**{title}** — {count} questions" for _, title, count in quizzes.values()]
    embed = discord.Embed(title="Available Quizzes", description="\n".join(lines), color=0x5865F2)
    embed.set_footer(text=f"Start one with {COMMAND_PREFIX}quiz <name>")
    await ctx.send(embed=embed)


@bot.command(name="quizstop")
async def quizstop(ctx):
    if ctx.channel.id in active_channels:
        active_channels.discard(ctx.channel.id)
        await ctx.send("Quiz stopped early. (It'll finish its current question first.)")
    else:
        await ctx.send("There's no quiz running in this channel.")


@bot.command(name="quiz")
async def quiz(ctx, *, args: str = ""):
    if ctx.channel.id in active_channels:
        await ctx.send("A quiz is already running in this channel. Use `!quizstop` to end it first.")
        return

    args = args.strip()
    if not args:
        await ctx.send(f"Usage: `{COMMAND_PREFIX}quiz <quiz name> [random]`. See `{COMMAND_PREFIX}quizlist` for options.")
        return

    random_order = False
    parts = args.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].lower() == "random":
        random_order = True
        name = parts[0]
    else:
        name = args

    found = find_quiz_by_name(name)
    if not found:
        await ctx.send(f"Couldn't find a quiz matching '{name}'. Try `{COMMAND_PREFIX}quizlist`.")
        return

    fpath, title, _ = found
    data = load_quiz(fpath)
    questions = list(data.get("questions", []))
    if random_order:
        random.shuffle(questions)

    active_channels.add(ctx.channel.id)
    try:
        await run_quiz(ctx.channel, title, questions)
    finally:
        active_channels.discard(ctx.channel.id)


# ---------------------------------------------------------------------------
# Quiz engine
# ---------------------------------------------------------------------------

async def run_quiz(channel, title, questions):
    await channel.send(
        f"📋 **{title}** is starting! {len(questions)} questions, "
        f"{SECONDS_PER_QUESTION}s each. React to answer — everyone can play."
    )
    await asyncio.sleep(2)

    scores = {}  # user_id -> {"name": str, "correct": int, "answered": int}

    for i, q in enumerate(questions, start=1):
        if channel.id not in active_channels:
            await channel.send("Quiz stopped.")
            return
        await ask_question(channel, i, len(questions), q, scores)
        await asyncio.sleep(1.5)

    await announce_results(channel, title, scores)


async def ask_question(channel, index, total, q, scores):
    qtype = q.get("type")
    embed = discord.Embed(
        title=f"Question {index}/{total}",
        description=q["question"],
        color=0x5865F2,
    )

    if qtype == "mc":
        choices = q.get("choices", {})
        emojis_used = []
        lines = []
        for letter, emoji in zip(["a", "b", "c", "d"], MC_EMOJIS):
            if letter in choices:
                lines.append(f"{emoji} {choices[letter]}")
                emojis_used.append(emoji)
        embed.add_field(name="Choices", value="\n".join(lines), inline=False)
    else:  # true/false
        emojis_used = list(TF_EMOJIS.keys())
        embed.add_field(name="Choices", value="✅ True      ❌ False", inline=False)

    msg = await channel.send(embed=embed)
    for emoji in emojis_used:
        await msg.add_reaction(emoji)

    answers = {}  # user_id -> (user, emoji)
    loop = asyncio.get_event_loop()
    end_time = loop.time() + SECONDS_PER_QUESTION

    def check(reaction, user):
        return (
            reaction.message.id == msg.id
            and not user.bot
            and str(reaction.emoji) in emojis_used
        )

    while True:
        remaining = end_time - loop.time()
        if remaining <= 0:
            break
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=remaining, check=check)
        except asyncio.TimeoutError:
            break
        answers[user.id] = (user, str(reaction.emoji))  # last reaction before time-up counts

    # score it
    if qtype == "mc":
        correct_answer = q.get("answer")
        correct_emoji = MC_EMOJIS[["a", "b", "c", "d"].index(correct_answer)] if correct_answer in ["a", "b", "c", "d"] else None
        correct_text = q.get("choices", {}).get(correct_answer, correct_answer)
    else:
        correct_answer = str(q.get("answer")).lower()
        correct_emoji = "✅" if correct_answer == "true" else "❌"
        correct_text = "True" if correct_answer == "true" else "False"

    correct_users = []
    for user_id, (user, emoji) in answers.items():
        record = scores.setdefault(user_id, {"name": user.display_name, "correct": 0, "answered": 0})
        record["answered"] += 1
        if emoji == correct_emoji:
            record["correct"] += 1
            correct_users.append(user.display_name)

    reveal = f"⏰ Time's up! Correct answer: **{correct_text}**"
    if correct_users:
        reveal += f"\n✅ Correct: {', '.join(correct_users)}"
    else:
        reveal += "\nNobody got it this time."
    await channel.send(reveal)


async def announce_results(channel, title, scores):
    if not scores:
        await channel.send(f"**{title}** finished — nobody answered any questions!")
        return

    lines = []
    for record in scores.values():
        pct = (record["correct"] / record["answered"] * 100) if record["answered"] else 0
        lines.append(f"**{record['name']}** — {record['correct']}/{record['answered']} correct ({pct:.0f}%)")

    embed = discord.Embed(
        title=f"🏁 {title} — Results",
        description="\n".join(lines),
        color=0x57F287,
    )
    await channel.send(embed=embed)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Set the DISCORD_BOT_TOKEN environment variable to your bot's token before running this."
        )
    bot.run(token)
