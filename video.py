from moviepy import (
    VideoFileClip,
    CompositeVideoClip,
    ImageClip,
    AudioFileClip,
)
import json
import numpy as np

# Загрузка данных из JSON
with open("./output/final/metadata.json", "r", encoding="utf-8") as file:
    data = json.load(file)

video_duration = data["audio_duration"] / 1000  # Перевод из миллисекунд в секунды
clips = []

# Параметры экрана и анимации
screen_width = 1080
screen_height = 1920
move_in_duration = 0.5  # Длительность анимации появления
move_out_duration = 0.5  # Длительность анимации исчезновения
answer_display_duration = 1.5  # Время отображения изображения ответа
timer_offset = 3.125  # Смещение таймера в секундах перед показом ответа
timer_position = (
    "center",
    212,
)  # Позиция таймера: центр по горизонтали, 212 пикселей от верха


# Функция для эффекта ease-in/ease-out
def ease_in_out(progress):
    return -0.5 * (np.cos(np.pi * progress) - 1)  # progress от 0 до 1


# Загрузка видео фона
background_video = VideoFileClip("./assets/backgrounds/minecraft/parkour_1.mp4")

# Зацикливание видео фона на длительность итогового видео
background_loops = []
start_time = 0
while start_time < video_duration:
    loop_clip = background_video.with_start(start_time).with_duration(
        min(background_video.duration, video_duration - start_time)
    )
    background_loops.append(loop_clip)
    start_time += background_video.duration

background = CompositeVideoClip(background_loops, size=(screen_width, screen_height))

# Загрузка видео таймера
timer_original = VideoFileClip("./assets/vfx/timer.mov", has_mask=True)

if not timer_original.mask:
    print(
        "Warning: timer_clip does not have a mask. Transparency may not work as expected."
    )
    timer_original = timer_original.with_opacity(0.5)

for entry in data["combined_data"]:
    number = entry["number"]

    # Вопрос
    question_start = entry["question"]["start_time"] / 1000
    question_end = entry["question"]["end_time"] / 1000
    question_img_path = f"./assets/images/questions/question_{number}.png"

    question_clip = ImageClip(question_img_path)
    image_width, image_height = question_clip.size
    start_pos = -image_width
    center_pos = (screen_width - image_width) / 2
    end_pos = screen_width

    def question_position_with_swing(t):
        if 0 <= t < move_in_duration:
            # Анимация появления
            progress = t / move_in_duration
            x = start_pos + (center_pos - start_pos) * ease_in_out(progress)
        elif (
            move_in_duration <= t < (question_end - question_start - move_out_duration)
        ):
            # Вопрос в центре экрана с легким качанием
            center_time = t - move_in_duration  # Время с начала центральной фазы
            swing_amplitude = 10  # Амплитуда качания (в пикселях)
            swing_frequency = 0.5  # Частота качания (кол-во циклов в секунду)
            x = center_pos + swing_amplitude * np.sin(
                2 * np.pi * swing_frequency * center_time
            ) * ease_in_out(
                0.5 + 0.5 * np.sin(2 * np.pi * swing_frequency * center_time)
            )
        elif (
            (question_end - question_start - move_out_duration)
            <= t
            <= (question_end - question_start)
        ):
            # Анимация исчезновения
            t_rel = t - (question_end - question_start - move_out_duration)
            progress = t_rel / move_out_duration
            x = center_pos + (end_pos - center_pos) * ease_in_out(progress)
        else:
            # Вне времени отображения
            x = 2 * screen_width
        return (x, "center")

    question_clip = (
        question_clip.with_position(question_position_with_swing)
        .with_start(question_start)
        .with_duration(question_end - question_start)
    )
    clips.append(question_clip)

    # Ответ
    answer_start = entry["answer"]["start_time"] / 1000
    answer_img_path = f"./assets/images/answers/answer_{number}.png"

    answer_clip = (
        ImageClip(answer_img_path)
        .with_start(answer_start)
        .with_duration(answer_display_duration)
    )

    def answer_position(t):
        if 0 <= t < move_in_duration:
            progress = t / move_in_duration
            x = start_pos + (center_pos - start_pos) * ease_in_out(progress)
        elif move_in_duration <= t < (answer_display_duration - move_out_duration):
            x = center_pos
        elif (
            (answer_display_duration - move_out_duration)
            <= t
            <= answer_display_duration
        ):
            t_rel = t - (answer_display_duration - move_out_duration)
            progress = t_rel / move_out_duration
            x = center_pos + (end_pos - center_pos) * ease_in_out(progress)
        else:
            x = 2 * screen_width
        return (x, "center")

    answer_clip = answer_clip.with_position(answer_position)
    clips.append(answer_clip)

    # Таймер
    timer_start_time = answer_start - timer_offset
    if timer_start_time >= 0:
        timer_clip = timer_original.with_start(timer_start_time).with_position(
            timer_position
        )
        clips.append(timer_clip)
    else:
        print(
            f"Warning: Timer for answer {number} starts before the beginning of the video. Skipping timer addition."
        )
monkey_clip = VideoFileClip("./assets/hooks/genius/genius.mov", has_mask=True)
if not monkey_clip.mask:
    monkey_clip = monkey_clip.with_opacity(0.5)
if monkey_clip.duration > video_duration:
    monkey_clip = monkey_clip.subclip(0, video_duration)
monkey_clip = monkey_clip.with_position(("center", "center")).with_start(0)

# Сбор всех клипов
all_clips = [background] + clips + [monkey_clip]

final_video = CompositeVideoClip(
    all_clips, size=(screen_width, screen_height)
).with_duration(video_duration)

# Аудио
audio_clip = AudioFileClip("./output/final/final_audio.wav")
final_video = final_video.with_audio(audio_clip)

final_video.write_videofile("./result/video.mp4", fps=24, bitrate="5000k")
