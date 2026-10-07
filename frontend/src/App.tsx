import { useCallback, useEffect, useRef, useState } from 'react'
import { Bus } from 'lucide-react'
import { analizarPoligono, analizarPunto } from './api'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import TerrenoCard from './components/TerrenoCard'
import FiltrosVias from './components/FiltrosVias'
import MapaConectividad from './components/MapaConectividad'
import type { Base, Enfoque } from './components/MapaConectividad'
import { AccesoTerreno, Observaciones, RedVialCercana } from './components/Paneles'
import { COLORES_VIA, COLOR_TRANSPORTE, ETIQUETAS_VIA } from './format'
import type { Analisis, Candidato, Capas, ClaseVia, LatLon, ViaCercana } from './types'
import './App.css'

// Centro de la zona de estudio (Chorrillos): 12°10'46.26"S 76°59'56.88"W
const PUNTO_INICIAL = { lat: -12.179517, lon: -76.999133 }

type Objetivo =
  | { tipo: 'punto'; lat: number; lon: number }
  | { tipo: 'poligono'; poligono: LatLon[] }

let contadorEnfoque = 0
const nuevoEnfoque = (e: Omit<Enfoque, 'token'>): Enfoque => ({ ...e, token: ++contadorEnfoque })

export default function App() {
  const [objetivo, setObjetivo] = useState<Objetivo>({ tipo: 'punto', ...PUNTO_INICIAL })
  const [intento, setIntento] = useState(0)
  const [analisis, setAnalisis] = useState<Analisis | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [capas, setCapas] = useState<Capas>({
    expresa: true,
    arterial: true,
    colectora: true,
    local: true,
    paraderos: true,
    estaciones: true,
  })
  const [base, setBase] = useState<Base>('satelite')
  const [enfoque, setEnfoque] = useState<Enfoque | null>(null)
  const [viaSel, setViaSel] = useState<ViaCercana | null>(null)
  const [dibujo, setDibujo] = useState<LatLon[] | null>(null)
  const [pantallaCompleta, setPantallaCompleta] = useState(false)
  const enfocarAlCargar = useRef(true)

  // Cada cambio de objetivo dispara un análisis; el anterior se cancela
  useEffect(() => {
    const ctrl = new AbortController()
    setCargando(true)
    setError(null)
    setViaSel(null)
    const peticion =
      objetivo.tipo === 'punto'
        ? analizarPunto(objetivo.lat, objetivo.lon, ctrl.signal)
        : analizarPoligono(objetivo.poligono, ctrl.signal)
    peticion
      .then((a) => {
        setAnalisis(a)
        if (enfocarAlCargar.current) {
          const t = a.terreno
          setEnfoque(nuevoEnfoque({ lat: t.lat, lon: t.lon, zoom: 16, bounds: t.poligono ?? undefined }))
          enfocarAlCargar.current = false
        }
      })
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError(e.message || 'No se pudo completar el análisis')
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setCargando(false)
      })
    return () => ctrl.abort()
  }, [objetivo, intento])

  useEffect(() => {
    if (!pantallaCompleta) return
    const salir = (e: KeyboardEvent) => e.key === 'Escape' && setPantallaCompleta(false)
    window.addEventListener('keydown', salir)
    return () => window.removeEventListener('keydown', salir)
  }, [pantallaCompleta])

  const analizarEn = useCallback((lat: number, lon: number, enfocar: boolean) => {
    enfocarAlCargar.current = enfocar
    if (enfocar) setEnfoque(nuevoEnfoque({ lat, lon, zoom: 16 }))
    setObjetivo({ tipo: 'punto', lat, lon })
  }, [])

  const onClickMapa = useCallback(
    (ll: LatLon) => {
      if (dibujo) setDibujo([...dibujo, ll])
      else analizarEn(ll[0], ll[1], false)
    },
    [dibujo, analizarEn],
  )

  function onCandidato(c: Candidato) {
    setEnfoque(nuevoEnfoque({ lat: c.centro[0], lon: c.centro[1], bounds: c.poligono }))
    enfocarAlCargar.current = false
    setObjetivo({ tipo: 'punto', lat: c.centro[0], lon: c.centro[1] })
  }

  function onDibujo(accion: 'iniciar' | 'deshacer' | 'terminar' | 'cancelar') {
    if (accion === 'iniciar') setDibujo([])
    else if (accion === 'cancelar') setDibujo(null)
    else if (accion === 'deshacer') setDibujo((d) => (d ? d.slice(0, -1) : d))
    else if (dibujo && dibujo.length >= 3) {
      enfocarAlCargar.current = false
      setObjetivo({ tipo: 'poligono', poligono: dibujo })
      setDibujo(null)
    }
  }

  function centrar() {
    const t = analisis?.terreno
    if (t) setEnfoque(nuevoEnfoque({ lat: t.lat, lon: t.lon, zoom: 17, bounds: t.poligono ?? undefined }))
  }

  function onSeleccionarVia(v: ViaCercana) {
    const t = analisis?.terreno
    if (viaSel?.osm_id === v.osm_id) {
      setViaSel(null)
      return
    }
    setViaSel(v)
    if (!capas[v.clase]) setCapas({ ...capas, [v.clase]: true })
    if (t) {
      setEnfoque(
        nuevoEnfoque({
          lat: v.punto_acceso[0],
          lon: v.punto_acceso[1],
          bounds: [[t.lat, t.lon], v.punto_acceso, [t.lat, t.lon]],
        }),
      )
    }
  }

  const conect = analisis?.conectividad

  return (
    <div className="app">
      <Header onSeleccionar={(lat, lon) => analizarEn(lat, lon, true)} />
      <div className="cuerpo">
        <Sidebar />
        <main className="contenido">
          <div className="titulo-fila">
            <div>
              <h1>Conectividad y accesos</h1>
              <p className="subtitulo">Análisis de la red vial, transporte y tiempos de acceso.</p>
            </div>
            <TerrenoCard terreno={analisis?.terreno ?? null} cargando={cargando} onEnfocar={centrar} />
          </div>

          <div className="grid-principal">
            <section className="col-mapa">
              <FiltrosVias capas={capas} onCambiar={setCapas} />
              <MapaConectividad
                analisis={analisis}
                cargando={cargando}
                error={error}
                capas={capas}
                base={base}
                onBase={setBase}
                enfoque={enfoque}
                viaSeleccionada={viaSel}
                onClickMapa={onClickMapa}
                onCandidato={onCandidato}
                onCentrar={centrar}
                dibujo={dibujo}
                onDibujo={onDibujo}
                pantallaCompleta={pantallaCompleta}
                onPantallaCompleta={() => setPantallaCompleta(!pantallaCompleta)}
                onReintentar={() => setIntento((i) => i + 1)}
              />
              <div className="leyenda">
                {(Object.keys(ETIQUETAS_VIA) as ClaseVia[]).map((c) => (
                  <span key={c}>
                    <i className="leyenda-linea" style={{ background: COLORES_VIA[c] }} />
                    {ETIQUETAS_VIA[c]}
                    {conect && <small>({conect.resumen[c]})</small>}
                  </span>
                ))}
                <span>
                  <i className="leyenda-bus" style={{ background: COLOR_TRANSPORTE }}>
                    <Bus size={13} color="#fff" />
                  </i>
                  Transporte
                  {conect && <small>({conect.transporte.paraderos.length})</small>}
                </span>
              </div>
            </section>

            <aside className="col-paneles">
              <RedVialCercana
                vias={conect?.red_vial_cercana ?? null}
                seleccionada={viaSel?.osm_id ?? null}
                onSeleccionar={onSeleccionarVia}
                onVerMapa={() => setPantallaCompleta(true)}
              />
              <Observaciones items={conect?.observaciones ?? null} />
              <AccesoTerreno acceso={conect?.acceso ?? null} cargado={!!conect} />
              <p className="fuentes">
                Datos: © OpenStreetMap · Rutas: OSRM · Imágenes: Esri. {conect?.meta.nota_tiempos}
              </p>
            </aside>
          </div>
        </main>
      </div>
    </div>
  )
}
