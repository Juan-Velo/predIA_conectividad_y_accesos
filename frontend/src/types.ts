export type ClaseVia = 'expresa' | 'arterial' | 'colectora' | 'local'
export type LatLon = [number, number]

export interface Candidato {
  osm_id: number
  uso: string
  nombre: string | null
  area_m2: number
  centro: LatLon
  poligono: LatLon[]
}

export interface Terreno {
  lat: number
  lon: number
  direccion: string
  direccion_completa: string
  distrito: string | null
  nombre: string | null
  poligono: LatLon[] | null
  fuente_poligono: 'osm' | 'usuario' | null
  area_m2: number | null
  perimetro_m: number | null
  uso_actual: string
  miniatura: {
    zoom: number
    teselas: { url: string; x: number; y: number }[]
    centro_px: [number, number]
    contorno_px: [number, number][]
  }
  candidatos: Candidato[]
}

export interface ViaCercana {
  clase: ClaseVia
  etiqueta: string
  nombre: string
  nombre_completo: string
  osm_id: number
  recta_m: number
  distancia_m: number
  duracion_min: number
  modo: 'caminando' | 'vehiculo'
  frente_al_terreno: boolean
  estimado: boolean
  punto_acceso: LatLon
}

export interface Observacion {
  tipo: 'positivo' | 'neutral' | 'alerta'
  texto: string
  detalle: string | null
}

export interface Acceso {
  tipo_via_frontal: string
  clase_via_frontal: string
  via_frontal: string
  distancia_via_m: number
  ancho_aprox_m: number
  ancho_fuente: 'osm' | 'carriles' | 'tipico'
  carriles: string | null
  superficie: string | null
  acceso_vehicular: string
  transporte_publico: string
}

export interface PuntoTransporte {
  nombre: string | null
  lat: number
  lon: number
  tipo: 'paradero' | 'metro' | 'metropolitano' | 'corredor'
  recta_m: number
  red?: string | null
}

export interface Conectividad {
  punto: { lat: number; lon: number }
  red_vial_cercana: ViaCercana[]
  observaciones: Observacion[]
  acceso: Acceso | null
  transporte: {
    paraderos: PuntoTransporte[]
    estaciones: PuntoTransporte[]
    paradero_cercano: (PuntoTransporte & { distancia_m: number; duracion_min: number }) | null
    estacion_cercana:
      | (PuntoTransporte & { distancia_m: number; duracion_min: number; modo: string })
      | null
  }
  vias_geojson: GeoJSON.FeatureCollection<
    GeoJSON.LineString,
    { id: number; clase: ClaseVia; highway: string; nombre: string | null }
  >
  resumen: Record<ClaseVia, number>
  meta: { generado: string; fuentes: string[]; nota_tiempos: string }
}

export interface Analisis {
  terreno: Terreno
  conectividad: Conectividad
}

export interface ResultadoBusqueda {
  lat: number
  lon: number
  titulo: string
  detalle: string
  tipo: string
}

export interface Capas {
  expresa: boolean
  arterial: boolean
  colectora: boolean
  local: boolean
  paraderos: boolean
  estaciones: boolean
}
