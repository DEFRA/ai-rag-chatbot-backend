from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_uploader_callback_success(monkeypatch):
    # Mock S3 client
    mock_s3 = MagicMock()
    monkeypatch.setattr("boto3.client", lambda *_, **__: mock_s3)

    # Mock download_fileobj to write a test file
    def fake_download_fileobj(_bucket, _key, fileobj):
        fileobj.write(b"test content")

    mock_s3.download_fileobj.side_effect = fake_download_fileobj

    # Patch vector_store_grants
    with patch("app.cdp_uploader.router.vector_store_grants") as mock_vs:
        mock_vs.add_documents = MagicMock()
        # Prepare request data
        data = {
            "form": {
                "file1": {
                    "fileStatus": "complete",
                    "s3Bucket": "my-bucket",
                    "s3Key": "test.txt",
                }
            }
        }
        client = TestClient(app)
        response = client.post("/uploader-callback", json=data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["files_ingested"] == 1
        assert mock_vs.add_documents.called


def test_uploader_callback_no_files():
    client = TestClient(app)
    data = {"form": {}}
    response = client.post("/uploader-callback", json=data)
    assert response.status_code == 400
    assert response.json()["detail"] == "No completed files in callback."
