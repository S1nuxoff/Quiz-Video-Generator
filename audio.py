from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
import os
import json

# Параметры
vosk_model_path = "./assets/models/vosk-ru"
input_audio_path = "./input/voice/voice.wav"
questions_output_path = "./temp/audio/questions"
answers_output_path = "./temp/audio/answers"
final_audio_output_path = "./temp/audio"
bells_path = "./assets/sfx/answer"
question_sfx_path = "./assets/sfx/question"
timer_sound_path = "./assets/sfx/timer/timer.wav"
background_music_path = "./assets/music/ai_swing.wav"
genius_sound_path = "./assets/hooks/genius/genius.wav"
json_output_path = "./temp/metadata.json"

# Настройки громкости
bell_volume_db = -10
question_sfx_volume_db = -5  # Громкость эффектов для вопросов
music_volume_db = -10

# Настройки вставки звуков
custom_sounds = {
    3: "./assets/bites/send_to_friend/send_to_friend.wav",
    6: "./assets/bites/like/like.wav",
}

# Убедимся, что папки существуют
os.makedirs(questions_output_path, exist_ok=True)
os.makedirs(answers_output_path, exist_ok=True)
os.makedirs(final_audio_output_path, exist_ok=True)

# Ключевые фразы
question_phrases = [
    "первый вопрос",
    "второй вопрос",
    "третий вопрос",
    "четвёртый вопрос",
    "пятый вопрос",
    "шестой вопрос",
    "седьмой вопрос",
    "восьмой вопрос",
    "девятый вопрос",
    "десятый вопрос",
]
answer_phrase = "ответ"

# question_phrases = [
#     "first question",
#     "second question",
#     "third  question",
#     "fourth question",
#     "fifth question",
#     "sixth question",
#     "seventh question",
#     "eighth question",
#     "ninth question",
#     "tenth  question",
# ]
# answer_phrase = "answer"


# Загрузка модели Vosk
if not os.path.exists(vosk_model_path):
    raise FileNotFoundError("Модель Vosk не найдена по указанному пути.")
model = Model(vosk_model_path)

# Загрузка звуков
bells = [
    AudioSegment.from_file(f"{bells_path}/bell_{i}.wav").apply_gain(bell_volume_db)
    for i in range(1, 5)
]
question_sfx = [
    AudioSegment.from_file(f"{question_sfx_path}/whoosh_{i}.wav").apply_gain(
        question_sfx_volume_db
    )
    for i in range(1, 5)
]
timer_sound = AudioSegment.from_file(timer_sound_path)
background_music = AudioSegment.from_file(background_music_path).apply_gain(
    music_volume_db
)
genius_sound = AudioSegment.from_file(genius_sound_path)

# Загрузка пользовательских звуков
custom_sounds_audio = {
    key: AudioSegment.from_file(value) for key, value in custom_sounds.items()
}

# Загрузка аудиофайла
original_audio = AudioSegment.from_file(input_audio_path)
audio_for_vosk = original_audio.set_channels(1).set_frame_rate(
    16000
)  # Подготовка для Vosk

recognizer = KaldiRecognizer(model, 16000)
recognizer.SetWords(True)

# Преобразование аудио в текст с временными метками
results = []
buffer_size = 4000
for i in range(0, len(audio_for_vosk), buffer_size):
    chunk = audio_for_vosk[i : i + buffer_size]
    data = chunk.raw_data
    if recognizer.AcceptWaveform(data):
        results.append(json.loads(recognizer.Result()))
results.append(json.loads(recognizer.FinalResult()))

# Обработка распознанного текста
timestamps = []
for result in results:
    if "result" in result:
        for word in result["result"]:
            timestamps.append(
                {
                    "word": word["word"],
                    "start": int(word["start"] * 1000),
                    "end": int(word["end"] * 1000),
                }
            )


# Функция поиска временных меток ключевых фраз
def find_timestamps(phrases, timestamps):
    found = []
    for phrase in phrases:
        phrase_words = phrase.split()
        for i in range(len(timestamps) - len(phrase_words) + 1):
            if all(
                timestamps[i + j]["word"] == phrase_words[j]
                for j in range(len(phrase_words))
            ):
                found.append(
                    {
                        "phrase": phrase,
                        "start": timestamps[i]["start"],
                        "end": timestamps[i + len(phrase_words) - 1]["end"],
                    }
                )
    return found


# Найти временные метки вопросов и ответов
questions = find_timestamps(question_phrases, timestamps)
answers = find_timestamps([answer_phrase], timestamps)

# Разделить аудио на вопросы и ответы
for i in range(len(questions)):
    question_start = questions[i]["end"]
    answer_start = answers[i]["end"] if i < len(answers) else len(original_audio)
    next_question_start = (
        questions[i + 1]["start"] if i + 1 < len(questions) else len(original_audio)
    )

    # Сохранение вопросов с наложением эффекта
    question_audio = original_audio[question_start : answers[i]["start"]]
    sfx = question_sfx[i % len(question_sfx)]  # Выбираем звук по индексу
    combined_question_audio = question_audio.overlay(sfx)
    combined_question_audio.export(
        f"{questions_output_path}/question_{i + 1}.wav", format="wav"
    )

    # Сохранение ответов с наложением фонового звука
    answer_audio = original_audio[answer_start:next_question_start]
    bell = bells[i % len(bells)]
    combined_answer_audio = answer_audio.overlay(bell, loop=False)
    combined_answer_audio.export(
        f"{answers_output_path}/answer_{i + 1}.wav", format="wav"
    )


# Функция сортировки файлов по числовой части имени
def sort_files_by_number(files, prefix):
    return sorted(
        files,
        key=lambda x: int(x.replace(prefix, "").replace(".wav", "")),
    )


# Сортировка файлов вопросов и ответов
question_files = sort_files_by_number(
    [f for f in os.listdir(questions_output_path) if f.startswith("question_")],
    prefix="question_",
)
answer_files = sort_files_by_number(
    [f for f in os.listdir(answers_output_path) if f.startswith("answer_")],
    prefix="answer_",
)

# Создание итогового аудио
final_audio = genius_sound  # Начинаем с genius.wav
current_time = len(genius_sound)

metadata = {"combined_data": [], "bites": [], "audio_duration": 0}

for i, (question_file, answer_file) in enumerate(zip(question_files, answer_files)):
    question_audio = AudioSegment.from_file(
        os.path.join(questions_output_path, question_file)
    )
    answer_audio = AudioSegment.from_file(
        os.path.join(answers_output_path, answer_file)
    )

    question_start_time = current_time
    current_time += len(question_audio)
    question_end_time = (
        current_time + 2700
    )  # Добавляем 2700 мс только к end_time вопроса

    final_audio += question_audio
    final_audio += timer_sound
    current_time += len(timer_sound)

    answer_start_time = current_time
    current_time += len(answer_audio)
    answer_end_time = current_time

    final_audio += answer_audio

    metadata["combined_data"].append(
        {
            "number": i + 1,
            "question": {
                "start_time": question_start_time,
                "end_time": question_end_time,
            },
            "answer": {"start_time": answer_start_time, "end_time": answer_end_time},
        }
    )

    # Проверяем, нужно ли вставить пользовательский звук
    if i + 1 in custom_sounds_audio:
        custom_sound = custom_sounds_audio[i + 1]
        final_audio += custom_sound
        metadata["bites"].append(
            {
                "type": f"custom_sound_{i + 1}",
                "start_time": current_time,
                "end_time": current_time + len(custom_sound),
            }
        )
        current_time += len(custom_sound)

# Наложение фоновой музыки
background_music = background_music * (len(final_audio) // len(background_music) + 1)
final_audio = final_audio.overlay(background_music[: len(final_audio)])

metadata["audio_duration"] = len(final_audio)

# Сохранение итогового аудио
final_audio.export(
    os.path.join(final_audio_output_path, "final_audio.wav"), format="wav"
)

# Сохранение метаданных в JSON
with open(json_output_path, "w") as f:
    json.dump(metadata, f, indent=4)

print("Итоговое аудио и метаданные успешно сгенерированы.")
