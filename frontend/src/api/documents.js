// Все запросы идут по относительному пути /api/... —
// в контейнере его подхватывает Nginx и проксирует на backend (см. frontend/nginx.conf).
// Благодаря этому не нужен ни CORS, ни полный адрес backend — с точки зрения браузера
// это один и тот же домен.

const BASE_URL = "/api/documents/";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = `Ошибка ${response.status}`;
    try {
      const data = await response.json();
      detail = JSON.stringify(data);
    } catch {
      // тело ответа не JSON — оставляем стандартное сообщение
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchDocuments() {
  const response = await fetch(BASE_URL);
  return handleResponse(response);
}

export async function uploadDocument(file, onProgress) {
  // Через fetch нельзя получить прогресс загрузки — используем XMLHttpRequest,
  // чтобы показать пользователю процент загрузки для больших файлов.
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", BASE_URL);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Ошибка загрузки: ${xhr.status} ${xhr.responseText}`));
      }
    };

    xhr.onerror = () => reject(new Error("Сетевая ошибка при загрузке файла"));

    xhr.send(formData);
  });
}

export async function deleteDocument(id) {
  const response = await fetch(`${BASE_URL}${id}/`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`Не удалось удалить документ ${id}`);
  }
}

export async function processDocument(id) {
  const response = await fetch(`${BASE_URL}${id}/process/`, { method: "POST" });
  return handleResponse(response);
}
