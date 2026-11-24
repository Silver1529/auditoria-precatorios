// Cliente da API: sessão por cookie, CSRF no cabeçalho e erros sempre como ErroApi com mensagem em português.

export class ErroApi extends Error {
  constructor(mensagem, status, dados = {}) {
    super(mensagem)
    this.status = status
    this.dados = dados
  }
}

function lerCookie(nome) {
  const par = document.cookie.split('; ').find((c) => c.startsWith(`${nome}=`))
  return par ? decodeURIComponent(par.split('=')[1]) : ''
}

async function requisitar(metodo, url, corpo) {
  const opcoes = { method: metodo, credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (metodo !== 'GET') opcoes.headers['X-CSRFToken'] = lerCookie('csrftoken')
  if (corpo instanceof FormData) {
    opcoes.body = corpo
  } else if (corpo !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json'
    opcoes.body = JSON.stringify(corpo)
  }
  let resposta
  try {
    resposta = await fetch(url, opcoes)
  } catch {
    throw new ErroApi('Sem conexão com o servidor. Verifique a internet e tente de novo.', 0)
  }
  const dados = await resposta.json().catch(() => ({}))
  if (!resposta.ok) {
    throw new ErroApi(dados.erro || `Erro inesperado (código ${resposta.status}).`, resposta.status, dados)
  }
  return dados
}

const consulta = (params) => {
  const limpos = Object.entries(params).filter(([, v]) => v)
  return limpos.length ? `?${new URLSearchParams(limpos)}` : ''
}

export const api = {
  me: () => requisitar('GET', '/api/me'),
  entrar: (usuario, senha) => requisitar('POST', '/api/login', { usuario, senha }),
  sair: () => requisitar('POST', '/api/logout'),
  enviarLote: (formData) => requisitar('POST', '/api/lotes', formData),
  lote: (id) => requisitar('GET', `/api/lotes/${id}`),
  registros: (id, filtros = {}) => requisitar('GET', `/api/lotes/${id}/registros${consulta(filtros)}`),
  conferencia: (id) => requisitar('GET', `/api/lotes/${id}/conferencia`),
  prazos: (id) => requisitar('GET', `/api/lotes/${id}/prazos`),
  decidir: (loteId, registroId, decisao, justificativa) =>
    requisitar('POST', `/api/pendencias/${encodeURIComponent(registroId)}/decisao`,
      { lote_id: loteId, decisao, justificativa }),
  gerar: (id) => requisitar('POST', `/api/lotes/${id}/gerar`),
  demo: (id) => requisitar('GET', `/api/demo/idempotencia${consulta({ lote_id: id })}`),
}
