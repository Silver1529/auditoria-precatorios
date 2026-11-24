export default function EstadoVazio({ titulo, children }) {
  return (
    <div className="estado estado--vazio">
      <span className="estado__icone" aria-hidden="true">○</span>
      <strong>{titulo}</strong>
      {children && <p>{children}</p>}
    </div>
  )
}
