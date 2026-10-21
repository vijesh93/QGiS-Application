import { Routes, Route, Outlet } from 'react-router-dom';
import Header from './components/Header';
import MapPage from './pages/MapPage';
import Impressum from './pages/Impressum';
import Datenschutz from './pages/Datenschutz';
import Barrierefreiheit from './pages/Barrierefreiheit';
import 'maplibre-gl/dist/maplibre-gl.css';

// The map route doesn't get this — its Sidebar already carries the
// KlimaWandeln branding, so a page-level Header on top of it would just be
// a redundant duplicate bar eating map viewport height. Legal pages have no
// sidebar, so they go through this layout to still get branding + the logo.
function LegalLayout() {
  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <Header />
      <div className="flex-1 min-h-0">
        <Outlet />
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="w-screen h-screen flex flex-col bg-slate-900">
      {/* Visually hidden until focused — first tab stop, jumps past any
          chrome straight to the page's main content. Required for
          keyboard/screen-reader users under BITV 2.0 / WCAG 2.1. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-bawu-gelb focus:text-bawu-schwarz focus:px-3 focus:py-2 focus:rounded focus:font-bawu-sans focus:font-semibold"
      >
        Zum Inhalt springen
      </a>

      <Routes>
        <Route path="/" element={<MapPage />} />
        <Route element={<LegalLayout />}>
          <Route path="/impressum" element={<Impressum />} />
          <Route path="/datenschutz" element={<Datenschutz />} />
          <Route path="/barrierefreiheit" element={<Barrierefreiheit />} />
        </Route>
      </Routes>
    </div>
  );
}

export default App;
