import LegalPageLayout from '../components/LegalPageLayout';
import { ORG_NAME } from '../constants/brand';

// Required under § 5 TMG / § 18 Abs. 2 MStV. Structure is complete; the
// bracketed [PLATZHALTER] fields need LAZBW's exact details before this app
// goes fully public — see docs/bw-rebrand-plan.md, Open Items #2.
export default function Impressum() {
  return (
    <LegalPageLayout title="Impressum">
      <p>Angaben gemäß § 5 TMG / § 18 Abs. 2 Medienstaatsvertrag (MStV)</p>

      <h2>Diensteanbieter</h2>
      <p>
        {ORG_NAME}
        <br />
        [PLATZHALTER: Straße und Hausnummer]
        <br />
        [PLATZHALTER: PLZ und Ort]
      </p>

      <h2>Vertreten durch</h2>
      <p>[PLATZHALTER: Name der vertretungsberechtigten Person/Leitung]</p>

      <h2>Kontakt</h2>
      <p>
        Telefon: [PLATZHALTER]
        <br />
        E-Mail: [PLATZHALTER]
      </p>

      <h2>Zuständige Aufsichtsbehörde</h2>
      <p>[PLATZHALTER: zuständiges Ministerium des Landes Baden-Württemberg]</p>

      <h2>Verantwortlich für den Inhalt gemäß § 18 Abs. 2 MStV</h2>
      <p>[PLATZHALTER: Name und Anschrift der inhaltlich verantwortlichen Person]</p>

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
