"""Leitores de arquivo: transformam bytes em estruturas simples, sem aplicar regra de negócio."""
from precatorios.adapters.leitores.arquivos import ArquivoAusente, ArquivoIlegivel, LeitorArquivosBytes
from precatorios.adapters.leitores.csv_leitor import LeiauteInvalido, ler_csv_precatorios
from precatorios.adapters.leitores.json_leitor import JsonInvalido, ler_json

__all__ = [
    "ArquivoAusente", "ArquivoIlegivel", "JsonInvalido", "LeiauteInvalido", "LeitorArquivosBytes", "ler_csv_precatorios", "ler_json",
]
