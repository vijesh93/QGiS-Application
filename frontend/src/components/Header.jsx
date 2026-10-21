import { Link } from 'react-router-dom';
import { APP_TITLE } from '../constants/brand';

// Branded top bar, used on the legal pages only (the map route uses the
// Sidebar's own header instead — see App.jsx for why).
export default function Header() {
  return (
    <header className="h-12 flex-shrink-0 flex items-center gap-3 px-4 bg-bawu-schwarz border-b-4 border-bawu-gelb">
      <Link
        to="/"
        className="flex items-center gap-2.5 hover:opacity-80 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-bawu-gelb rounded"
      >
        <img
          src="/BaWue_Logo_Flag_rgb.svg"
          alt="Land Baden-Württemberg"
          className="h-8 w-auto flex-shrink-0"
          onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = '/logo-placeholder.svg'; }}
        />
        <span className="font-bawu-sans text-white font-semibold text-sm sm:text-base tracking-tight">
          {APP_TITLE}
        </span>
      </Link>
    </header>
  );
}
