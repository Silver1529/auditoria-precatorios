// Status do envio em forma de carimbo (cor + texto + forma), com a explicação ao lado.
export default function BannerEnvio({ liberado, motivo }) {
  if (liberado) {
    return (
      <div role="status" className="banner banner--liberado">
        <span className="carimbo" aria-hidden="true">Liberado</span>
        <div className="banner__texto"><strong>Tudo validado, envio liberado</strong>
          <p>Nenhuma pendência ou erro. O lote pode ser gerado.</p></div>
      </div>
    )
  }
  return (
    <div role="alert" className="banner banner--bloqueado">
      <span className="carimbo" aria-hidden="true">Bloqueado</span>
      <div className="banner__texto"><strong>{motivo}</strong>
        <p>Nada é enviado enquanto houver dúvida. Decida cada pendência para liberar.</p></div>
    </div>
  )
}
