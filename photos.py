import os
import json
import requests

# Конфигурация
API_KEY = "26357884-95e2f76db78602d2b5dc0e5df"
API_URL = "https://pixabay.com/api/"
JSON_PATH = "./input/data/data.json"  # Путь к JSON-файлу
DOWNLOAD_FOLDER = "photos"  # Папка для сохранения фотографий

# Создание папки для загрузки
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


def extract_keywords_from_json(json_path):
    """Извлекает массивы ключевых слов из JSON-файла."""
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return [
        (entry.get("keywords", []), entry.get("number"))
        for entry in data.get("questions", [])
    ]


def sanitize_query(query):
    """Удаляет спецсимволы из строки запроса, чтобы избежать ошибок API."""
    return "".join(c for c in query if c.isalnum() or c.isspace()).strip()


def download_photo_for_keywords(keywords, question_number, download_folder):
    """Ищет и скачивает одну фотографию по массиву ключевых слов."""
    for keyword in keywords:
        sanitized_query = sanitize_query(keyword)
        params = {
            "key": API_KEY,
            "q": sanitized_query,
            "image_type": "photo",
            "per_page": 3,  # Загружаем только одно изображение
        }

        response = requests.get(API_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])

            if hits:
                image_url = hits[0]["largeImageURL"]
                try:
                    image_data = requests.get(image_url).content
                    # Формируем имя файла на основе номера вопроса
                    file_name = os.path.join(
                        download_folder, f"question_{question_number}.jpg"
                    )
                    with open(file_name, "wb") as f:
                        f.write(image_data)
                    print(
                        f"Скачано фото для вопроса #{question_number} (ключевое слово: '{keyword}'): {file_name}"
                    )
                    return  # Если фото найдено, выходим из цикла
                except Exception as e:
                    print(f"Ошибка при скачивании {image_url}: {e}")
            else:
                print(f"Фото по ключевому слову '{keyword}' не найдены.")
        else:
            print(
                f"Ошибка API для ключевого слова '{keyword}': {response.status_code}, {response.text}"
            )

    print(f"Не удалось найти фото для вопроса #{question_number}.")


def main():
    # Извлекаем ключевые слова и номера вопросов из JSON-файла
    questions = extract_keywords_from_json(JSON_PATH)
    print(f"Найдено вопросов для обработки: {len(questions)}")

    # Скачиваем фотографии для каждого вопроса
    for keywords, question_number in questions:
        download_photo_for_keywords(keywords, question_number, DOWNLOAD_FOLDER)


if __name__ == "__main__":
    main()
