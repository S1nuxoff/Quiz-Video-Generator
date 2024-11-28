import os
import json
from PIL import Image, ImageDraw, ImageFont

# Конфигурация
CONFIG = {
    "font_path": "./assets/fonts/RussoOne-Regular.ttf",
    "font_size": 40,
    "question_bg_color": "#FFFFFF",
    "answer_bg_color": "#09B71D",
    "question_text_color": "#173871",
    "answer_text_color": "#FFFFFF",
    "padding_vertical": 40,
    "padding_horizontal": 63,
    "max_width": 903,
    "border_radius": 40,
    "outline_color": "#FFFFFF",
    "outline_width": 10,
    "success_image_path": "./assets/images/success/success.png",
    "number_image_dir": "./assets/images/numbers/v4",
    "question_image_dir": "./assets/images/questions",
    "answer_image_dir": "./assets/images/answers",
    "data_path": "./data/data.json",
    "fixed_width": 1080,
}


def create_rounded_rectangle_with_outline(
    draw, x0, y0, x1, y1, radius, fill, outline_color, outline_width
):
    """Создаёт прямоугольник с округлыми углами и обводкой."""
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
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def wrap_text(text, font, max_width):
    """Переносит текст, если он не помещается в строку."""
    words = text.split()
    wrapped_text, line = "", ""

    for word in words:
        test_line = f"{line} {word}".strip()
        if font.getlength(test_line) <= max_width:
            line = test_line
        else:
            wrapped_text += f"{line}\n"
            line = word

    return wrapped_text + line


def create_image_with_text(
    text, bg_color, text_color, save_path, config, overlay_image_path=None
):
    """Создаёт изображение с текстом, дополнительно накладывая изображение сверху, если требуется."""
    font = ImageFont.truetype(config["font_path"], config["font_size"])
    wrapped_text = wrap_text(
        text, font, config["max_width"] - 2 * config["padding_horizontal"]
    )

    dummy_image = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_image)
    text_bbox = dummy_draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    text_width, text_height = text_bbox[2], text_bbox[3]

    bg_width = (
        text_width + 2 * config["padding_horizontal"] + 2 * config["outline_width"]
    )
    bg_height = (
        text_height + 2 * config["padding_vertical"] + 2 * config["outline_width"]
    )

    overlay_height = 0
    if overlay_image_path:
        overlay_image = Image.open(overlay_image_path).convert("RGBA")
        overlay_width, overlay_height = overlay_image.size

    total_height = bg_height + overlay_height - 14
    image = Image.new("RGBA", (config["fixed_width"], total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    x_offset = (config["fixed_width"] - bg_width) // 2
    create_rounded_rectangle_with_outline(
        draw,
        x_offset + config["outline_width"],
        overlay_height - 14 + config["outline_width"],
        x_offset + bg_width - config["outline_width"],
        total_height - config["outline_width"],
        config["border_radius"],
        bg_color,
        config["outline_color"],
        config["outline_width"],
    )

    text_x = x_offset + (bg_width - text_width) // 2
    text_y = (
        overlay_height
        - 14
        + config["outline_width"]
        + (bg_height - 2 * config["outline_width"] - text_height) // 2
    )
    draw.multiline_text(
        (text_x, text_y), wrapped_text, font=font, fill=text_color, align="center"
    )

    if overlay_image_path:
        overlay_x = x_offset + (bg_width - overlay_width) // 2
        image.paste(overlay_image, (overlay_x, 32), overlay_image)

    image.save(save_path)


def process_data(config):
    """Обрабатывает данные и создаёт изображения для вопросов и ответов."""
    os.makedirs(config["question_image_dir"], exist_ok=True)
    os.makedirs(config["answer_image_dir"], exist_ok=True)

    with open(config["data_path"], "r", encoding="utf-8") as file:
        data = json.load(file)

    for item in data["questions"]:
        number = item["number"]
        question_image_path = os.path.join(
            config["question_image_dir"], f"question_{number}.png"
        )
        answer_image_path = os.path.join(
            config["answer_image_dir"], f"answer_{number}.png"
        )
        number_image_path = os.path.join(
            config["number_image_dir"], f"number_{number}.png"
        )

        create_image_with_text(
            item["question"],
            config["question_bg_color"],
            config["question_text_color"],
            question_image_path,
            config,
            number_image_path,
        )
        create_image_with_text(
            item["answer"],
            config["answer_bg_color"],
            config["answer_text_color"],
            answer_image_path,
            config,
            config["success_image_path"],
        )


if __name__ == "__main__":
    process_data(CONFIG)
