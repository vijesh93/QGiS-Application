import LegalPageLayout from '../components/LegalPageLayout';
import { ORG_NAME } from '../constants/brand';

// Required under § 10 Abs. 1 L-BGG (which points to BITV 2.0 / EN 301 549 /
// WCAG 2.1). Deliberately does NOT claim full compliance — no formal audit
// has been run yet, only an initial implementation pass (lang attribute,
// skip link, aria-labels, focus-visible styles). Update the compliance
// status + known-barriers list once a real BITV self-test (bitvtest.de) or
// third-party audit has been done. [PLATZHALTER] fields need LAZBW's exact
// feedback contact — see docs/bw-rebrand-plan.md, Open Items #2/#3.
export default function Barrierefreiheit() {
  return (
    <LegalPageLayout title="Erklärung zur Barrierefreiheit">
      <p>
        Die {ORG_NAME} ist bemüht, diese Anwendung im Einklang mit den
        Bestimmungen des Landes-Behindertengleichstellungsgesetzes (L-BGG)
        und der Barrierefreie-Informationstechnik-Verordnung (BITV 2.0)
        barrierefrei zugänglich zu machen.
      </p>

      <h2>Stand der Vereinbarkeit</h2>
      <p>
        Diese Anwendung befindet sich aktuell in der Umsetzung erster
        Barrierefreiheitsmaßnahmen (u. a. Sprachkennzeichnung, Sprungmarke
        zum Inhalt, Tastaturbedienbarkeit, sichtbare Fokusindikatoren). Eine
        förmliche Prüfung nach BITV 2.0 / EN 301 549 wurde noch nicht
        durchgeführt; der Grad der Vereinbarkeit wird derzeit geprüft und
        diese Erklärung nach Abschluss der Prüfung aktualisiert.
      </p>

      <h2>Nicht barrierefreie Inhalte</h2>
      <p>
        Eine vollständige Liste bekannter Barrieren liegt noch nicht vor und
        wird im Rahmen der laufenden Prüfung ergänzt. Dazu zählt
        voraussichtlich insbesondere die Bedienbarkeit der interaktiven
        Kartendarstellung (MapLibre) mit Tastatur und Screenreadern, deren
        vollständige Barrierefreiheit technisch eingeschränkt sein kann.
      </p>

      <h2>Erstellung dieser Erklärung</h2>
      <p>Diese Erklärung wurde am 20. Oktober 2026 erstellt.</p>

      <h2>Barrieren melden: Feedback</h2>
      <p>
        Sollten Ihnen Barrieren bei der Nutzung dieser Anwendung auffallen,
        kontaktieren Sie uns bitte:
        <br />
        {ORG_NAME}
        <br />
        E-Mail: [PLATZHALTER]
        <br />
        Telefon: [PLATZHALTER]
      </p>

      <h2>Schlichtungsverfahren</h2>
      <p>
        Wenn innerhalb von vier Wochen keine zufriedenstellende Antwort
        erfolgt, können Sie sich an die Schlichtungsstelle nach § 16
        L-BGG (Landeszentrum Barrierefreiheit Baden-Württemberg) wenden.
        Das Schlichtungsverfahren ist kostenfrei; eine anwaltliche Vertretung
        ist nicht erforderlich.
      </p>

      <p className="mt-8 text-xs text-bawu-grau-4">
        Hinweis: Diese Erklärung enthält noch Platzhalter und ist nach
        Abschluss einer förmlichen Barrierefreiheitsprüfung durch die{' '}
        {ORG_NAME} zu vervollständigen.
      </p>
    </LegalPageLayout>
  );
}
