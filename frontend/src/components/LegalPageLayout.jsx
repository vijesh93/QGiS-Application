import { Link } from 'react-router-dom';

// Shared chrome for the three legal pages (Impressum, Datenschutz,
// Barrierefreiheit) — full-page, light background, BW typography tokens,
// with a back-to-map link and cross-links to the other legal pages.
export default function LegalPageLayout({ title, children }) {
  return (
    <div
      id="main-content"
      className="h-full overflow-y-auto bg-white text-bawu-schwarz font-bawu-sans"
    >
      <div className="max-w-3xl mx-auto px-6 py-10">
        <Link
          to="/"
          className="inline-block mb-6 text-sm text-bawu-info-dunkel hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-bawu-info-dunkel rounded"
        >
          ← Zurück zur Karte
        </Link>

        <h1 className="font-bawu-serif text-3xl font-bold mb-6">{title}</h1>

        <div className="space-y-4 leading-relaxed text-bawu-grau-6 [&_h2]:font-bawu-serif [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-bawu-schwarz [&_h2]:mt-8 [&_h2]:mb-2">
          {children}
        </div>

        <nav
          aria-label="Rechtliche Seiten"
          className="mt-12 pt-6 border-t border-bawu-grau-2 flex flex-wrap gap-4 text-sm text-bawu-grau-5"
        >
          <Link to="/impressum" className="hover:text-bawu-schwarz hover:underline">
            Impressum
          </Link>
          <Link to="/datenschutz" className="hover:text-bawu-schwarz hover:underline">
            Datenschutz
          </Link>
          <Link to="/barrierefreiheit" className="hover:text-bawu-schwarz hover:underline">
            Erklärung zur Barrierefreiheit
          </Link>
        </nav>
      </div>
    </div>
  );
}
