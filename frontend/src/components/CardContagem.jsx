export default function CardContagem({ titulo, valor, tom = 'neutro', icone, descricao }) {
  return (
    <div role="listitem" className={`card-contagem card-contagem--${tom}`}>
      <span className="card-contagem__titulo">
        {icone && <span aria-hidden="true">{icone} </span>}{titulo}
      </span>
      <strong className="card-contagem__valor">{valor}</strong>
      {descricao && <span className="card-contagem__descricao">{descricao}</span>}
    </div>
  )
}
