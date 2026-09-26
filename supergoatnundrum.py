from collections import defaultdict
from pathlib import Path
import random

import streamlit as st


LEXICON_PATH = Path(__file__).with_name("lexicon.txt")


@st.cache_data
def load_lexicon():
	entries = {}
	with LEXICON_PATH.open(encoding="utf-8") as lexicon_file:
		for line in lexicon_file:
			word, separator, difficulty_text = line.strip().partition("\t")
			if not separator or len(word) != 9 or not word.isalpha():
				continue
			try:
				difficulty = int(difficulty_text)
			except ValueError:
				continue
			entries[word.upper()] = difficulty
	return entries


def build_index(words):
	words_by_initial = defaultdict(list)
	for word in words:
		words_by_initial[word[0]].append(word)
	return words_by_initial


def choose_words(solution, words_by_initial):
	candidates_by_position = []
	for letter in solution:
		candidates = [
			word for word in words_by_initial[letter]
			if word != solution
		]
		if not candidates:
			raise ValueError(f"No alternate word starts with {letter}.")
		candidates_by_position.append(candidates)

	positions = sorted(
		range(len(solution)),
		key=lambda position: len(candidates_by_position[position]),
	)
	selected = [None] * len(solution)
	used_words = set()

	def search(position):
		if position == len(positions):
			return True

		word_position = positions[position]
		candidates = candidates_by_position[word_position].copy()
		random.shuffle(candidates)
		for word in candidates:
			if word in used_words:
				continue
			used_words.add(word)
			selected[word_position] = word
			if search(position + 1):
				return True
			used_words.remove(word)
			selected[word_position] = None
		return False

	if not search(0):
		raise ValueError("Could not find nine distinct words for this solution.")
	return selected


def jumble(word):
	letters = list(word)
	random.shuffle(letters)
	scrambled = "".join(letters)
	while scrambled == word and len(set(word)) > 1:
		random.shuffle(letters)
		scrambled = "".join(letters)
	return scrambled


def generate_puzzle(entries, maximum_difficulty):
	eligible_solutions = [
		word for word, difficulty in entries.items()
		if 1 <= difficulty <= maximum_difficulty
	]
	if not eligible_solutions:
		raise ValueError("No eligible solution words were found.")

	words_by_initial = build_index(entries)
	random.shuffle(eligible_solutions)
	for solution in eligible_solutions:
		try:
			selected_words = choose_words(solution, words_by_initial)
		except ValueError:
			continue

		items = [
			{
				"letter": letter,
				"word": word,
				"scrambled": jumble(word),
			}
			for letter, word in zip(solution, selected_words)
		]
		random.shuffle(items)
		return {"solution": solution, "items": items}

	raise ValueError("Could not build a puzzle from the available lexicon.")


st.set_page_config(page_title="Supernundrum", page_icon="?", layout="centered")
st.title("Supernundrum")
st.write(
	"Unscramble the nine words. Their starting letters spell the original "
	"nine-letter word."
)

entries = load_lexicon()
st.caption(f"Loaded {len(entries):,} nine-letter words")

maximum_difficulty = st.slider(
	"Maximum difficulty",
	min_value=1,
	max_value=4,
	value=2,
	help="The original word can have any difficulty from 1 up to this value.",
)

if st.button("Generate Supernundrum", type="primary", use_container_width=True):
	try:
		st.session_state.puzzle = generate_puzzle(entries, maximum_difficulty)
		st.session_state.revealed = False
	except ValueError as error:
		st.error(str(error))

puzzle = st.session_state.get("puzzle")
if puzzle:
	st.divider()
	st.subheader("Your words")
	for item in puzzle["items"]:
		displayed_word = item["word"] if st.session_state.get("revealed") else item["scrambled"]
		st.markdown(f"### {displayed_word}")

	if not st.session_state.get("revealed"):
		if st.button("Reveal Solution", use_container_width=True):
			st.session_state.revealed = True
			st.rerun()
	else:
		st.success(f"Original chosen word: **{puzzle['solution']}**")
