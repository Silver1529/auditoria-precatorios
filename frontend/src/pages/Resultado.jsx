import { useState } from 'react'
import { api } from '../api/client'
import CardContagem from '../components/CardContagem'
import GerarLote from '../components/GerarLote'
import { formatarMoeda } from '../formato'

export default function Resultado({ loteId, resumo, onAtualizar }) {
  const [gerando, setGerando] = useState(false)
  const [mensagem, setMensagem] = useState(null)
  const c = resumo.contagens

  async function gerar() {
    setGerando(true)
    setMensagem(null)
    try {
      const r = await api.gerar(loteId)
      setMensagem({ tipo: 'sucesso', texto: `Lote gerado: ${r.eventos} eventos, ${r.novos} novos. `
        + `${r.eventos - r.novos} já tinham sido importados e não foram somados de novo.` })
    } catch (e) {
      setMensagem({ tipo: 'erro', texto: e.message })
    } finally {
      setGerando(false)
      onAtualizar()
    }
  }

  return (
    <section>
      <h2>Resumo dos pagamentos</h2>
      <div className="grade-resultado">
        <div className="grade-cards">
          <CardContagem titulo="Analisados" valor={c.analisados} icone="∑" />
          <CardContagem titulo="OK" valor={c.validos} tom="ok" icone="✓" />
          <CardContagem titulo="Corrigidos" valor={c.corrigidos} tom="corrigido" icone="✎" />
          <CardContagem titulo="Descartados" valor={c.descartados} tom="descartado" icone="⊘"
            descricao={c.duplicados ? `${c.duplicados} duplicado(s)` : undefined} />
          <CardContagem titulo="Pendentes" valor={c.pendentes} tom="pendente" icone="!" />
        </div>
        <div className="cartao totais">
          <h3>Total pago</h3>
          <dl>
            <div><dt>Antes do tratamento <span className="texto-suave">(simulação)</span></dt>
              <dd className="valor valor--antes">{formatarMoeda(resumo.total_antes)}</dd></div>
            <div><dt>Depois do tratamento</dt><dd className="valor valor--depois">{formatarMoeda(resumo.total_depois)}</dd></div>
          </dl>
          <p className="texto-suave texto-pequeno">“Antes” simula o comportamento inferido do script atual (o original
            não foi fornecido): soma tudo, inclusive repetidos e estornos.</p>
        </div>
      </div>

      <h2>Total por processo</h2>
      <div className="rolagem">
        <table className="tabela">
          <thead><tr><th>Processo (como veio)</th><th className="num">Antes (simulação)</th><th className="num">Depois</th></tr></thead>
          <tbody>
            {resumo.totais.map((t) => (
              <tr key={t.processo || 'vazio'}>
                <td><code>{t.processo || '(vazio)'}</code></td>
                <td className="num">{formatarMoeda(t.antes)}</td>
                <td className="num">{formatarMoeda(t.depois)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <GerarLote resumo={resumo} onGerar={gerar} gerando={gerando} />
      {mensagem && <p className={`aviso aviso--${mensagem.tipo}`} role="status">{mensagem.texto}</p>}
    </section>
  )
}
