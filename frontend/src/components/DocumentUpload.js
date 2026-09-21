import { useCallback, useEffect, useRef, useState } from "react";
import { deleteDocument, fetchDocuments, processDocument, uploadDocument } from "../api/documents";

const STATUS_LABELS = {
  uploaded: "Загружен",
  processing: "Обрабатывается",
  done: "Обработан",
  error: "Ошибка",
};

function StatusBadge({ status }) {
  return <span className={`status-badge status-${status}`}>{STATUS_LABELS[status] || status}</span>;
}

export default function DocumentUpload() {
  const [documents, setDocuments] = useState([]);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [listError, setListError] = useState(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null); // null = не загружается
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  // id документов, которые сейчас обрабатываются (чтобы не жать "Обработать" второй раз)
  const [processingIds, setProcessingIds] = useState(new Set());
  const [expandedId, setExpandedId] = useState(null); // какой документ показывает извлечённый текст

  const loadDocuments = useCallback(async () => {
    setIsLoadingList(true);
    setListError(null);
    try {
      const data = await fetchDocuments();
      // DRF без пагинации отдаёт просто массив; с пагинацией — объект с полем results
      setDocuments(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setListError(err.message);
    } finally {
      setIsLoadingList(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  function handleFileChange(event) {
    setSelectedFile(event.target.files[0] || null);
    setUploadError(null);
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!selectedFile) return;

    setUploadProgress(0);
    setUploadError(null);
    try {
      await uploadDocument(selectedFile, setUploadProgress);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadDocuments();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploadProgress(null);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((doc) => doc.id !== id));
    } catch (err) {
      setListError(err.message);
    }
  }

  async function handleProcess(id) {
    setProcessingIds((prev) => new Set(prev).add(id));
    setDocuments((prev) => prev.map((doc) => (doc.id === id ? { ...doc, status: "processing" } : doc)));
    try {
      const updated = await processDocument(id);
      setDocuments((prev) => prev.map((doc) => (doc.id === id ? updated : doc)));
      setExpandedId(id);
    } catch (err) {
      setListError(err.message);
      setDocuments((prev) => prev.map((doc) => (doc.id === id ? { ...doc, status: "error" } : doc)));
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  return (
    <div className="upload-section">
      <h2>Загрузка документа</h2>

      <form onSubmit={handleUpload} className="upload-form">
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.docx"
        />
        <button type="submit" disabled={!selectedFile || uploadProgress !== null}>
          {uploadProgress !== null ? `Загрузка... ${uploadProgress}%` : "Загрузить"}
        </button>
      </form>

      {uploadError && <p className="error-text">Ошибка: {uploadError}</p>}

      <div className="documents-header">
        <h2>Документы</h2>
        <button type="button" onClick={loadDocuments} disabled={isLoadingList}>
          Обновить
        </button>
      </div>

      {listError && <p className="error-text">Ошибка: {listError}</p>}
      {isLoadingList && documents.length === 0 && <p>Загружаю список...</p>}
      {!isLoadingList && documents.length === 0 && !listError && <p>Пока нет ни одного документа.</p>}

      <ul className="documents-list">
        {documents.map((doc) => {
          const isProcessing = processingIds.has(doc.id) || doc.status === "processing";
          const isExpanded = expandedId === doc.id;
          return (
            <li key={doc.id} className="document-item-wrapper">
              <div className="document-item">
                <a href={doc.file} target="_blank" rel="noreferrer">
                  {doc.file.split("/").pop()}
                </a>
                <StatusBadge status={doc.status} />
                <span className="document-date">{new Date(doc.created_at).toLocaleString()}</span>

                {doc.status !== "done" && (
                  <button type="button" disabled={isProcessing} onClick={() => handleProcess(doc.id)}>
                    {isProcessing ? "Обрабатывается..." : "Обработать"}
                  </button>
                )}
                {doc.status === "done" && (
                  <button type="button" onClick={() => setExpandedId(isExpanded ? null : doc.id)}>
                    {isExpanded ? "Скрыть текст" : "Показать текст"}
                  </button>
                )}
                <button type="button" className="delete-btn" onClick={() => handleDelete(doc.id)}>
                  Удалить
                </button>
              </div>
              {isExpanded && doc.extracted_text && (
                <pre className="extracted-text">{doc.extracted_text}</pre>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
