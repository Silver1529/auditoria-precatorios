export default function BannerEnvio({ liberado, motivo }) {
  if (liberado) {
    return (
      <div role="status" className="banner banner--liberado">
        <span className="banner__icone" aria-hidden="true">✓</span>
        <div><strong>Tudo validado, envio liberado</strong>
          <p>Nenhuma pendência ou erro. O lote pode ser gerado.</p></div>
      </div>
    )
  }
  return (
    <div role="alert" className="banner banner--bloqueado">
      <span className="banner__icone" aria-hidden="true">✕</span>
      <div><strong>{motivo}</strong>
        <p>Resolva as pendências para liberar o envio. Nada é enviado enquanto houver dúvida.</p></div>
    </div>
  )
}
