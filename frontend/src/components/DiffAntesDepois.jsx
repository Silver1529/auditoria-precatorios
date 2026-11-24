// Valor antigo riscado → valor novo em destaque.
// Sem valor novo (ex.: pendência), o valor recebido aparece sem risco: nada foi apagado.
export default function DiffAntesDepois({ antes, depois }) {
  if (!antes && !depois) return null
  if (antes && !depois) {
    return (
      <span className="diff diff--recebido">
        <span className="sr-only">valor recebido: </span><code>{antes}</code>
      </span>
    )
  }
  return (
    <span className="diff">
      {antes && <><span className="sr-only">antes: </span><del>{antes}</del></>}
      {antes && <span className="diff__seta" aria-hidden="true">→</span>}
      <span className="sr-only">depois: </span><ins>{depois}</ins>
    </span>
  )
}
