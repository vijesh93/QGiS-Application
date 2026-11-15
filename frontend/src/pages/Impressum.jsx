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

      <h2>Technische Umsetzung</h2>
      <p>
        Diese Anwendung wird als containerisierte Webanwendung betrieben
        (React-Frontend, FastAPI-Backend, PostGIS-Datenbank, TiTiler).
      </p>

      <p className="mt-8 text-xs text-bawu-grau-4">
        Hinweis: Dieses Impressum enthält noch Platzhalter und ist vor der
        öffentlichen Freigabe durch die {ORG_NAME} zu vervollständigen und
        rechtlich zu prüfen.
      </p>
    </LegalPageLayout>
  );
}
