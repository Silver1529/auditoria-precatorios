// Valor antigo riscado → valor novo em destaque.
export default function DiffAntesDepois({ antes, depois }) {
  if (!antes && !depois) return null
  return (
    <span className="diff">
      {antes && <><span className="sr-only">antes: </span><del>{antes}</del></>}
      {antes && depois && <span className="diff__seta" aria-hidden="true">→</span>}
      {depois && <><span className="sr-only">depois: </span><ins>{depois}</ins></>}
    </span>
  )
}
