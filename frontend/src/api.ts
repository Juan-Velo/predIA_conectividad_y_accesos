import type { Analisis, LatLon, ResultadoBusqueda } from './types'

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init)
  if (!resp.ok) {
    let detalle = `Error ${resp.status}`
    try {
      const body = await resp.json()
      if (typeof body.detail === 'string') detalle = body.detail
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(detalle)
  }
  return resp.json() as Promise<T>
}

export function analizarPunto(lat: number, lon: number, signal?: AbortSignal) {
  const q = new URLSearchParams({ lat: String(lat), lon: String(lon) })
  return pedir<Analisis>(`/api/analisis?${q}`, { signal })
}

export function analizarPoligono(poligono: LatLon[], signal?: AbortSignal) {
  const lat = poligono.reduce((s, p) => s + p[0], 0) / poligono.length
  const lon = poligono.reduce((s, p) => s + p[1], 0) / poligono.length
  return pedir<Analisis>('/api/analisis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lat, lon, poligono }),
    signal,
  })
}

export function buscarDireccion(q: string) {
  return pedir<ResultadoBusqueda[]>(`/api/geocode/search?q=${encodeURIComponent(q)}`)
}
