import os
import json
from PIL import Image, ImageDraw, ImageFont

# Настройки
FONT_PATH = "./assets/fonts/Rubik-Bold.ttf"  # Укажите путь к жирному шрифту Rubik
FONT_SIZE = 40
QUESTION_BG_COLOR = "#FFFFFF"
ANSWER_BG_COLOR = "#09B71D"
TEXT_COLOR = "#173871"
PADDING_VERTICAL = 40
PADDING_HORIZONTAL = 63
MAX_WIDTH = 903
BORDER_RADIUS = 40
OUTLINE_COLOR = "#FFFFFF"
OUTLINE_WIDTH = 10
DATA_PATH = "./data/data.json"
QUESTION_IMAGE_DIR = "./assets/images/questions"
ANSWER_IMAGE_DIR = "./assets/images/answers"
NUMBER_IMAGE_DIR = "./assets/images/numbers/v4"  # Директория с номерами


def create_rounded_rectangle_with_outline(
    draw, x0, y0, x1, y1, radius, fill, outline_color, outline_width
):
    """Создаёт прямоугольник с округлыми углами и обводкой."""
    # Рисуем обводку
    draw.rounded_rectangle(
        [
            x0 - outline_width,
            y0 - outline_width,
            x1 + outline_width,
            y1 + outline_width,
        ],
        radius=radius + outline_width,
        fill=outline_color,
    )
    # Рисуем основной прямоугольник
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        fill=fill,
    )


def wrap_text(text, font, max_width):
    """Переносит текст, если он не помещается в строку."""
    words = text.split()
    wrapped_text = ""
    line = ""

    for word in words:
        test_line = f"{line} {word}".strip()
        line_width = font.getlength(test_line)
        if line_width <= max_width:
            line = test_line
        else:
            wrapped_text += f"{line}\n"
            line = word

    wrapped_text += line
    return wrapped_text


def create_question_image(text, bg_color, save_path, number_image_path):
    """Создаёт изображение вопроса с наложением номера, с фиксированной шириной 1080."""
    # Настройка шрифта
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # Перенос текста
    wrapped_text = wrap_text(text, font, MAX_WIDTH - 2 * PADDING_HORIZONTAL)

    # Вычисляем размеры текста
    dummy_image = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_image)
    text_bbox = dummy_draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Устанавливаем ширину и высоту фона с учетом отступов
    bg_width = text_width + 2 * PADDING_HORIZONTAL + 2 * OUTLINE_WIDTH
    bg_height = text_height + 2 * PADDING_VERTICAL + 2 * OUTLINE_WIDTH

    # Загружаем изображение номера
    number_image = Image.open(number_image_path).convert("RGBA")
    number_width, number_height = number_image.size

    # Общая высота изображения (фон + номер)
    total_height = bg_height + number_height - 14

    # Фиксированная ширина итогового изображения
    fixed_width = 1080
    fixed_height = total_height

    # Создаём изображение с фиксированной шириной и прозрачным фоном
    image = Image.new("RGBA", (fixed_width, fixed_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Вычисляем горизонтальное смещение для центрирования
    x_offset = (fixed_width - bg_width) // 2

    # Добавляем закругленный фон с обводкой
    create_rounded_rectangle_with_outline(
        draw,
        x_offset + OUTLINE_WIDTH,
        number_height - 14 + OUTLINE_WIDTH,
        x_offset + bg_width - OUTLINE_WIDTH,
        total_height - OUTLINE_WIDTH,
        BORDER_RADIUS,
        bg_color,
        OUTLINE_COLOR,
        OUTLINE_WIDTH,
    )

    # Центрируем текст
    text_x = x_offset + (bg_width - text_width) // 2
    text_y = (
        number_height
        - 14
        + OUTLINE_WIDTH
        + (bg_height - 2 * OUTLINE_WIDTH - text_height) // 2
    )

    # Добавляем обводку текста
    outline_color = "#000000"
    outline_width = 0
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            if offset_x != 0 or offset_y != 0:
                draw.multiline_text(
                    (text_x + offset_x, text_y + offset_y),
                    wrapped_text,
                    font=font,
                    fill=outline_color,
                    align="center",
                )

    # Рисуем основной текст
    draw.multiline_text(
        (text_x, text_y), wrapped_text, font=font, fill=TEXT_COLOR, align="center"
    )

    # Накладываем изображение номера
    number_x = x_offset + (bg_width - number_width) // 2
    number_y = 32
    image.paste(number_image, (number_x, number_y), number_image)

    # Сохраняем изображение
    image.save(save_path)


def create_answer_image(text, bg_color, save_path):
    """Создаёт изображение ответа с фиксированной шириной 1080 и добавляет изображение успеха сверху после отрисовки текста."""
    # Настройка шрифта
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # Перенос текста
    wrapped_text = wrap_text(text, font, MAX_WIDTH - 2 * PADDING_HORIZONTAL)

    # Вычисляем размеры текста
    dummy_image = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_image)
    text_bbox = dummy_draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Устанавливаем ширину и высоту фона с учетом отступов
    bg_width = text_width + 2 * PADDING_HORIZONTAL + 2 * OUTLINE_WIDTH
    bg_height = text_height + 2 * PADDING_VERTICAL + 2 * OUTLINE_WIDTH

    # Загружаем изображение успеха
    success_image_path = "./assets/images/success/success.png"
    success_image = Image.open(success_image_path).convert("RGBA")
    success_width, success_height = success_image.size

    # Общая высота изображения (успех + фон)
    total_height = bg_height + success_height - 14

    # Фиксированная ширина итогового изображения
    fixed_width = 1080
    fixed_height = total_height

    # Создаём изображение с фиксированной шириной и прозрачным фоном
    image = Image.new("RGBA", (fixed_width, fixed_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Вычисляем горизонтальное смещение для центрирования
    x_offset = (fixed_width - bg_width) // 2

    # Добавляем закругленный фон с обводкой
    create_rounded_rectangle_with_outline(
        draw,
        x_offset + OUTLINE_WIDTH,
        success_height - 14 + OUTLINE_WIDTH,
        x_offset + bg_width - OUTLINE_WIDTH,
        total_height - OUTLINE_WIDTH,
        BORDER_RADIUS,
        bg_color,
        OUTLINE_COLOR,
        OUTLINE_WIDTH,
    )

    success_width, success_height = success_image.size
    text_x = x_offset + (bg_width - text_width) // 2
    text_y = (
        success_height
        - 20
        + OUTLINE_WIDTH
        + (bg_height - 2 * OUTLINE_WIDTH - text_height) // 2
    )

    # Добавляем обводку текста
    outline_color = "#000000"
    outline_width = 0
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            if offset_x != 0 or offset_y != 0:
                draw.multiline_text(
                    (text_x + offset_x, text_y + offset_y),
                    wrapped_text,
                    font=font,
                    fill=outline_color,
                    align="center",
                )

    # Рисуем основной текст
    draw.multiline_text(
        (text_x, text_y), wrapped_text, font=font, fill="#FFFF", align="center"
    )

    # Накладываем изображение успеха сверху после отрисовки основного текста
    success_x = x_offset + (bg_width - success_width) // 2
    success_y = 32
    image.paste(success_image, (success_x, success_y), success_image)

    # Сохраняем изображение
    image.save(save_path)


def main():
    # Создаём директории, если их нет
    os.makedirs(QUESTION_IMAGE_DIR, exist_ok=True)
    os.makedirs(ANSWER_IMAGE_DIR, exist_ok=True)

    # Загружаем данные
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Генерируем изображения
    for item in data["questions"]:
        question_text = item["question"]
        answer_text = item["answer"]
        number = item["number"]
        question_path = os.path.join(QUESTION_IMAGE_DIR, f"question_{number}.png")
        answer_path = os.path.join(ANSWER_IMAGE_DIR, f"answer_{number}.png")
        number_image_path = os.path.join(NUMBER_IMAGE_DIR, f"number_{number}.png")

        # Создаём изображение для вопроса с наложением номера
        create_question_image(
            question_text, QUESTION_BG_COLOR, question_path, number_image_path
        )
        # Создаём изображение для ответа
        create_answer_image(answer_text, ANSWER_BG_COLOR, answer_path)


if __name__ == "__main__":
    main()
