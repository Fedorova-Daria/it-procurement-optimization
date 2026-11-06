import os

ALLOWED_EXTENSIONS = (".xlsx", ".xls")
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def validate_excel_file(uploaded_file):
    """Проверяет загруженный файл: расширение и размер."""
    errors = []

    _, ext = os.path.splitext(uploaded_file.name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        errors.append(
            f"Недопустимый формат файла '{ext}'. "
            f"Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if uploaded_file.size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        errors.append(f"Файл слишком большой. Максимальный размер: {max_mb} МБ.")

    if uploaded_file.size == 0:
        errors.append("Файл пуст.")

    return errors