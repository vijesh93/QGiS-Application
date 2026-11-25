import LegalPageLayout from '../components/LegalPageLayout';
import { ORG_NAME } from '../constants/brand';
import legal from '../config/legal.json';

// Required under § 5 TMG / § 18 Abs. 2 MStV. Structure is complete; the
// actual org details live in frontend/src/config/legal.json (gitignored —
// copy legal.example.json to legal.json and fill in LAZBW's exact details
// before this app goes fully public — see README's Quick Start and
// docs/bw-rebrand-plan.md, Open Items #2).
export default function Impressum() {
  return (
    <LegalPageLayout title="Impressum">
      <p>Angaben gemäß § 5 TMG / § 18 Abs. 2 Medienstaatsvertrag (MStV)</p>

      <h2>Diensteanbieter</h2>
      <p>
        {ORG_NAME}
        <br />
        {legal.address.strasse}
        <br />
        {legal.address.plzOrt}
      </p>

      <h2>Vertreten durch</h2>
      <p>{legal.impressum.vertretenDurch}</p>

      <h2>Kontakt</h2>
      <p>
        Telefon: {legal.impressum.telefon}
        <br />
        E-Mail: {legal.impressum.email}
      </p>

      <h2>Zuständige Aufsichtsbehörde</h2>
      <p>{legal.impressum.aufsichtsbehoerde}</p>

      <h2>Verantwortlich für den Inhalt gemäß § 18 Abs. 2 MStV</h2>
      <p>{legal.impressum.verantwortlichFuerInhalt}</p>

      <h2>Haftungsausschluss</h2>
      <p>
        <strong>Haftung für Inhalte:</strong> Die Inhalte dieser Anwendung
        wurden mit größtmöglicher Sorgfalt erstellt. Für die Richtigkeit,
        Vollständigkeit und Aktualität der Inhalte kann jedoch keine Gewähr
        übernommen werden.
      </p>
      <p>
        <strong>Haftung für Links:</strong> Diese Anwendung kann Links zu
        externen Webseiten Dritter enthalten, auf deren Inhalte kein Einfluss
        besteht. Für diese fremden Inhalte kann daher keine Gewähr übernommen
        werden; verantwortlich ist stets der jeweilige Anbieter oder Betreiber
        der verlinkten Seiten.
      </p>

      <h2>Urheber- und Kennzeichenrecht</h2>
      <p>
        Die durch die Betreiber dieser Anwendung erstellten Inhalte und Werke
        unterliegen dem deutschen Urheberrecht. Vervielfältigung, Bearbeitung,
        Verbreitung und jede Art der Verwertung außerhalb der Grenzen des
        Urheberrechtes bedürfen der schriftlichen Zustimmung der jeweiligen
        Urheber bzw. Ersteller.
      </p>

      <p className="mt-8 text-xs text-bawu-grau-4">
        Hinweis: Dieses Impressum enthält noch Platzhalter und ist vor der
        öffentlichen Freigabe durch die {ORG_NAME} zu vervollständigen und
        rechtlich zu prüfen.
      </p>
    </LegalPageLayout>
  );
}
