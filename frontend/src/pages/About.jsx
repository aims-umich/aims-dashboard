import { Link } from "react-router-dom"
import { useStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"

function Section({ title, children }) {
  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
      <div className="mt-3 space-y-3 text-base leading-7 text-gray-600 dark:text-gray-300">{children}</div>
    </section>
  )
}

export default function About() {
  useDocumentTitle("About")
  const { data } = useStatus()
  const model = data?.scorer?.model

  return (
    <article className="mx-auto max-w-3xl pb-16">
      <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">About</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 dark:text-white">How the dashboard works</h1>
      <p className="mt-4 text-base leading-7 text-gray-600 dark:text-gray-300">
        This dashboard is a research project of the Artificial Intelligence and Multiphysics Simulations (AIMS) Lab in
        Nuclear Engineering and Radiological Sciences at the University of Michigan. It measures how public discussion
        of nuclear energy feels across social media and news, and how that changes over time.
      </p>

      <Section title="Collection">
        <p>
          Every source is read through its official, public API and within its terms of use. Bluesky posts arrive
          from the public Jetstream feed within seconds. Mastodon hashtag timelines are checked every two minutes.
          YouTube, The Guardian, and the New York Times are checked every 30 to 60 minutes, as their API quotas allow.
          Each page shows when its source last updated.
        </p>
        <p>
          We only keep what we need to show the charts: the text that is scored, a link to the original, the
          author&apos;s public handle, and engagement counts. Bluesky and Reddit posts that are deleted at the source are
          removed here automatically. Mastodon accounts that opted out of indexing, bot accounts, and Bluesky
          accounts hidden from logged-out viewers are left out. YouTube data is refreshed from YouTube at least every
          30 days, and anything removed there is removed here. YouTube results are shown only as topic-level
          aggregates, never as scores for individual channels.
        </p>
      </Section>

      <Section title="Relevance filtering">
        <p>
          Searching for &quot;nuclear&quot; also finds idioms (&quot;the nuclear option&quot;), weapons, geopolitics, and
          medicine. Those texts are filtered out before scoring, along with anything that is not in English, so the
          trends reflect discussion of nuclear energy. News articles are split into sentences, and only sentences about
          nuclear energy are scored.
        </p>
      </Section>

      <Section title="The sentiment model">
        <p>
          Each text is labeled positive, neutral, or negative by a BERT model fine-tuned on nuclear-energy discourse
          {model ? (
            <>
              {" "}
              (<code className="rounded bg-gray-100 px-1.5 py-0.5 text-sm dark:bg-gray-800">{model.name}</code>)
            </>
          ) : null}
          , which scored 97.9% accuracy on the lab&apos;s held-out test set. The dashboard shows the model&apos;s confidence for
          every label. Like any model, it makes mistakes, especially on sarcasm and very short posts, so individual
          labels should be read as estimates and trends as the more reliable signal.
        </p>
        <p>
          &quot;Net sentiment&quot; is the share of positive texts minus the share of negative texts, from -1 (all
          negative) to +1 (all positive).
        </p>
      </Section>

      <Section title="What this data is and is not">
        <p>
          These are public, English-language posts and articles that mention nuclear energy. They are not a
          representative sample of any country&apos;s population, and platforms differ a lot in who posts and why.
          Data from before 2026 comes from the lab&apos;s earlier collection and was re-filtered and re-scored with the
          same rules and model as live data.
        </p>
      </Section>

      <Section title="Contributors">
        <p>
          Designed and built by Jeremy Moon at the AIMS Lab, including the dashboard, the frontend, and the pipeline
          that connects every platform. Early data-collection scripts were contributed by Andre Gala-Garza
          (Mastodon), Arvind Kutirakulam (YouTube), Yikun Yang (The Guardian), and Huawen Shen (New York Times).
        </p>
      </Section>

      <Section title="Contact and removal requests">
        <p>
          To ask a question or have content removed, contact the AIMS Lab through{" "}
          <a
            href="https://www.aims-umich.com/"
            className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            aims-umich.com
          </a>
          .
        </p>
      </Section>

      <p className="mt-12">
        <Link to="/" className="font-medium text-indigo-600 hover:underline dark:text-indigo-400">
          ← Back to the dashboards
        </Link>
      </p>
    </article>
  )
}
