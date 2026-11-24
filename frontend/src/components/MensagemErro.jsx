export default function MensagemErro({ erro, onTentarDeNovo }) {
  if (!erro) return null
  return (
    <div className="estado estado--erro" role="alert">
      <span className="estado__icone" aria-hidden="true">✕</span>
      <strong>{erro.message ?? String(erro)}</strong>
      {onTentarDeNovo && <button type="button" className="botao botao--secundario" onClick={onTentarDeNovo}>
        Tentar de novo</button>}
    </div>
  )
}
