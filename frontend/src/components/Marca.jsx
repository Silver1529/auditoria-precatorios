// Marca: um auto (documento) com selo de conferido.
export function IconeMarca({ tamanho = 32 }) {
  return (
    <svg className="marca__icone" width={tamanho} height={tamanho} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path d="M7 3h13l6 6v20H7z" fill="currentColor" />
      <path d="M20 3v6h6" className="marca__dobra" />
      <circle cx="16.5" cy="19" r="6" fill="none" stroke="var(--sobre-marca)" strokeWidth="2" />
      <path d="m13.8 19 1.9 1.9 3.6-3.8" fill="none" stroke="var(--sobre-marca)" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function Marca() {
  return (
    <span className="marca">
      <IconeMarca />
      <span className="marca__nome">Validador<span className="marca__complemento"> de precatórios</span></span>
    </span>
  )
}
