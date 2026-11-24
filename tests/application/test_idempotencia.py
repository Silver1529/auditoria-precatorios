from conftest import resolver_todas
from precatorios.adapters.repositorio_memoria import RepositorioMemoria, RepositorioMemoriaSemUnicidade
from precatorios.application.gerar_lote import gerar_lote, importar_lote


def test_importar_duas_vezes_da_o_mesmo_total(analise, relogio):
    lote = gerar_lote(resolver_todas(analise, relogio))
    repo = RepositorioMemoria()
    novos = importar_lote(repo, lote)
    total_uma_vez = repo.total_por_processo()
    assert importar_lote(repo, lote) == 0
    assert repo.total_por_processo() == total_uma_vez
    assert novos == len(lote.eventos)


def test_sem_unicidade_a_reimportacao_dobra_o_total(analise, relogio):
    """Simulação do comportamento inferido (script original não fornecido)."""
    lote = gerar_lote(resolver_todas(analise, relogio))
    repo = RepositorioMemoriaSemUnicidade()
    importar_lote(repo, lote)
    uma_vez = repo.total_por_processo()
    importar_lote(repo, lote)
    assert repo.total_por_processo() == {k: v * 2 for k, v in uma_vez.items()}


def test_analise_e_deterministica(dir_fixtures):
    from precatorios.adapters.leitores import LeitorArquivosBytes
    from precatorios.application.analise import executar_analise

    a = executar_analise(LeitorArquivosBytes.de_diretorio(dir_fixtures))
    b = executar_analise(LeitorArquivosBytes.de_diretorio(dir_fixtures))
    assert a.decisoes == b.decisoes
