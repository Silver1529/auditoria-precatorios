import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client'
import BannerEnvio from './components/BannerEnvio'
import Carregando from './components/Carregando'
import Marca from './components/Marca'
import MensagemErro from './components/MensagemErro'
import Conferencia from './pages/Conferencia'
import DemoIdempotencia from './pages/DemoIdempotencia'
import Importacao from './pages/Importacao'
import Login from './pages/Login'
import Pendencias from './pages/Pendencias'
import Prazos from './pages/Prazos'
import Registros from './pages/Registros'
import Resultado from './pages/Resultado'

const ABAS = [
  ['resultado', 'Resultado', Resultado],
  ['registros', 'Registros', Registros],
  ['pendencias', 'Pendências', Pendencias],
  ['conferencia', 'Conferência', Conferencia],
  ['prazos', 'Prazos', Prazos],
  ['demo', 'Demonstração', DemoIdempotencia],
]

// Rotas simples por hash: #/ (importação) e #/lotes/<id>/<aba>. Sem biblioteca de rotas.
function lerRota() {
  const partes = window.location.hash.replace(/^#\/?/, '').split('/')
  if (partes[0] === 'lotes' && partes[1]) return { loteId: Number(partes[1]), aba: partes[2] || 'resultado' }
  return { loteId: null, aba: null }
}

function useRota() {
  const [rota, setRota] = useState(lerRota)
  useEffect(() => {
    const aoMudar = () => setRota(lerRota())
    window.addEventListener('hashchange', aoMudar)
    return () => window.removeEventListener('hashchange', aoMudar)
  }, [])
  return rota
}

function Lote({ loteId, aba }) {
  const [resumo, setResumo] = useState(null)
  const [erro, setErro] = useState(null)
  const atualizar = useCallback(async () => {
    try {
      setResumo(await api.lote(loteId))
      setErro(null)
    } catch (e) {
      setErro(e)
    }
  }, [loteId])
  useEffect(() => { atualizar() }, [atualizar])

  if (erro) return <MensagemErro erro={erro} onTentarDeNovo={atualizar} />
  if (!resumo) return <Carregando texto="Carregando o lote…" />
  const [, , Pagina] = ABAS.find(([chave]) => chave === aba) ?? ABAS[0]
  return (
    <>
      <div className="lote-topo">
        <div>
          <h1 className="lote-topo__titulo">Lote {loteId}</h1>
          {resumo.criado_em && <p className="texto-suave">Analisado em {new Date(resumo.criado_em).toLocaleString('pt-BR',
            { dateStyle: 'short', timeStyle: 'short' })}</p>}
        </div>
        <BannerEnvio liberado={resumo.envio_liberado} motivo={resumo.motivo_bloqueio} />
      </div>
      <nav className="abas" aria-label="Seções do lote">
        {ABAS.map(([chave, rotulo]) => (
          <a key={chave} href={`#/lotes/${loteId}/${chave}`} aria-current={chave === aba ? 'page' : undefined}>
            {rotulo}{chave === 'pendencias' && resumo.bloqueios.length > 0 &&
              <span className="contador">{resumo.bloqueios.length}</span>}
          </a>
        ))}
      </nav>
      <Pagina loteId={loteId} resumo={resumo} onAtualizar={atualizar}
        onResumo={(novo) => setResumo((atual) => ({ ...atual, ...novo }))} />
    </>
  )
}

export default function App() {
  const [usuario, setUsuario] = useState(undefined)
  const [loginLivre, setLoginLivre] = useState(false)
  const rota = useRota()

  useEffect(() => {
    api.me().then(setUsuario).catch((e) => {
      setLoginLivre(Boolean(e.dados?.login_livre))
      setUsuario(null)
    })
  }, [])

  if (usuario === undefined) return <Carregando />
  if (usuario === null) return <Login onEntrar={setUsuario} loginLivre={loginLivre} />

  async function sair() {
    await api.sair().catch(() => {})
    setUsuario(null)
  }

  return (
    <>
      <header className="topo">
        <a href="#/" className="topo__marca" aria-label="Validador de precatórios: início"><Marca /></a>
        <span className="topo__ola">Olá, <strong>{usuario.nome}</strong></span>
        <nav className="topo__acoes" aria-label="Conta">
          {rota.loteId && <a href="#/" className="botao botao--secundario">Nova importação</a>}
          <button type="button" className="botao botao--texto" onClick={sair}>Sair</button>
        </nav>
      </header>
      <main className="conteudo">
        {rota.loteId
          ? <Lote key={rota.loteId} loteId={rota.loteId} aba={rota.aba} />
          : <Importacao nome={usuario.nome} onCriado={(id) => { window.location.hash = `#/lotes/${id}/resultado` }} />}
      </main>
    </>
  )
}
