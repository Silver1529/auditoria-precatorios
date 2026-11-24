"""Os arquivos de entrada nunca são alterados pelo pipeline (SHA-256 antes e depois)."""
import hashlib
from pathlib import Path

import pytest

from conftest import FIXTURES, RAIZ
from precatorios.adapters.cli import main

ORIGINAIS = RAIZ / "originais"


def _hashes(pasta: Path) -> dict[str, str]:
    return {
        str(p.relative_to(pasta)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(pasta.rglob("*")) if p.is_file()
    }


def test_fixtures_intactas(tmp_path):
    antes = _hashes(FIXTURES)
    main(["--dados", str(FIXTURES), "--saida", str(tmp_path)])
    assert _hashes(FIXTURES) == antes


@pytest.mark.skipif(not ORIGINAIS.exists(), reason="pasta originais/ não está presente nesta cópia")
def test_originais_intactos(tmp_path):
    antes = _hashes(ORIGINAIS)
    for dados in {p.parent for p in ORIGINAIS.rglob("pagamentos.json")}:
        main(["--dados", str(dados), "--saida", str(tmp_path)])
    assert _hashes(ORIGINAIS) == antes
