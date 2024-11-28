import wave
import json
import os
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment


def prepare_audio_for_vosk(input_file):
    """
    Prepares the input audio file for Vosk by ensuring it is in the correct format.
    If necessary, converts the audio to mono, 16kHz, 16-bit PCM WAV format.

    Args:
        input_file (str): Path to the input audio file.

    Returns:
        tuple: A tuple containing the wave file object and the path to any temporary audio file created.
    """
    wf = wave.open(input_file, "rb")
    if (
        wf.getnchannels() != 1
        or wf.getsampwidth() != 2
        or wf.getframerate() not in [8000, 16000]
    ):
        print("Converting audio to suitable format for Vosk...")
        sound = AudioSegment.from_file(input_file)
        sound = sound.set_channels(1).set_frame_rate(16000)
        temp_audio_path = "temp_vosk_audio.wav"
        sound.export(temp_audio_path, format="wav")
        wf = wave.open(temp_audio_path, "rb")
    else:
        temp_audio_path = None
    return wf, temp_audio_path


def transcribe_audio(wave_file, model_path):
    """
    Transcribes speech from the given wave file using the specified Vosk model.

    Args:
        wave_file (wave.Wave_read): The wave file object.
        model_path (str): Path to the Vosk model.

    Returns:
        list: A list of word dictionaries containing 'word', 'start', and 'end' times.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at path {model_path}")

    model = Model(model_path)
    recognizer = KaldiRecognizer(model, wave_file.getframerate())
    recognizer.SetWords(True)

    print("Transcribing speech...")
    words = []
    while True:
        data = wave_file.readframes(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            if "result" in result:
                words.extend(result["result"])

    final_result = json.loads(recognizer.FinalResult())
    if "result" in final_result:
        words.extend(final_result["result"])
    return words


def process_words(audio, words, config, initial_offset=0, timer_sound=None):
    """
    Processes the transcribed words to insert pauses or timer sounds at specified trigger words,
    and identifies occurrences of specified phrases.

    Args:
        audio (AudioSegment): The original audio segment.
        words (list): List of transcribed word dictionaries.
        config (dict): Configuration dictionary containing settings.
        initial_offset (int, optional): Initial time offset in milliseconds. Defaults to 0.
        timer_sound (AudioSegment, optional): The timer sound to insert. Defaults to None.

    Returns:
        tuple: Processed audio, list of pause times, and list of phrase occurrences.
    """
    output_audio = AudioSegment.empty()
    last_end_time = 0
    offset = initial_offset
    pause_times = []
    phrase_occurrences = []

    # Prepare phrases to find
    phrases_to_find = [
        [word.lower() for word in phrase] for phrase in config["phrases_to_find"]
    ]
    active_phrases = []
    trigger_words_lower = [w.lower() for w in config["trigger_words"]]

    phrase_counter = 1  # For numbering phrases

    for word_info in words:
        word = word_info["word"].lower()
        start_time = (word_info["start"] * 1000) + offset
        end_time = (word_info["end"] * 1000) + offset
        word_duration = end_time - start_time

        # Check for trigger words
        if word in trigger_words_lower:
            # Remove the word, insert timer or silence, and adjust offset
            pause_start = start_time
            pause_end = pause_start + config["question_pause_duration"]
            pause_times.append({"start_time": pause_start, "end_time": pause_end})

            output_audio += audio[last_end_time : word_info["start"] * 1000]

            if timer_sound:
                # Calculate how many times to repeat the timer sound to cover the pause duration
                repeats = config["question_pause_duration"] // len(timer_sound)
                remainder = config["question_pause_duration"] % len(timer_sound)
                timer_full = timer_sound * repeats + timer_sound[:remainder]
                output_audio += timer_full
            else:
                # If no timer sound is specified, use silence
                output_audio += AudioSegment.silent(
                    duration=config["question_pause_duration"]
                )

            offset += config["question_pause_duration"] - word_duration
            last_end_time = word_info["end"] * 1000
            continue  # Skip further processing of this word

        # Update active phrases
        new_active_phrases = []
        for active_phrase in active_phrases:
            phrase = phrases_to_find[active_phrase["phrase_idx"]]
            if (
                active_phrase["index"] < len(phrase)
                and phrase[active_phrase["index"]] == word
            ):
                active_phrase["index"] += 1
                if active_phrase["index"] == len(phrase):
                    # Phrase fully matched
                    phrase_occurrences.append(
                        {
                            "number": phrase_counter,
                            "phrase": " ".join(phrase),
                            "start_time": active_phrase["start_time"],
                            "end_time": end_time,
                        }
                    )
                    phrase_counter += 1  # Increment phrase number
                else:
                    new_active_phrases.append(active_phrase)
        active_phrases = new_active_phrases

        # Start new phrases
        for idx, phrase in enumerate(phrases_to_find):
            if phrase[0] == word:
                active_phrases.append(
                    {
                        "phrase_idx": idx,
                        "index": 1,
                        "start_time": start_time,
                    }
                )

        # Add current word's audio to output audio
        output_audio += audio[last_end_time : word_info["end"] * 1000]
        last_end_time = word_info["end"] * 1000

    # Add remaining audio
    output_audio += audio[last_end_time:]
    return output_audio, pause_times, phrase_occurrences


def combine_phrase_and_pause(phrase_times, pause_times, questions_data, config):
    """
    Combines phrase occurrences and pause times to generate a structured data list
    containing question and answer timings and texts.

    Args:
        phrase_times (list): List of phrase occurrence dictionaries.
        pause_times (list): List of pause time dictionaries.
        questions_data (list): List of question data dictionaries.
        config (dict): Configuration dictionary containing settings.

    Returns:
        list: Combined data list with question and answer timings and texts.
    """
    combined_data = []
    for i, (phrase, pause) in enumerate(zip(phrase_times, pause_times)):
        next_phrase_start = (
            phrase_times[i + 1]["start_time"] if i + 1 < len(phrase_times) else None
        )

        # Find the question and answer from questions_data
        question_data = next(
            (q for q in questions_data if q["number"] == phrase["number"]), {}
        )
        question_text = question_data.get("question", "No data")
        answer_text = question_data.get("answer", "No data")

        combined_data.append(
            {
                "number": phrase["number"],
                "question": {
                    "start_time": phrase["start_time"],
                    "end_time": pause["end_time"] + config["question_end_offset"],
                },
                "answer": {
                    "start_time": pause["end_time"] + config["answer_start_offset"],
                    "end_time": (
                        next_phrase_start if next_phrase_start is not None else None
                    ),
                },
                "question_text": question_text,
                "answer_text": answer_text,
            }
        )
    return combined_data


def overlay_background_music(audio, background_music_file, volume):
    """
    Overlays background music onto the provided audio at the specified volume level.

    Args:
        audio (AudioSegment): The original audio segment.
        background_music_file (str): Path to the background music file.
        volume (int): Volume level in dB to reduce the background music.

    Returns:
        AudioSegment: The audio with background music overlaid.
    """
    if not background_music_file:
        return audio

    print("Overlaying background music...")
    background_music = AudioSegment.from_file(background_music_file) - abs(volume)
    loop_count = (len(audio) // len(background_music)) + 1
    background_music = (background_music * loop_count)[: len(audio)]
    return audio.overlay(background_music)


def load_questions(file_path):
    """
    Loads questions data from the specified JSON file.

    Args:
        file_path (str): Path to the questions JSON file.

    Returns:
        list: List of question data dictionaries.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Questions file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("questions", [])


def add_pause(config):
    """
    Main function to process the audio file based on the provided configuration.
    Inserts pauses or timer sounds at trigger words, overlays background music,
    and saves the processed audio and timestamps.

    Args:
        config (dict): Configuration dictionary containing file paths and settings.
    """
    # Prepare audio for Vosk
    wf, temp_audio_path = prepare_audio_for_vosk(config["input_file"])
    words = transcribe_audio(wf, config["model_path"])
    audio = AudioSegment.from_file(config["input_file"])

    # Load questions data
    questions_data = load_questions(config["questions_file"])

    output_audio = AudioSegment.empty()
    total_offset = 0

    # Add hook if specified
    if config.get("hook"):
        hook_audio = AudioSegment.from_file(config["hook"])
        # Add hook pause
        hook_pause = AudioSegment.silent(duration=config["hook_pause_duration"])
        output_audio += hook_audio + hook_pause
        total_offset += len(hook_audio) + config["hook_pause_duration"]

    # Load timer sound
    timer_sound = (
        AudioSegment.from_file(config["timer_sound_file"])
        if config.get("timer_sound_file")
        else None
    )

    # Load bell sounds
    bell_sounds = []
    for i in range(1, config["bell_sound_count"] + 1):
        bell_path = config["bell_sound_files_pattern"].format(index=i)
        if not os.path.exists(bell_path):
            raise FileNotFoundError(f"Bell sound file not found: {bell_path}")
        bell_sounds.append(AudioSegment.from_file(bell_path))

    bell_counter = 0  # Counter to select next bell sound

    # Process words to insert pauses and find phrases
    processed_audio, pause_times, phrase_occurrences = process_words(
        audio, words, config, initial_offset=total_offset, timer_sound=timer_sound
    )
    output_audio += processed_audio

    # Overlay background music if specified
    final_audio = overlay_background_music(
        output_audio, config["background_music_file"], config["music_volume"]
    )

    # Overlay bell sounds after each pause
    if config.get("overlay_bell_sounds", True):
        print("Overlaying bell sounds after each pause...")
        for pause in pause_times:
            bell_position = pause["end_time"]
            # Ensure bell position does not exceed audio length
            if bell_position + len(bell_sounds[bell_counter]) > len(final_audio):
                bell_position = len(final_audio) - len(bell_sounds[bell_counter])
            final_audio = final_audio.overlay(
                bell_sounds[bell_counter], position=int(bell_position)
            )
            # Update counter for next bell sound
            bell_counter = (bell_counter + 1) % config["bell_sound_count"]

    # Combine phrases and pauses with questions data
    combined_data = combine_phrase_and_pause(
        phrase_occurrences, pause_times, questions_data, config
    )

    # Export final audio
    final_audio.export(config["output_file"], format="wav")
    print(f"File saved: {config['output_file']}")

    # Save timestamps and combined data if specified
    result_data = {
        "combined_data": combined_data,
        "audio_duration": len(final_audio),
    }
    if config.get("timestamps_file"):
        with open(config["timestamps_file"], "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)
        print(f"Timestamps saved to {config['timestamps_file']}")

    # Clean up temporary audio file if created
    if temp_audio_path:
        wf.close()
        os.remove(temp_audio_path)


# Configuration
config = {
    "model_path": r"./assets/models/vosk-ru",
    "input_file": "./assets/voice/voice.wav",
    "output_file": "./output/output_audio.wav",
    "hook": "./assets/hooks/minecrafter/minecrafter.wav",
    "timestamps_file": "./output/timestamps.json",
    "questions_file": "./data/data.json",  # Path to questions file
    "background_music_file": "./assets/music/funy.wav",
    "timer_sound_file": "./assets/sfx/timer/timer_with_whoosh.wav",  # Path to timer sound
    "bell_sound_files_pattern": "./assets/sfx/answer/bell_{index}.wav",
    "hook_pause_duration": 200,
    "question_pause_duration": 3000,
    "music_volume": -10,
    "bell_sound_count": 4,
    "question_end_offset": -400,
    "answer_start_offset": 200,
    "overlay_bell_sounds": True,
    "phrases_to_find": [
        ["первый", "вопрос"],
        ["идём", "дальше"],
        ["следующий", "вопрос"],
        ["двигаемся", "дальше"],
        ["самый", "сложный", "вопрос"],
        ["готов", "к", "следующему", "вопросу"],
    ],
    "trigger_words": ["ответ"],
}

# Run the processing
add_pause(config)
