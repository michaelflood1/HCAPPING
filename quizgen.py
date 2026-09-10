



# """
# important functionality 

# 1. import quizzes
# 2. easy to create quizzes whether through the cli or by typing a file out and adding it to the folder
# 3. on quiz call will allow you to go numerically or randomly through the questions
# 4. after finish output correct answer count/ percent answered correctly
# 5. gives option to redo quiz or to go back to quiz list






# """








# print("select option")
# print(select_list)
# list_choice = input(" enter the number attached to your quiz")

# if list_choice == # whatever number chosen:
#     # give option to start quiz numerically or randomly
#     # repeat
#     # quiz functionality, runs through all questions giving the question and allowing the user to provide input.
#     #  multiple choice and true false statements
#     # after question answered will return if true or false and move on to the next 
#     # after quiz completed total score and percent of correct returned
#     # option to retake quiz or go back to previous section
# elif list_choice = "create quiz":
#     # return option to first name a quiz
#     # create new file in same folder to store the quiz
#     # for each quiestion give option to create multiple choice or true and false
#     # if multiple choice give 4 letters a b c d and let teach be filled out for the question, after input get the correct answer selected, store 
#     # store answer in whatever format into the created quiz file
# #!/usr/bin/env python3
# """
# Quick Quiz Generator
# =====================
# A simple CLI tool for creating and taking quizzes.

# Quizzes are stored as JSON files in the "quizzes/" folder (next to this
# script). You can create a quiz two ways:
#   1. Through the CLI's built-in quiz creator ("create quiz" option).
#   2. By hand-writing a JSON file and dropping it into the "quizzes/"
#      folder. See quizzes/sample_science.json for the exact format, or
#      the SCHEMA text below.

# JSON schema for a quiz file:
# {
#   "title": "Quiz Title",
#   "questions": [
#     {
#       "type": "mc",
#       "question": "Question text?",
#       "choices": {"a": "...", "b": "...", "c": "...", "d": "..."},
#       "answer": "b"
#     },
#     {
#       "type": "tf",
#       "question": "Statement to judge.",
#       "answer": "true"
#     }
#   ]
# }

# Run it with:  python3 quiz_app.py
# """

import json
import os
import random
import re
import sys

QUIZ_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quizzes")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clear_ish():
    """Print a small visual break instead of clearing the whole terminal,
    so past output/scores aren't lost from scrollback."""
    print("\n" + "-" * 40 + "\n")


def prompt(msg):
    try:
        return input(msg).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        sys.exit(0)


def prompt_choice(msg, valid_choices):
    """Keep asking until the user enters one of valid_choices (case-insensitive)."""
    valid_lower = {v.lower() for v in valid_choices}
    while True:
        ans = prompt(msg).lower()
        if ans in valid_lower:
            return ans
        print(f"Please enter one of: {', '.join(valid_choices)}")


def prompt_int(msg, min_val=None, max_val=None):
    while True:
        raw = prompt(msg)
        if raw.isdigit():
            val = int(raw)
            if (min_val is None or val >= min_val) and (max_val is None or val <= max_val):
                return val
        print("Please enter a valid number" +
              (f" between {min_val} and {max_val}." if min_val is not None else "."))


def safe_filename(name):
    """Turn a quiz title into a safe filename."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return name or "quiz"


# ---------------------------------------------------------------------------
# Quiz storage
# ---------------------------------------------------------------------------

def ensure_quiz_dir():
    os.makedirs(QUIZ_DIR, exist_ok=True)


def list_quizzes():
    """Return a list of (filepath, title, question_count) for every valid
    quiz JSON file in the quizzes folder. Invalid files are skipped with
    a warning so one bad file doesn't crash the whole app."""
    ensure_quiz_dir()
    quizzes = []
    for fname in sorted(os.listdir(QUIZ_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(QUIZ_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            title = data.get("title", fname)
            questions = data.get("questions", [])
            if not questions:
                raise ValueError("no questions found")
            quizzes.append((fpath, title, len(questions)))
        except (json.JSONDecodeError, ValueError, OSError) as e:
            print(f"  [!] Skipping '{fname}': {e}")
    return quizzes


def load_quiz(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_quiz(title, questions):
    ensure_quiz_dir()
    base = safe_filename(title)
    fname = base + ".json"
    fpath = os.path.join(QUIZ_DIR, fname)
    # avoid overwriting an existing quiz file
    counter = 2
    while os.path.exists(fpath):
        fname = f"{base}_{counter}.json"
        fpath = os.path.join(QUIZ_DIR, fname)
        counter += 1
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump({"title": title, "questions": questions}, f, indent=2)
    return fpath


# ---------------------------------------------------------------------------
# Quiz creation
# ---------------------------------------------------------------------------

def create_quiz_flow():
    clear_ish()
    print("=== Create a New Quiz ===")
    title = prompt("Quiz name: ")
    while not title:
        title = prompt("Quiz name can't be empty. Quiz name: ")

    questions = []
    while True:
        clear_ish()
        print(f"Adding question #{len(questions) + 1} to '{title}'")
        qtype = prompt_choice(
            "Question type - (m)ultiple choice or (t)rue/false? ", ["m", "t"]
        )

        qtext = prompt("Question text: ")
        while not qtext:
            qtext = prompt("Question can't be empty. Question text: ")

        if qtype == "m":
            choices = {}
            for letter in ["a", "b", "c", "d"]:
                val = prompt(f"  Choice {letter}: ")
                while not val:
                    val = prompt(f"  Choice {letter} can't be empty. Choice {letter}: ")
                choices[letter] = val
            correct = prompt_choice(
                "  Correct answer (a/b/c/d): ", ["a", "b", "c", "d"]
            )
            questions.append({
                "type": "mc",
                "question": qtext,
                "choices": choices,
                "answer": correct,
            })
        else:
            correct = prompt_choice("  Correct answer (true/false): ", ["true", "false"])
            questions.append({
                "type": "tf",
                "question": qtext,
                "answer": correct,
            })

        more = prompt_choice("Add another question? (y/n): ", ["y", "n"])
        if more == "n":
            break

    fpath = save_quiz(title, questions)
    clear_ish()
    print(f"Saved '{title}' ({len(questions)} questions) to:\n  {fpath}")
    prompt("\nPress Enter to return to the quiz list...")


# ---------------------------------------------------------------------------
# Quiz taking
# ---------------------------------------------------------------------------

def ask_question(index, q):
    """Ask a single question, return True if answered correctly."""
    print(f"\nQ{index}: {q['question']}")
    if q["type"] == "mc":
        for letter in ["a", "b", "c", "d"]:
            if letter in q["choices"]:
                print(f"  {letter}) {q['choices'][letter]}")
        valid = [l for l in q["choices"]]
        ans = prompt_choice("Your answer: ", valid)
    else:  # true/false
        ans = prompt_choice("Your answer (true/false): ", ["true", "false"])

    correct = ans == str(q["answer"]).lower()
    if correct:
        print("Correct!")
    else:
        # show the correct answer in a readable form
        if q["type"] == "mc":
            correct_display = f"{q['answer']}) {q['choices'].get(q['answer'], '')}"
        else:
            correct_display = q["answer"]
        print(f"Incorrect. Correct answer: {correct_display}")
    return correct


def run_quiz(fpath):
    while True:  # loop so "retake" doesn't leave this function
        data = load_quiz(fpath)
        title = data.get("title", "Quiz")
        questions = list(data.get("questions", []))

        clear_ish()
        print(f"=== {title} ===")
        order = prompt_choice(
            "Go through questions (n)umerically or (r)andomly? ", ["n", "r"]
        )
        if order == "r":
            random.shuffle(questions)

        correct_count = 0
        for i, q in enumerate(questions, start=1):
            if ask_question(i, q):
                correct_count += 1

        total = len(questions)
        pct = (correct_count / total * 100) if total else 0
        clear_ish()
        print(f"=== Results: {title} ===")
        print(f"Score: {correct_count}/{total} correct ({pct:.1f}%)")

        choice = prompt_choice(
            "\n(r)etake this quiz or (b)ack to quiz list? ", ["r", "b"]
        )
        if choice == "b":
            return


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu():
    ensure_quiz_dir()
    while True:
        clear_ish()
        print("=== Quiz Menu ===")
        quizzes = list_quizzes()
        for i, (fpath, title, qcount) in enumerate(quizzes, start=1):
            print(f"  {i}) {title} ({qcount} questions)")
        create_option = len(quizzes) + 1
        print(f"  {create_option}) Create a new quiz")
        print(f"  0) Quit")

        choice = prompt("\nEnter the number for your choice: ")
        if not choice.isdigit():
            print("Please enter a number.")
            prompt("Press Enter to continue...")
            continue
        choice = int(choice)

        if choice == 0:
            print("Goodbye!")
            return
        elif choice == create_option:
            create_quiz_flow()
        elif 1 <= choice <= len(quizzes):
            fpath = quizzes[choice - 1][0]
            run_quiz(fpath)
        else:
            print("Invalid choice.")
            prompt("Press Enter to continue...")


if __name__ == "__main__":
    main_menu()
