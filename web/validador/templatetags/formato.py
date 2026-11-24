from django import template

from precatorios.adapters.saida import formatar_moeda

register = template.Library()


@register.filter
def moeda(valor):
    return formatar_moeda(valor)
