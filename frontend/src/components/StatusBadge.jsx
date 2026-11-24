// Status com cor + ícone + texto: nunca só a cor.
const ESTILOS = {
  OK: { texto: 'OK', icone: '✓' },
  CORRIGIDO: { texto: 'Corrigido', icone: '✎' },
  DESCARTADO: { texto: 'Descartado', icone: '⊘' },
  PENDENTE: { texto: 'Pendente', icone: '!' },
}

export default function StatusBadge({ status }) {
  const estilo = ESTILOS[status] ?? { texto: status, icone: '?' }
  return (
    <span className={`badge badge--${String(status).toLowerCase()}`}>
      <span data-icone className="badge__icone" aria-hidden="true">{estilo.icone}</span>
      {estilo.texto}
    </span>
  )
}
