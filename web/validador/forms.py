from django import forms

LIMITE_BYTES = 5 * 1024 * 1024


class UploadForm(forms.Form):
    pagamentos = forms.FileField(label="pagamentos.json")
    tribunal = forms.FileField(label="tribunal.csv")
    hub = forms.FileField(label="hub.csv")
    apresentacoes = forms.FileField(label="apresentacoes.json (opcional)", required=False)

    NOMES = {"pagamentos": "pagamentos.json", "tribunal": "tribunal.csv", "hub": "hub.csv",
             "apresentacoes": "apresentacoes.json"}

    def clean(self):
        dados = super().clean()
        for campo, arquivo in dados.items():
            if arquivo and arquivo.size > LIMITE_BYTES:
                self.add_error(campo, "arquivo maior que 5 MB")
        return dados

    def conteudos(self) -> dict[str, bytes]:
        return {self.NOMES[c]: a.read() for c, a in self.cleaned_data.items() if a}


class ResolucaoForm(forms.Form):
    registro_id = forms.CharField(max_length=120, widget=forms.HiddenInput)
    acao = forms.ChoiceField(choices=[("APROVAR", "Aprovar"), ("REJEITAR", "Rejeitar")])
    justificativa = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
