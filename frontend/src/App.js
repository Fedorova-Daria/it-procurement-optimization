import { useEffect, useState } from "react";
import DocumentUpload from "./components/DocumentUpload";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Проверяю связь с backend...");

  useEffect(() => {
    // Относительный путь: в контейнере запрос уйдёт на Nginx (см. frontend/nginx.conf),
    // а тот перенаправит его на backend по внутренней docker-сети.
    fetch("/api/health/")
      .then((res) => res.json())
      .then((data) => setStatus(`Backend отвечает: ${JSON.stringify(data)}`))
      .catch(() => setStatus("Backend недоступен — проверьте docker compose logs backend"));
  }, []);

  return (
    <div className="app-container">
      <h1>Проект развёрнут</h1>
      <p className="backend-status">{status}</p>
      <DocumentUpload />
    </div>
  );
}

export default App;
