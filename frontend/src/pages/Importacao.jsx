import { useState } from 'react'
import { api } from '../api/client'
import Carregando from '../components/Carregando'
import { formatarTamanho } from '../formato'

const ARQUIVOS = [
  { campo: 'pagamentos', nome: 'pagamentos.json', descricao: 'Eventos de pagamento enviados pelo tribunal', obrigatorio: true },
  { campo: 'tribunal', nome: 'tribunal.csv', descricao: 'Lista de precatórios do tribunal', obrigatorio: true },
  { campo: 'hub', nome: 'hub.csv', descricao: 'Exportação do nosso sistema', obrigatorio: true },
  { campo: 'apresentacoes', nome: 'apresentacoes.json', descricao: 'Datas de apresentação dos precatórios', obrigatorio: false },
]

function IconeArquivo() {
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 4h11l6 6v20H9z" /><path d="M20 4v6h6" /><path d="M17.5 25v-9m-3.5 3.5 3.5-3.5 3.5 3.5" />
    </svg>
  )
}

function IconeOk() {
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none" stroke="currentColor" strokeWidth="2.2"
      strokeLinecap="round" strokeLinejoin="round">
      <circle cx="17" cy="17" r="12" /><path d="m11.5 17.5 3.8 3.8 7.2-7.6" />
    </svg>
  )
}

function ZonaArquivo({ config, arquivo, erro, onEscolher }) {
  const [arrastando, setArrastando] = useState(false)
  const id = `arquivo-${config.campo}`
  return (
    <div className={`zona ${arrastando ? 'zona--ativa' : ''} ${arquivo ? 'zona--preenchida' : ''} ${erro ? 'zona--erro' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setArrastando(true) }}
      onDragLeave={() => setArrastando(false)}
      onDrop={(e) => { e.preventDefault(); setArrastando(false); onEscolher(e.dataTransfer.files[0]) }}>
      <label htmlFor={id} className="zona__rotulo">
        <span className="zona__icone" aria-hidden="true">{arquivo ? <IconeOk /> : <IconeArquivo />}</span>
        <strong>{config.nome}</strong>{!config.obrigatorio && <span className="texto-suave"> (opcional)</span>}
        <span className="texto-suave texto-pequeno">{config.descricao}</span>
        {arquivo
          ? <span className="zona__arquivo">{arquivo.name} · {formatarTamanho(arquivo.size)}</span>
          : <span className="zona__dica">Arraste aqui ou clique para escolher</span>}
      </label>
      <input id={id} type="file" className="sr-only" accept={config.nome.endsWith('.json') ? '.json' : '.csv'}
        onChange={(e) => onEscolher(e.target.files[0])} />
      {erro && <p className="erro-campo" role="alert"><span aria-hidden="true">✕ </span>{erro}</p>}
    </div>
  )
}

export default function Importacao({ nome, onCriado }) {
  const [arquivos, setArquivos] = useState({})
  const [erros, setErros] = useState({})
  const [erroGeral, setErroGeral] = useState('')
  const [enviando, setEnviando] = useState(false)
  const faltando = ARQUIVOS.filter((a) => a.obrigatorio && !arquivos[a.campo])

  async function validar() {
    const formData = new FormData()
    Object.entries(arquivos).forEach(([campo, arquivo]) => formData.append(campo, arquivo))
    setEnviando(true)
    setErros({})
    setErroGeral('')
    try {
      const { lote_id: loteId } = await api.enviarLote(formData)
      onCriado(loteId)
    } catch (e) {
      setErros(e.dados?.arquivos ?? {})
      setErroGeral(e.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section>
      <h1 className="titulo-pagina">Olá, {nome}. Quais arquivos chegaram?</h1>
      <p className="texto-suave largura-leitura">Envie os arquivos exatamente como vieram do tribunal. Eles não são
        alterados: tudo o que for corrigido, descartado ou ficar em dúvida aparece com o motivo.</p>
      <div className="grade-zonas">
        {ARQUIVOS.map((config) => (
          <ZonaArquivo key={config.campo} config={config} arquivo={arquivos[config.campo]} erro={erros[config.campo]}
            onEscolher={(arquivo) => arquivo && setArquivos({ ...arquivos, [config.campo]: arquivo })} />
        ))}
      </div>
      {erroGeral && <p className="erro-campo" role="alert">{erroGeral}</p>}
      <div className="acoes">
        <button type="button" className="botao botao--primario" disabled={faltando.length > 0 || enviando} onClick={validar}>
          Validar
        </button>
        {faltando.length > 0 && <span className="texto-suave">Falta: {faltando.map((a) => a.nome).join(', ')}</span>}
      </div>
      {enviando && <Carregando texto="Enviando e validando os arquivos…" />}
    </section>
  )
}
