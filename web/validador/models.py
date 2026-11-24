"""Models.

- Precatorio e Pagamento espelham sql/schema_atual.sql, com as proteções que faltam lá
  (UNIQUE em evento_id e CHECK de formato do processo).
- Analise, ArquivoEnviado, ResolucaoRegistro e LoteGerado guardam o estado da tela.
  Os arquivos ficam no banco (BinaryField) porque o disco do Render é efêmero.
- DemoPagamento* existem só para a página de demonstração de idempotência.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

TIPOS = [("pagamento", "pagamento"), ("estorno", "estorno")]


class Precatorio(models.Model):
    numero_processo = models.CharField(max_length=20, unique=True)
    ente_devedor = models.TextField()
    valor_face = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(numero_processo__regex=r"^[0-9]{20}$"),
                                   name="precatorio_numero_20_digitos"),
        ]

    def __str__(self) -> str:
        return self.numero_processo


class Pagamento(models.Model):
    precatorio = models.ForeignKey(Precatorio, on_delete=models.PROTECT, related_name="pagamentos")
    evento_id = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    pago_em = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["evento_id"], name="pagamento_evento_id_unico"),
            models.CheckConstraint(condition=Q(valor__gt=0), name="pagamento_valor_positivo"),
            models.CheckConstraint(condition=Q(tipo__in=["pagamento", "estorno"]), name="pagamento_tipo_valido"),
        ]


class Analise(models.Model):
    criada_em = models.DateTimeField(auto_now_add=True)
    criada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-id"]


class ArquivoEnviado(models.Model):
    analise = models.ForeignKey(Analise, on_delete=models.CASCADE, related_name="arquivos")
    nome = models.CharField(max_length=40)
    conteudo = models.BinaryField()
    sha256 = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["analise", "nome"], name="arquivo_unico_por_analise")]


class ResolucaoRegistro(models.Model):
    analise = models.ForeignKey(Analise, on_delete=models.CASCADE, related_name="resolucoes")
    registro_id = models.CharField(max_length=120)
    acao = models.CharField(max_length=10, choices=[("APROVAR", "Aprovar"), ("REJEITAR", "Rejeitar")])
    justificativa = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    em = models.DateTimeField()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["analise", "registro_id"], name="uma_resolucao_por_registro"),
            models.CheckConstraint(condition=~Q(justificativa=""), name="resolucao_com_justificativa"),
        ]


class LoteGerado(models.Model):
    analise = models.ForeignKey(Analise, on_delete=models.CASCADE, related_name="lotes")
    gerado_em = models.DateTimeField(auto_now_add=True)
    gerado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    eventos = models.PositiveIntegerField()
    novos = models.PositiveIntegerField()

    class Meta:
        ordering = ["-id"]


class DemoPagamentoBase(models.Model):
    evento_id = models.CharField(max_length=100)
    processo = models.CharField(max_length=20)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    pago_em = models.DateField()

    class Meta:
        abstract = True


class DemoPagamentoSemUnique(DemoPagamentoBase):
    """Simulação do comportamento inferido: como no schema atual, sem UNIQUE em evento_id."""


class DemoPagamentoComUnique(DemoPagamentoBase):
    class Meta:
        constraints = [models.UniqueConstraint(fields=["evento_id"], name="demo_evento_id_unico")]
