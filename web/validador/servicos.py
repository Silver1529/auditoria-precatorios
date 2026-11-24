"""Composição: liga o ORM aos casos de uso. Nenhuma regra de validação mora aqui."""
from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from precatorios.adapters.leitores import LeitorArquivosBytes
from precatorios.adapters.relogio import RelogioSistema
from precatorios.application.analise import Analise as AnaliseDominio
from precatorios.application.analise import executar_analise, somar_por_processo
from precatorios.application.gerar_lote import Lote, gerar_lote, importar_lote
from precatorios.application.resolver_pendencia import resolver_pendencia
from precatorios.domain.processo import formatar_processo
from precatorios.domain.resultado import Acao, Resolucao
from validador.models import (
    Analise,
    ArquivoEnviado,
    DemoPagamentoComUnique,
    DemoPagamentoSemUnique,
    LoteGerado,
    ResolucaoRegistro,
)
from validador.repositorio import RepositorioDjango

log = logging.getLogger(__name__)


def criar_analise(arquivos: dict[str, bytes], usuario) -> Analise:
    """Valida a leitura dos arquivos antes de gravar; erro de leitura não cria análise."""
    executar_analise(LeitorArquivosBytes(arquivos))
    with transaction.atomic():
        analise = Analise.objects.create(criada_por=usuario)
        for nome, conteudo in arquivos.items():
            ArquivoEnviado.objects.create(analise=analise, nome=nome, conteudo=conteudo,
                                          sha256=hashlib.sha256(conteudo).hexdigest())
    log.info("análise %s criada por %s", analise.id, usuario)
    return analise


def carregar(analise: Analise) -> AnaliseDominio:
    """Reexecuta a análise a partir dos arquivos gravados e reaplica as decisões humanas."""
    arquivos = {a.nome: bytes(a.conteudo) for a in analise.arquivos.all()}
    dominio = executar_analise(LeitorArquivosBytes(arquivos))
    for r in analise.resolucoes.all():
        dominio = dominio.com_resolucao(Resolucao(r.registro_id, Acao(r.acao), r.justificativa,
                                                  r.usuario.get_username(), r.em))
    return dominio


def resolver(analise: Analise, registro_id: str, acao: str, justificativa: str | None, usuario) -> AnaliseDominio:
    nova = resolver_pendencia(carregar(analise), registro_id, Acao(acao), justificativa,
                              usuario.get_username(), RelogioSistema())
    resolucao = nova.resolucao_de(registro_id)
    ResolucaoRegistro.objects.create(analise=analise, registro_id=registro_id, acao=resolucao.acao.value,
                                     justificativa=resolucao.justificativa, usuario=usuario, em=resolucao.em)
    return nova


def gerar_e_importar(analise: Analise, usuario) -> tuple[Lote, int]:
    lote = gerar_lote(carregar(analise))  # LoteBloqueado sobe para a view
    with transaction.atomic():
        novos = importar_lote(RepositorioDjango(), lote)
        LoteGerado.objects.create(analise=analise, gerado_por=usuario, eventos=len(lote.eventos), novos=novos)
    return lote, novos


def demonstrar_idempotencia(analise: Analise) -> dict:
    """SIMULAÇÃO DO COMPORTAMENTO INFERIDO: o script original não foi fornecido.

    Importa os mesmos eventos aceitos duas vezes em duas tabelas reais: uma sem UNIQUE (como o
    schema atual) e outra com UniqueConstraint(evento_id). Tudo roda numa transação desfeita no
    fim, então a demonstração não deixa dados gravados.
    """
    eventos = carregar(analise).eventos_aceitos()
    rodadas: dict[str, list[dict[str, Decimal]]] = {"sem_unique": [], "com_unique": []}
    with transaction.atomic():
        for _rodada in range(2):
            for e in eventos:
                campos = {"processo": e.processo, "tipo": e.tipo.value, "valor": e.valor, "pago_em": e.pago_em}
                DemoPagamentoSemUnique.objects.create(evento_id=e.evento_id, **campos)
                DemoPagamentoComUnique.objects.get_or_create(evento_id=e.evento_id, defaults=campos)
            rodadas["sem_unique"].append(_totais(DemoPagamentoSemUnique))
            rodadas["com_unique"].append(_totais(DemoPagamentoComUnique))
        transaction.set_rollback(True)
    return {
        "aviso": AVISO_SIMULACAO,
        "eventos": len(eventos),
        "esperado": somar_por_processo(eventos),
        **{modelo: _rodadas(r) for modelo, r in rodadas.items()},
    }


AVISO_SIMULACAO = "Simulação do comportamento inferido. O script original não foi fornecido."


def _rodadas(totais: list[dict[str, Decimal]]) -> dict:
    primeira, segunda = totais
    return {"primeira": primeira, "segunda": segunda,
            "total_primeira": sum(primeira.values(), Decimal("0.00")),
            "total_segunda": sum(segunda.values(), Decimal("0.00"))}


def _totais(modelo) -> dict[str, Decimal]:
    totais: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for linha in modelo.objects.all():
        totais[formatar_processo(linha.processo)] += -linha.valor if linha.tipo == "estorno" else linha.valor
    return dict(sorted(totais.items()))
