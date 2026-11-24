// Selo genérico (cor + ícone + texto) para situações que não são status de registro.
export default function Selo({ tom, icone, children }) {
  return (
    <span className={`badge badge--${tom}`}>
      <span data-icone className="badge__icone" aria-hidden="true">{icone}</span>
      {children}
    </span>
  )
}
