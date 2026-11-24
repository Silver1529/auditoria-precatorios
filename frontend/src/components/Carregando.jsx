export default function Carregando({ texto = 'Carregando…' }) {
  return (
    <div className="estado estado--carregando" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{texto}</span>
    </div>
  )
}
