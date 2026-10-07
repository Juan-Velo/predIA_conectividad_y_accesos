import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import L from 'leaflet'
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  Marker,
  Pane,
  Polygon,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import {
  Check,
  LoaderCircle,
  LocateFixed,
  Maximize2,
  Minimize2,
  Minus,
  Pencil,
  Plus,
  Undo2,
  X,
} from 'lucide-react'
import { COLORES_VIA, area } from '../format'
import type { Analisis, Candidato, Capas, ClaseVia, LatLon, PuntoTransporte, ViaCercana } from '../types'

export type Base = 'mapa' | 'satelite'

export interface Enfoque {
  lat: number
  lon: number
  zoom?: number
  bounds?: LatLon[]
  token: number
}

const GROSOR: Record<ClaseVia, number> = { expresa: 6, arterial: 5, colectora: 4, local: 2.5 }
const CENTRO_INICIAL: LatLon = [-12.179517, -76.999133]

// ---------- Íconos (divIcon con SVG, sin imágenes externas) ----------

const SVG_BUS =
  '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6v6M15 6v6M2 12h19.6M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/><circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="16" cy="18" r="2"/></svg>'
const SVG_TREN =
  '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3.1V7a4 4 0 0 0 8 0V3.1"/><path d="m9 15-1-1"/><path d="m15 15 1-1"/><path d="M9 19c-2.8 0-5-2.2-5-5v-4a8 8 0 0 1 16 0v4c0 2.8-2.2 5-5 5Z"/><path d="m8 19-2 3"/><path d="m16 19 2 3"/></svg>'

const iconoParadero = L.divIcon({
  className: '',
  html: `<div class="mk-transporte" role="img" aria-label="Paradero">${SVG_BUS}</div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})
const iconoEstacion = (tipo: PuntoTransporte['tipo']) =>
  L.divIcon({
    className: '',
    html: `<div class="mk-transporte mk-estacion ${tipo}" role="img" aria-label="Estación">${
      tipo === 'metro' ? SVG_TREN : SVG_BUS
    }</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  })
const iconoTerreno = L.divIcon({
  className: '',
  html: `<div class="mk-terreno"><svg viewBox="0 0 24 32" width="30" height="40"><path d="M12 0C5.4 0 0 5.3 0 11.9 0 20.8 12 32 12 32s12-11.2 12-20.1C24 5.3 18.6 0 12 0Z" fill="#0d3b4f" stroke="#fff" stroke-width="1.5"/><circle cx="12" cy="12" r="4.5" fill="#fff"/></svg><span>Terreno</span></div>`,
  iconSize: [30, 40],
  iconAnchor: [15, 40],
})

function etiquetaVia(nombre: string, angulo: number, clase: ClaseVia) {
  return L.divIcon({
    className: '',
    html: `<div class="etiqueta-via ${clase}" style="transform: translate(-50%,-50%) rotate(${angulo}deg)">${nombre}</div>`,
    iconSize: [0, 0],
  })
}

// ---------- Utilidades geométricas para las etiquetas de calles ----------

function largo(coords: number[][]): number {
  let s = 0
  for (let i = 1; i < coords.length; i++) {
    const [x1, y1] = coords[i - 1]
    const [x2, y2] = coords[i]
    s += Math.hypot((x2 - x1) * Math.cos((y1 * Math.PI) / 180), y2 - y1)
  }
  return s * 111_000
}

function etiquetasDeCalles(data: Analisis['conectividad']['vias_geojson'], capas: Capas) {
  const mejores = new Map<string, { coords: number[][]; clase: ClaseVia; largo: number; total: number }>()
  for (const f of data.features) {
    const { nombre, clase } = f.properties
    if (!nombre || clase === 'local' || !capas[clase]) continue
    const l = largo(f.geometry.coordinates)
    const actual = mejores.get(nombre)
    if (!actual) mejores.set(nombre, { coords: f.geometry.coordinates, clase, largo: l, total: l })
    else {
      actual.total += l
      if (l > actual.largo) Object.assign(actual, { coords: f.geometry.coordinates, largo: l })
    }
  }
  const res: { nombre: string; pos: LatLon; angulo: number; clase: ClaseVia }[] = []
  for (const [nombre, m] of mejores) {
    if (m.total < 250 || m.coords.length < 2) continue
    const i = Math.max(1, Math.floor(m.coords.length / 2))
    const [x1, y1] = m.coords[i - 1]
    const [x2, y2] = m.coords[i]
    let ang = (-Math.atan2(y2 - y1, (x2 - x1) * Math.cos((y1 * Math.PI) / 180)) * 180) / Math.PI
    if (ang > 90) ang -= 180
    if (ang < -90) ang += 180
    res.push({ nombre, pos: [(y1 + y2) / 2, (x1 + x2) / 2], angulo: ang, clase: m.clase })
  }
  return res
}

// ---------- Componentes internos ----------

function Eventos({ onClick, onZoom }: { onClick: (ll: LatLon) => void; onZoom: (z: number) => void }) {
  useMapEvents({
    click: (e) => onClick([e.latlng.lat, e.latlng.lng]),
    zoomend: (e) => onZoom(e.target.getZoom()),
  })
  return null
}

function Controlador({ enfoque, pantallaCompleta, onMapa }: {
  enfoque: Enfoque | null
  pantallaCompleta: boolean
  onMapa: (m: L.Map) => void
}) {
  const map = useMap()
  useEffect(() => onMapa(map), [map, onMapa])
  useEffect(() => {
    const escala = L.control.scale({ metric: true, imperial: false, position: 'bottomleft', maxWidth: 140 })
    escala.addTo(map)
    return () => {
      escala.remove()
    }
  }, [map])
  useEffect(() => {
    if (!enfoque) return
    if (enfoque.bounds && enfoque.bounds.length > 2) {
      map.flyToBounds(L.latLngBounds(enfoque.bounds), { maxZoom: 17, padding: [80, 80], duration: 0.8 })
    } else {
      map.flyTo([enfoque.lat, enfoque.lon], enfoque.zoom ?? Math.max(map.getZoom(), 16), { duration: 0.8 })
    }
  }, [enfoque, map])
  useEffect(() => {
    const t = setTimeout(() => map.invalidateSize(), 250)
    return () => clearTimeout(t)
  }, [pantallaCompleta, map])
  return null
}

interface Props {
  analisis: Analisis | null
  cargando: boolean
  error: string | null
  capas: Capas
  base: Base
  onBase: (b: Base) => void
  enfoque: Enfoque | null
  viaSeleccionada: ViaCercana | null
  onClickMapa: (ll: LatLon) => void
  onCandidato: (c: Candidato) => void
  onCentrar: () => void
  dibujo: LatLon[] | null
  onDibujo: (accion: 'iniciar' | 'deshacer' | 'terminar' | 'cancelar') => void
  pantallaCompleta: boolean
  onPantallaCompleta: () => void
  onReintentar: () => void
  children?: ReactNode
}

export default function MapaConectividad(props: Props) {
  const { analisis, cargando, error, capas, base, onBase, enfoque, viaSeleccionada, dibujo } = props
  const [mapa, setMapa] = useState<L.Map | null>(null)
  const [zoom, setZoom] = useState(16)

  const conect = analisis?.conectividad
  const terreno = analisis?.terreno
  const idVersion = conect?.meta.generado ?? 'vacio'

  const porClase = useMemo(() => {
    const res = {} as Record<ClaseVia, GeoJSON.FeatureCollection>
    for (const c of ['local', 'colectora', 'arterial', 'expresa'] as ClaseVia[]) {
      res[c] = {
        type: 'FeatureCollection',
        features: conect?.vias_geojson.features.filter((f) => f.properties.clase === c) ?? [],
      }
    }
    return res
  }, [conect])

  const etiquetas = useMemo(
    () => (conect ? etiquetasDeCalles(conect.vias_geojson, capas) : []),
    [conect, capas],
  )

  const resaltado = useMemo<GeoJSON.FeatureCollection | null>(() => {
    if (!conect || !viaSeleccionada) return null
    return {
      type: 'FeatureCollection',
      features: conect.vias_geojson.features.filter(
        (f) => f.properties.id === viaSeleccionada.osm_id || (f.properties.nombre === viaSeleccionada.nombre && f.properties.clase === viaSeleccionada.clase),
      ),
    }
  }, [conect, viaSeleccionada])

  const candidatos = (terreno?.candidatos ?? []).filter(
    (c) => !terreno?.poligono || Math.abs(c.centro[0] - terreno.lat) + Math.abs(c.centro[1] - terreno.lon) > 1e-6,
  )
  const dibujando = dibujo !== null
  const sinPoligono = terreno && !terreno.poligono

  return (
    <div className={`mapa-wrap${props.pantallaCompleta ? ' pantalla-completa' : ''}${dibujando ? ' dibujando' : ''}`}>
      <MapContainer
        center={CENTRO_INICIAL}
        zoom={16}
        zoomControl={false}
        className="mapa"
        attributionControl
      >
        {base === 'satelite' ? (
          <>
            <TileLayer
              key="sat"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution="Imágenes &copy; Esri, Maxar, Earthstar Geographics"
              maxNativeZoom={19}
              maxZoom={20}
            />
            <TileLayer
              key="sat-ref"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
              maxNativeZoom={19}
              maxZoom={20}
            />
          </>
        ) : (
          <TileLayer
            key="mapa"
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
            subdomains="abcd"
            maxZoom={20}
          />
        )}

        <Controlador enfoque={enfoque} pantallaCompleta={props.pantallaCompleta} onMapa={setMapa} />
        <Eventos onClick={props.onClickMapa} onZoom={setZoom} />

        <Pane name="candidatos" style={{ zIndex: 405 }}>
          {!dibujando &&
            candidatos.map((c) => (
              <Polygon
                key={c.osm_id}
                positions={c.poligono}
                pathOptions={{
                  color: '#ffffff',
                  weight: 2,
                  dashArray: '5 5',
                  fillColor: '#ffffff',
                  fillOpacity: 0.12,
                }}
                bubblingMouseEvents={false}
                eventHandlers={{ click: () => props.onCandidato(c) }}
              >
                <Tooltip sticky>
                  <strong>{c.nombre ?? c.uso}</strong> · {area(c.area_m2)}
                  <br />
                  Clic para analizar este terreno
                </Tooltip>
              </Polygon>
            ))}
        </Pane>

        <Pane name="vias" style={{ zIndex: 410 }}>
          {(['local', 'colectora', 'arterial', 'expresa'] as ClaseVia[]).map(
            (c) =>
              capas[c] && (
                <GeoJSON
                  key={`${c}-${idVersion}`}
                  data={porClase[c]}
                  style={{
                    color: COLORES_VIA[c],
                    weight: GROSOR[c],
                    opacity: c === 'local' ? 0.75 : 0.92,
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                  onEachFeature={(f, layer) => {
                    if (f.properties?.nombre) layer.bindTooltip(f.properties.nombre, { sticky: true })
                  }}
                />
              ),
          )}
        </Pane>

        <Pane name="resaltado" style={{ zIndex: 415 }}>
          {resaltado && viaSeleccionada && (
            <>
              <GeoJSON
                key={`cas-${viaSeleccionada.osm_id}-${idVersion}`}
                data={resaltado}
                style={{ color: '#ffffff', weight: GROSOR[viaSeleccionada.clase] + 7, opacity: 0.95 }}
                interactive={false}
              />
              <GeoJSON
                key={`res-${viaSeleccionada.osm_id}-${idVersion}`}
                data={resaltado}
                style={{ color: COLORES_VIA[viaSeleccionada.clase], weight: GROSOR[viaSeleccionada.clase] + 1, opacity: 1 }}
                interactive={false}
              />
            </>
          )}
          {viaSeleccionada && terreno && !viaSeleccionada.frente_al_terreno && (
            <>
              <Polyline
                positions={[[terreno.lat, terreno.lon], viaSeleccionada.punto_acceso]}
                pathOptions={{ color: '#ffffff', weight: 3, dashArray: '2 8', lineCap: 'round' }}
                interactive={false}
              />
              <CircleMarker
                center={viaSeleccionada.punto_acceso}
                radius={6}
                pathOptions={{ color: '#fff', weight: 2, fillColor: COLORES_VIA[viaSeleccionada.clase], fillOpacity: 1 }}
              >
                <Tooltip permanent direction="bottom" offset={[0, 8]} className="tt-acceso">
                  {viaSeleccionada.nombre} ·{' '}
                  {viaSeleccionada.duracion_min} min {viaSeleccionada.modo === 'caminando' ? 'a pie' : 'en auto'}
                </Tooltip>
              </CircleMarker>
            </>
          )}
        </Pane>

        <Pane name="terreno" style={{ zIndex: 420 }}>
          {terreno?.poligono && (
            <Polygon
              positions={terreno.poligono}
              pathOptions={{ color: '#5eead4', weight: 3, fillColor: '#2dd4bf', fillOpacity: 0.35 }}
              interactive={false}
            />
          )}
          {dibujo && dibujo.length > 0 && (
            <>
              {dibujo.length >= 3 ? (
                <Polygon positions={dibujo} pathOptions={{ color: '#fde047', weight: 3, fillOpacity: 0.2 }} interactive={false} />
              ) : (
                <Polyline positions={dibujo} pathOptions={{ color: '#fde047', weight: 3 }} interactive={false} />
              )}
              {dibujo.map((p, i) => (
                <CircleMarker key={i} center={p} radius={5} pathOptions={{ color: '#fff', weight: 2, fillColor: '#eab308', fillOpacity: 1 }} interactive={false} />
              ))}
            </>
          )}
        </Pane>

        {zoom >= 15 &&
          etiquetas.map((e) => (
            <Marker
              key={`${e.nombre}-${idVersion}`}
              position={e.pos}
              icon={etiquetaVia(e.nombre, e.angulo, e.clase)}
              interactive={false}
              keyboard={false}
            />
          ))}

        {capas.paraderos &&
          zoom >= 14 &&
          conect?.transporte.paraderos.map((p) => (
            <Marker key={`p-${p.lat},${p.lon}`} position={[p.lat, p.lon]} icon={iconoParadero}>
              <Tooltip direction="top" offset={[0, -10]}>
                Paradero{p.nombre ? `: ${p.nombre}` : ''}
              </Tooltip>
            </Marker>
          ))}
        {capas.estaciones &&
          conect?.transporte.estaciones.map((e) => (
            <Marker key={`e-${e.lat},${e.lon}`} position={[e.lat, e.lon]} icon={iconoEstacion(e.tipo)} zIndexOffset={500}>
              <Tooltip direction="top" offset={[0, -14]}>
                <strong>{e.nombre}</strong>
                <br />
                {e.red}
              </Tooltip>
            </Marker>
          ))}

        {terreno && <Marker position={[terreno.lat, terreno.lon]} icon={iconoTerreno} zIndexOffset={1000} interactive={false} />}
      </MapContainer>

      {/* ---------- Controles superpuestos ---------- */}
      <div className="ctrl-base" role="group" aria-label="Tipo de mapa">
        <button className={base === 'mapa' ? 'activo' : ''} onClick={() => onBase('mapa')}>
          Mapa
        </button>
        <button className={base === 'satelite' ? 'activo' : ''} onClick={() => onBase('satelite')}>
          Satélite
        </button>
      </div>
      <div className="ctrl-norte" aria-label="Norte" title="Norte">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path d="M12 2 18 20 12 16 6 20Z" fill="#0d3b4f" />
        </svg>
        <span>N</span>
      </div>

      <div className="ctrl-arriba-der">
        {!dibujando ? (
          <button className="ctrl-btn texto" onClick={() => props.onDibujo('iniciar')} title="Dibujar el contorno del terreno">
            <Pencil size={15} /> <span className="txt">Dibujar terreno</span>
          </button>
        ) : (
          <div className="barra-dibujo">
            <span>{dibujo.length < 3 ? `Marca los vértices (${dibujo.length}/3+)` : `${dibujo.length} vértices`}</span>
            <button className="ctrl-btn" onClick={() => props.onDibujo('deshacer')} disabled={!dibujo.length} title="Deshacer">
              <Undo2 size={16} />
            </button>
            <button className="ctrl-btn ok" onClick={() => props.onDibujo('terminar')} disabled={dibujo.length < 3} title="Analizar">
              <Check size={16} />
            </button>
            <button className="ctrl-btn" onClick={() => props.onDibujo('cancelar')} title="Cancelar">
              <X size={16} />
            </button>
          </div>
        )}
        <button
          className="ctrl-btn"
          onClick={props.onPantallaCompleta}
          title={props.pantallaCompleta ? 'Salir de pantalla completa (Esc)' : 'Ver mapa completo'}
        >
          {props.pantallaCompleta ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
        </button>
      </div>

      <div className="ctrl-zoom">
        <div className="ctrl-grupo">
          <button onClick={() => mapa?.zoomIn()} aria-label="Acercar">
            <Plus size={20} />
          </button>
          <button onClick={() => mapa?.zoomOut()} aria-label="Alejar">
            <Minus size={20} />
          </button>
        </div>
        <button className="ctrl-btn redondo" onClick={props.onCentrar} aria-label="Centrar en el terreno" title="Centrar en el terreno">
          <LocateFixed size={19} />
        </button>
      </div>

      {cargando && (
        <div className="mapa-aviso">
          <LoaderCircle size={16} className="girar" /> Analizando red vial y transporte…
        </div>
      )}
      {!cargando && error && (
        <div className="mapa-aviso error">
          {error}
          <button onClick={props.onReintentar}>Reintentar</button>
        </div>
      )}
      {!cargando && !error && !dibujando && sinPoligono && (
        <div className="mapa-aviso info">
          Haz clic en una cancha o área verde (contorno punteado) o dibuja el terreno
        </div>
      )}
      {!cargando && !error && !dibujando && terreno?.poligono && (
        <div className="mapa-aviso sutil">Clic en el mapa para analizar otro punto</div>
      )}
      {props.children}
    </div>
  )
}
