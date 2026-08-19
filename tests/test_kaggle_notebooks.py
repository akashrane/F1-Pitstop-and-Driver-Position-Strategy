import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_ROOT = ROOT / "notebooks" / "kaggle"


def test_four_public_kaggle_notebooks_have_valid_metadata():
    folders = sorted(path for path in NOTEBOOK_ROOT.iterdir() if path.is_dir())
    assert len(folders) == 4
    ids = set()
    for folder in folders:
        metadata = json.loads((folder / "kernel-metadata.json").read_text(encoding="utf-8"))
        notebook = json.loads((folder / metadata["code_file"]).read_text(encoding="utf-8"))
        assert metadata["id"].startswith("akashrane2609/")
        assert metadata["id"] not in ids
        ids.add(metadata["id"])
        assert metadata["is_private"] is False
        assert metadata["enable_internet"] is False
        assert metadata["enable_gpu"] is False
        assert metadata["dataset_sources"] == ["akashrane2609/formula-1-pit-stop-dataset"]
        assert notebook["nbformat"] == 4
        assert len(notebook["cells"]) >= 8
        sources = "\n".join(cell["source"] for cell in notebook["cells"])
        assert "/kaggle/input/formula-1-pit-stop-dataset" in sources
        assert "classified_position" not in sources.split("numeric =", 1)[-1].split("prep =", 1)[0] if "numeric =" in sources else True
