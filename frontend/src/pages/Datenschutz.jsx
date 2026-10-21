import LegalPageLayout from '../components/LegalPageLayout';
import { ORG_NAME } from '../constants/brand';

// Datenschutzerklärung (DSGVO). The factual claims here (no accounts, no
// cookies/tracking) match what a codebase review found as of 2026-10 — if
// that ever changes (analytics added, forms added, etc.), this page must be
// updated accordingly. [PLATZHALTER] fields need LAZBW's exact DSB contact
// — see docs/bw-rebrand-plan.md, Open Items #3/#4.
export default function Datenschutz() {
  return (
    <LegalPageLayout title="Datenschutzerklärung">
      <p>
        Der Schutz Ihrer personenbezogenen Daten ist uns wichtig. Diese
        Datenschutzerklärung informiert Sie über Art, Umfang und Zweck der
        Verarbeitung personenbezogener Daten bei der Nutzung dieser Anwendung.
      </p>

      <h2>Verantwortlicher</h2>
      <p>
        {ORG_NAME}
        <br />
        [PLATZHALTER: Straße, PLZ, Ort]
        <br />
        E-Mail: [PLATZHALTER]
      </p>

      <h2>Datenschutzbeauftragte(r)</h2>
      <p>[PLATZHALTER: Name/Kontakt des bzw. der Datenschutzbeauftragten der {ORG_NAME}]</p>

      <h2>Server-Logfiles</h2>
      <p>
        Beim Aufruf dieser Anwendung erhebt der Webserver automatisch
        technische Zugriffsdaten (z. B. gekürzte IP-Adresse, Datum und
        Uhrzeit des Zugriffs, aufgerufene Seite, verwendeter Browser). Diese
        Daten dienen ausschließlich der technischen Bereitstellung und
        Absicherung des Dienstes und werden nicht mit anderen Datenquellen
        zusammengeführt. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO
        (berechtigtes Interesse am sicheren und stabilen Betrieb).
      </p>

      <h2>Cookies, Analyse- und Trackingdienste</h2>
      <p>
        Diese Anwendung setzt nach aktuellem Stand (Oktober 2026) keine
        Cookies und keine Analyse- oder Trackingdienste ein. Sollte sich dies
        ändern, wird diese Erklärung entsprechend aktualisiert und — soweit
        gesetzlich erforderlich — vorab eine Einwilligung eingeholt.
      </p>

      <h2>Keine Nutzerkonten, keine Eingabe personenbezogener Daten</h2>
      <p>
        Die Anwendung dient der reinen Anzeige von Klimaprojektionsdaten auf
        einer interaktiven Karte. Es werden keine Nutzerkonten angelegt und
        keine personenbezogenen Daten über Formulare erfasst.
      </p>

      <h2>Ihre Rechte</h2>
      <p>
        Sie haben nach der DSGVO das Recht auf Auskunft (Art. 15), Berichtigung
        (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung
        (Art. 18), Datenübertragbarkeit (Art. 20) sowie Widerspruch
        (Art. 21) hinsichtlich Ihrer personenbezogenen Daten. Zudem steht
        Ihnen ein Beschwerderecht bei einer Datenschutz-Aufsichtsbehörde zu.
      </p>

      <p className="mt-8 text-xs text-bawu-grau-4">
        Hinweis: Diese Erklärung enthält noch Platzhalter und ist vor der
        öffentlichen Freigabe durch die {ORG_NAME} zu vervollständigen und
        rechtlich zu prüfen.
      </p>
    </LegalPageLayout>
  );
}
