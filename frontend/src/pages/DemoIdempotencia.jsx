import { useState } from 'react'
import { api } from '../api/client'
import Carregando from '../components/Carregando'
import MensagemErro from '../components/MensagemErro'
import { formatarMoeda } from '../formato'

function Coluna({ titulo, subtitulo, dados, tom }) {
  const dobrou = dados.total_segunda !== dados.total_primeira
  return (
    <article className={`cartao demo demo--${tom}`}>
      <h3>{titulo}</h3>
      <p className="texto-suave">{subtitulo}</p>
      <dl className="demo__totais">
        <div><dt>Após a 1ª importação</dt><dd className="valor">{formatarMoeda(dados.total_primeira)}</dd></div>
        <div><dt>Após a 2ª importação do mesmo arquivo</dt>
          <dd className={`valor ${dobrou ? 'valor--antes' : 'valor--depois'}`}>{formatarMoeda(dados.total_segunda)}</dd></div>
      </dl>
      <p className={`aviso ${dobrou ? 'aviso--erro' : 'aviso--sucesso'}`}>
        <span aria-hidden="true">{dobrou ? '✕ ' : '✓ '}</span>
        {dobrou ? 'O total dobrou: os pagamentos foram somados de novo.' : 'O total não mudou: nada foi somado duas vezes.'}
      </p>
      <table className="tabela tabela--interna">
        <thead><tr><th>Processo</th><th className="num">1ª</th><th className="num">2ª</th></tr></thead>
        <tbody>{Object.keys(dados.primeira).map((p) => (
          <tr key={p}><td><code>{p}</code></td><td className="num">{formatarMoeda(dados.primeira[p])}</td>
            <td className="num">{formatarMoeda(dados.segunda[p])}</td></tr>))}</tbody>
      </table>
    </article>
  )
}

export default function DemoIdempotencia({ loteId }) {
  const [estado, setEstado] = useState({})
  async function executar() {
    setEstado({ carregando: true })
    try {
      setEstado({ dados: await api.demo(loteId) })
    } catch (erro) {
      setEstado({ erro })
    }
  }
  return (
    <section>
      <h2>Demonstração: importar o mesmo arquivo duas vezes</h2>
      <p className="aviso aviso--pendente" role="note"><span aria-hidden="true">⚠ </span>
        <strong>Simulação do comportamento inferido. O script original não foi fornecido.</strong>{' '}
        Hoje, quando a importação falha, o operador roda o script de novo com o mesmo arquivo. Aqui os mesmos eventos
        aceitos são gravados duas vezes em duas tabelas de teste, e tudo é desfeito no final.</p>
      <button type="button" className="botao botao--primario" onClick={executar} disabled={estado.carregando}>
        Importar duas vezes</button>
      {estado.carregando && <Carregando texto="Importando…" />}
      <MensagemErro erro={estado.erro} onTentarDeNovo={executar} />
      {estado.dados && (
        <div className="grade-demo">
          <Coluna titulo="Sem UNIQUE (modelo atual)" subtitulo="Tabela sem restrição de evento_id, como o banco de hoje."
            dados={estado.dados.sem_unique} tom="atual" />
          <Coluna titulo="Com UNIQUE (proposto)" subtitulo="Tabela com UniqueConstraint(evento_id)."
            dados={estado.dados.com_unique} tom="proposto" />
        </div>
      )}
    </section>
  )
}
