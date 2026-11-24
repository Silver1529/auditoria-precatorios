"""Adaptador da porta RepositorioLote para o ORM (Postgres no Render, SQLite local)."""
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Sum, When

from precatorios.application.portas import PrecatorioRef
from precatorios.domain.evento import EventoPagamento
from precatorios.domain.processo import formatar_processo
from validador.models import Pagamento, Precatorio


class RepositorioDjango:
    def salvar_precatorio(self, precatorio: PrecatorioRef) -> None:
        Precatorio.objects.get_or_create(
            numero_processo=precatorio.processo,
            defaults={"ente_devedor": precatorio.ente_devedor, "valor_face": precatorio.valor_face},
        )

    def salvar_evento_se_novo(self, evento: EventoPagamento) -> bool:
        _, criado = Pagamento.objects.get_or_create(
            evento_id=evento.evento_id,
            defaults={
                "precatorio": Precatorio.objects.get(numero_processo=evento.processo),
                "tipo": evento.tipo.value, "valor": evento.valor, "pago_em": evento.pago_em,
            },
        )
        return criado

    def total_por_processo(self) -> dict[str, Decimal]:
        com_sinal = Case(When(tipo="estorno", then=-F("valor")), default=F("valor"),
                         output_field=DecimalField(max_digits=15, decimal_places=2))
        linhas = (Pagamento.objects.values("precatorio__numero_processo")
                  .annotate(total=Sum(com_sinal)).order_by("precatorio__numero_processo"))
        return {formatar_processo(l["precatorio__numero_processo"]): l["total"] for l in linhas}
