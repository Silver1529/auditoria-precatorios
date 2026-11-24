// Só formatação de exibição. Nenhuma regra de negócio aqui.
// Dinheiro chega da API como texto ("30500.00"); Intl formata o texto sem convertê-lo em float.
const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function formatarMoeda(valor) {
  if (valor === null || valor === undefined || valor === '') return '—'
  return moeda.format(valor)
}

export function formatarData(iso) {
  if (!iso) return '—'
  const [ano, mes, dia] = String(iso).slice(0, 10).split('-')
  return dia && mes && ano ? `${dia}/${mes}/${ano}` : String(iso)
}

export function formatarTamanho(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace('.', ',')} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`
}
