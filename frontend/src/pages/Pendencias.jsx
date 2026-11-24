import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import Carregando from '../components/Carregando'
import EstadoVazio from '../components/EstadoVazio'
import MensagemErro from '../components/MensagemErro'
import StatusBadge from '../components/StatusBadge'

function CartaoPendencia({ registro, loteId, onDecidido }) {
  const [justificativa, setJustificativa] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)
  const idJustificativa = `just-${registro.id}`

  async function decidir(decisao) {
    if (!justificativa.trim()) {
      setErro('Escreva a justificativa antes de decidir.')
      return
    }
    setEnviando(true)
    setErro('')
    try {
      const dados = await api.decidir(loteId, registro.id, decisao, justificativa)
      onDecidido(dados.resumo)
    } catch (e) {
      setErro(e.message)
      setEnviando(false)
    }
  }

  return (
    <article className={`cartao pendencia pendencia--${registro.severidade}`}>
      <header className="pendencia__topo">
        <StatusBadge status={registro.status} />
        <span className={`selo-severidade selo-severidade--${registro.severidade}`}>
          {registro.severidade === 'erro' ? 'Erro nos dados' : 'Precisa de decisão'}</span>
        <code>{registro.id}</code>
      </header>
      {registro.processo && <p className="texto-suave">Processo <code>{registro.processo}</code></p>}
      <p className="pendencia__mensagem">{registro.mensagem_usuario}</p>
      <p className="pendencia__corrigir"><strong>Como corrigir:</strong> {registro.como_corrigir}</p>
      <p className="texto-suave texto-pequeno">Regra {registro.regra_id} · arquivo {registro.evidencia.arquivo}</p>
      <label htmlFor={idJustificativa}>Justificativa (obrigatória)</label>
      <textarea id={idJustificativa} rows={2} value={justificativa} onChange={(e) => setJustificativa(e.target.value)}
        placeholder="Ex.: confirmado por e-mail com o tribunal em 20/11" />
      {erro && <p className="erro-campo" role="alert">{erro}</p>}
      <div className="acoes">
        <button type="button" className="botao botao--aprovar" disabled={enviando || !registro.pode_aprovar}
          title={registro.pode_aprovar ? undefined : 'Sem dados válidos para aprovar: só pode ser rejeitado'}
          onClick={() => decidir('aprovar')}><span aria-hidden="true">✓ </span>Aprovar</button>
        <button type="button" className="botao botao--rejeitar" disabled={enviando}
          onClick={() => decidir('rejeitar')}><span aria-hidden="true">✕ </span>Rejeitar</button>
        {!registro.pode_aprovar && <span className="texto-suave texto-pequeno">Só pode ser rejeitado: não há dados válidos para aprovar.</span>}
      </div>
    </article>
  )
}

export default function Pendencias({ loteId, onResumo }) {
  const [estado, setEstado] = useState({ carregando: true })

  const carregar = useCallback(async () => {
    try {
      const dados = await api.registros(loteId)
      setEstado({ registros: dados.registros })
    } catch (erro) {
      setEstado({ erro })
    }
  }, [loteId])

  useEffect(() => { carregar() }, [carregar])

  if (estado.carregando) return <Carregando />
  if (estado.erro) return <MensagemErro erro={estado.erro} onTentarDeNovo={carregar} />
  const abertas = estado.registros.filter((r) => r.aguardando_decisao)
  const decididas = estado.registros.filter((r) => r.resolucao)

  return (
    <section>
      <h2>Pendências <span className="contador">{abertas.length}</span></h2>
      <p className="texto-suave">Cada decisão exige justificativa e fica registrada com seu usuário e horário.
        Aprovar inclui o registro no lote; rejeitar o descarta.</p>
      {abertas.length === 0
        ? <EstadoVazio titulo="Nenhuma pendência">Todas as pendências foram decididas.</EstadoVazio>
        : <div className="grade-pendencias">
            {abertas.map((r) => (
              <CartaoPendencia key={r.id} registro={r} loteId={loteId}
                onDecidido={(resumo) => { onResumo(resumo); carregar() }} />
            ))}
          </div>}
      {decididas.length > 0 && (
        <>
          <h3>Já decididas</h3>
          <ul className="lista-decididas">
            {decididas.map((r) => (
              <li key={r.id}><StatusBadge status={r.status} /> <code>{r.id}</code>:{' '}
                {r.resolucao.decisao === 'aprovar' ? 'aprovado' : 'rejeitado'} por {r.resolucao.usuario}, “{r.resolucao.justificativa}”</li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
