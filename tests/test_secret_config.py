from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services.secret_config import load_secret


class SecretConfigTests(unittest.TestCase):

    def test_loads_secret_from_local_file(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "secrets.toml"
            secret_file.write_text(
                'DATABASE_URL = "postgresql://local-test"\n',
                encoding="utf-8",
            )

            self.assertEqual(
                load_secret("DATABASE_URL", secret_file),
                "postgresql://local-test",
            )

    @patch(
        "services.secret_config._read_streamlit_secret",
        return_value="cloud-test-value",
    )
    def test_loads_secret_from_streamlit_cloud(self, mock_reader):
        with TemporaryDirectory() as directory:
            missing_file = Path(directory) / "missing.toml"

            self.assertEqual(
                load_secret("DATABASE_URL", missing_file),
                "cloud-test-value",
            )

        mock_reader.assert_called_once_with("DATABASE_URL")

    def test_rejects_missing_secret(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "secrets.toml"
            secret_file.write_text(
                'OTHER_KEY = "value"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "DATABASE_URL"):
                load_secret("DATABASE_URL", secret_file)


if __name__ == "__main__":
    unittest.main()
