import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client'
import BannerEnvio from './components/BannerEnvio'
import Carregando from './components/Carregando'
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
      <BannerEnvio liberado={resumo.envio_liberado} motivo={resumo.motivo_bloqueio} />
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
  const rota = useRota()

  useEffect(() => {
    api.me().then((d) => setUsuario(d.usuario)).catch(() => setUsuario(null))
  }, [])

  if (usuario === undefined) return <Carregando />
  if (usuario === null) return <Login onEntrar={setUsuario} />

  async function sair() {
    await api.sair().catch(() => {})
    setUsuario(null)
  }

  return (
    <>
      <header className="topo">
        <a href="#/" className="topo__marca">Validador de precatórios</a>
        {rota.loteId && <span className="texto-suave">Lote #{rota.loteId}</span>}
        <a href="#/" className="botao botao--secundario">Nova importação</a>
        <span className="topo__usuario">{usuario}</span>
        <button type="button" className="botao botao--secundario" onClick={sair}>Sair</button>
      </header>
      <main className="conteudo">
        {rota.loteId
          ? <Lote key={rota.loteId} loteId={rota.loteId} aba={rota.aba} />
          : <Importacao onCriado={(id) => { window.location.hash = `#/lotes/${id}/resultado` }} />}
      </main>
    </>
  )
}
