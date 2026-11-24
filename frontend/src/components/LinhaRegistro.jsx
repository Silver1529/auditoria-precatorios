import { useState } from 'react'
import DiffAntesDepois from './DiffAntesDepois'
import StatusBadge from './StatusBadge'

// Linha expansível: o que aconteceu, campo, antes → depois, regra e como corrigir.
export default function LinhaRegistro({ registro }) {
  const [aberta, setAberta] = useState(false)
  const idDetalhe = `detalhe-${registro.id}`
  return (
    <>
      <tr className={`linha linha--${registro.status.toLowerCase()}`}>
        <td>
          <button type="button" className="linha__expandir" aria-expanded={aberta} aria-controls={idDetalhe}
            onClick={() => setAberta(!aberta)}>
            <span aria-hidden="true">{aberta ? '▾' : '▸'}</span>
            <span className="sr-only">{aberta ? 'Recolher' : 'Ver detalhes de'}</span> {registro.id}
          </button>
        </td>
        <td><code>{registro.chave || '(vazio)'}</code></td>
        <td><StatusBadge status={registro.status} /></td>
        <td className="linha__mensagem">{registro.mensagem_usuario}</td>
        <td><DiffAntesDepois antes={registro.antes} depois={registro.depois} /></td>
      </tr>
      {aberta && (
        <tr id={idDetalhe} className="linha-detalhe">
          <td colSpan={5}>
            <dl className="detalhe">
              <dt>O que aconteceu</dt><dd>{registro.mensagem_usuario}</dd>
              {registro.como_corrigir && <><dt>Como corrigir</dt><dd>{registro.como_corrigir}</dd></>}
              <dt>Onde</dt>
              <dd>Arquivo <code>{registro.evidencia.arquivo}</code>, registro <code>{registro.evidencia.registro}</code>
                {registro.evidencia.campo && <>, campo <code>{registro.evidencia.campo}</code></>}</dd>
              {registro.resolucao && <><dt>Decisão</dt>
                <dd>{registro.resolucao.decisao === 'aprovar' ? 'Aprovado' : 'Rejeitado'} por {registro.resolucao.usuario}:
                  “{registro.resolucao.justificativa}”</dd></>}
            </dl>
            {registro.ocorrencias.length > 0 && (
              <table className="tabela tabela--interna">
                <caption>Regras aplicadas</caption>
                <thead><tr><th>Regra</th><th>Campo</th><th>Antes → depois</th><th>Explicação</th></tr></thead>
                <tbody>
                  {registro.ocorrencias.map((o, i) => (
                    <tr key={`${o.regra_id}-${i}`}>
                      <td><code>{o.regra_id}</code></td>
                      <td>{o.campo || '—'}</td>
                      <td><DiffAntesDepois antes={o.antes} depois={o.depois} /></td>
                      <td>{o.mensagem_usuario}{o.como_corrigir && <><br /><em>{o.como_corrigir}</em></>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <details className="evidencia">
              <summary>Dados originais do registro</summary>
              <dl>{Object.entries(registro.evidencia.valores).map(([k, v]) => (
                <div key={k}><dt>{k}</dt><dd><code>{v}</code></dd></div>))}</dl>
            </details>
          </td>
        </tr>
      )}
    </>
  )
}
