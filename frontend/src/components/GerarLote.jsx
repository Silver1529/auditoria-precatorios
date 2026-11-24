// O botão só reflete o que a API diz (envio_liberado). A trava real fica no servidor (409).
export default function GerarLote({ resumo, onGerar, gerando = false }) {
  const bloqueado = !resumo.envio_liberado
  return (
    <section className="gerar-lote" aria-labelledby="titulo-gerar">
      <h2 id="titulo-gerar">Gerar lote</h2>
      <button type="button" className="botao botao--primario" disabled={bloqueado || gerando}
        aria-describedby={bloqueado ? 'motivo-bloqueio' : undefined} onClick={onGerar}>
        {gerando ? 'Gerando…' : 'Gerar lote'}
      </button>
      {bloqueado && (
        <div id="motivo-bloqueio" className="gerar-lote__motivo">
          <p><strong>{resumo.motivo_bloqueio}.</strong> O botão libera quando cada item for decidido na aba
            Pendências.</p>
          <details>
          <summary>Ver o que falta ({resumo.bloqueios.length})</summary>
          <ul>
            {resumo.bloqueios.map((b) => (
              <li key={b.registro_id} className={`bloqueio bloqueio--${b.severidade}`}>
                <span aria-hidden="true">{b.severidade === 'erro' ? '✕' : '!'}</span>{' '}
                <code>{b.registro_id}</code>: {b.mensagem_usuario}{' '}
                <em>{b.como_corrigir}</em>
              </li>
            ))}
          </ul>
          </details>
        </div>
      )}
    </section>
  )
}
