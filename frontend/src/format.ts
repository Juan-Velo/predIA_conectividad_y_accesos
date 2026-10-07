import type { ClaseVia } from './types'

export const COLORES_VIA: Record<ClaseVia, string> = {
  expresa: '#e5484d',
  arterial: '#f2811d',
  colectora: '#f5c518',
  local: '#5aa9f0',
}

export const COLOR_TRANSPORTE = '#7c3aed'

export const ETIQUETAS_VIA: Record<ClaseVia, string> = {
  expresa: 'Vías expresas',
  arterial: 'Vías arteriales',
  colectora: 'Vías colectoras',
  local: 'Vías locales',
}

export function distancia(m: number): string {
  if (m >= 1000) return `${(m / 1000).toFixed(1)} km`
  return `${Math.max(10, Math.round(m / 10) * 10)} m`
}

export function area(m2: number): string {
  return `${m2.toLocaleString('en-US')} m²`
}
