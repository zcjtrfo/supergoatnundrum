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


def build_index(entries, maximum_difficulty):
	words_by_initial = defaultdict(list)
	for word, difficulty in entries.items():
		if 1 <= difficulty <= maximum_difficulty:
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


def build_completion_index(entries):
	completions = defaultdict(set)
	for word in entries:
		for position in range(len(word)):
			visible_letters = word[:position] + word[position + 1:]
			completions["".join(sorted(visible_letters))].add(word)
	return completions


def valid_drop_positions(word, completion_index):
	valid_positions = []
	for position in range(len(word)):
		visible_letters = word[:position] + word[position + 1:]
		completion_words = completion_index["".join(sorted(visible_letters))]
		if completion_words == {word}:
			valid_positions.append(position)
	return valid_positions


def jumble(word):
	letters = list(word)
	random.shuffle(letters)
	scrambled = "".join(letters)
	while scrambled == word and len(set(word)) > 1:
		random.shuffle(letters)
		scrambled = "".join(letters)
	return scrambled


def goatdown_scramble(word, dropped_position):
	remaining_letters = list(word[:dropped_position] + word[dropped_position + 1:])
	random.shuffle(remaining_letters)
	blank_position = random.randrange(len(word))
	remaining_letters.insert(blank_position, " ")
	return "".join(remaining_letters)


def generate_puzzle(entries, maximum_difficulty, goatdown=False):
	eligible_solutions = [
		word for word, difficulty in entries.items()
		if 1 <= difficulty <= maximum_difficulty
	]
	if not eligible_solutions:
		raise ValueError("No eligible solution words were found.")

	words_by_initial = build_index(entries, maximum_difficulty)
	completion_index = build_completion_index(entries) if goatdown else None
	random.shuffle(eligible_solutions)
	for solution in eligible_solutions:
		try:
			selected_words = choose_words(solution, words_by_initial)
		except ValueError:
			continue

		items = []
		valid_goatdown = True
		for letter, word in zip(solution, selected_words):
			if goatdown:
				valid_positions = valid_drop_positions(word, completion_index)
				if not valid_positions:
					valid_goatdown = False
					break
				dropped_position = random.choice(valid_positions)
				scrambled = goatdown_scramble(word, dropped_position)
			else:
				scrambled = jumble(word)
			items.append(
				{
					"letter": letter,
					"word": word,
					"scrambled": scrambled,
				}
			)

		if not valid_goatdown:
			continue
		random.shuffle(items)
		return {"solution": solution, "items": items}

	raise ValueError("Could not build a puzzle from the available lexicon.")


def render_word_tiles(word):
	tiles = "".join(
		f'<span class="supernundrum-tile{ " supernundrum-blank" if letter == " " else "" }">'
		f'{"&nbsp;" if letter == " " else letter}</span>'
		for letter in word
	)
	st.markdown(
		f'<div class="supernundrum-word" aria-label="{word}">{tiles}</div>',
		unsafe_allow_html=True,
	)


st.set_page_config(page_title="Supernundrum", page_icon="?", layout="centered")
st.markdown(
	"""
	<style>
	.supernundrum-word {
		display: flex;
		justify-content: center;
		gap: 0.2rem;
		margin: 0.9rem 0;
		width: 100%;
	}
	.supernundrum-tile {
		align-items: center;
		background: #55acd8;
		border: 2px solid #2f8dbd;
		border-radius: 3px;
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3), 0 2px 3px rgba(20, 75, 105, 0.2);
		color: white;
		display: inline-flex;
		font-family: "Trebuchet MS", sans-serif;
		font-size: 1.65rem;
		font-weight: 700;
		height: 2.55rem;
		justify-content: center;
		line-height: 1;
		width: 2.35rem;
	}
	.supernundrum-blank {
		background: #dceef6;
		border-color: #55acd8;
		box-shadow: inset 0 1px 2px rgba(20, 75, 105, 0.2);
	}
	@media (max-width: 480px) {
		.supernundrum-tile {
			font-size: 1.25rem;
			height: 2.1rem;
			width: 1.82rem;
		}
	}
	</style>
	""",
	unsafe_allow_html=True,
)

entries = load_lexicon()
left_column, right_column = st.columns(2, gap="large")

with left_column:
	st.title("Supernundrum")
	goatdown = st.toggle(
		"Goatdown mode",
		help="Show each subword with one letter missing. Every missing letter must have a unique solution in the full lexicon.",
	)
	st.write(
		"In Goatdown mode, solve eight words with one letter missing. In Normal "
		"mode, unscramble nine complete words. Their starting letters spell the "
		"original nine-letter word."
	)
	st.caption(f"Loaded {len(entries):,} nine-letter words")

	maximum_difficulty = st.slider(
		"Maximum difficulty",
		min_value=1,
		max_value=4,
		value=2,
		help="The original word and subwords can have difficulty from 1 up to this value.",
	)

	if st.button("Generate Supernundrum", type="primary", use_container_width=True):
		try:
			st.session_state.puzzle = generate_puzzle(
				entries,
				maximum_difficulty,
				goatdown=goatdown,
			)
			st.session_state.revealed = False
		except ValueError as error:
			st.error(str(error))

puzzle = st.session_state.get("puzzle")
if puzzle:
	with right_column:
		for item in puzzle["items"]:
			displayed_word = item["word"] if st.session_state.get("revealed") else item["scrambled"]
			render_word_tiles(displayed_word)

		if not st.session_state.get("revealed"):
			if st.button("Reveal Solution", use_container_width=True):
				st.session_state.revealed = True
				st.rerun()
		else:
			st.success(f"Original chosen word: **{puzzle['solution']}**")
