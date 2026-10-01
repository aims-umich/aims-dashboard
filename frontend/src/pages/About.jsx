import { ArrowUpRight } from "lucide-react"
import { Link } from "react-router-dom"
import { Panel } from "../components/ui/Panel"
import { MODEL_ACCURACY, PAPER } from "../lib/platforms"
import { useStatus } from "../lib/statusContext"
import { useDocumentTitle } from "../lib/useDocumentTitle"

const STEPS = [
  {
    title: "Collect",
    body: "Official APIs only. Every source runs on its own schedule and on its own, so one outage never blocks the others.",
    meta: "seconds to 1 hour",
  },
  {
    title: "Filter",
    body: "Drop idioms, weapons, medicine, bot output and non-English text. Split news articles into sentences and keep those about energy.",
    meta: "keyword and context rules",
  },
  {
    title: "Score",
    body: "A BERT model fine-tuned on nuclear discourse gives each text three probabilities. The highest becomes its label.",
    meta: "per text, as it arrives",
  },
  {
    title: "Show",
    body: "Aggregate into trends with 95% intervals, and say “too few to call” when a sample is too small.",
    meta: "updated continuously",
  },
]

const SECTIONS = [
  ["collection", "Collection"],
  ["relevance", "Relevance filtering"],
  ["model", "The sentiment model"],
  ["net", "Reading net sentiment"],
  ["limits", "What this data is and is not"],
  ["people", "Contributors"],
  ["contact", "Contact and removal requests"],
]

const PEOPLE = [
  ["Jeremy Moon", "Designed and built the dashboard, the frontend, and the pipeline that connects every platform."],
  ["Andre Gala-Garza", "Early data-collection script for Mastodon."],
  ["Arvind Kutirakulam", "Early data-collection script for YouTube."],
  ["Yikun Yang", "Early data-collection script for The Guardian."],
  ["Huawen Shen", "Early data-collection script for the New York Times."],
]

function Section({ id, title, children }) {
  return (
    <section id={id} className="flex scroll-mt-24 flex-col gap-4">
      <h2 className="m-0 text-[30px] leading-tight font-[750] tracking-[-0.015em] wide text-ink">{title}</h2>
      {children}
    </section>
  )
}

export default function About() {
  useDocumentTitle("About")
  const model = useStatus().data?.scorer?.model
  const accuracy = model ? MODEL_ACCURACY[model.name] : null
  return (
    <div className="pb-8">
      <section aria-labelledby="ab-h" className="flex max-w-[900px] flex-col gap-5 pt-[72px] pb-12">
        <span className="num text-xs tracking-[0.1em] text-glow">ABOUT AND METHOD</span>
        <h1 id="ab-h" className="m-0 text-[44px] leading-none font-extrabold tracking-[-0.03em] wider sm:text-[64px]">
          How it works
        </h1>
        <p className="m-0 text-lg leading-relaxed text-ink2 sm:text-xl">
          A research project of the Artificial Intelligence and Multiphysics Simulations (AIMS) Lab in Nuclear
          Engineering and Radiological Sciences at the University of Michigan. It measures how public discussion of
          nuclear energy feels across social media and news, and how that changes over time.
        </p>
        <a
          href={PAPER.href}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 self-start text-[15px] font-semibold text-ink underline"
        >
          Read the paper behind it <ArrowUpRight size={15} aria-hidden="true" />
        </a>
      </section>

      <Panel
        as="section"
        aria-label="Pipeline"
        className="grid grid-cols-[repeat(auto-fit,minmax(min(230px,100%),1fr))] overflow-hidden"
      >
        {STEPS.map((step, i) => (
          <div key={step.title} className="flex flex-col gap-3 border-b border-line p-7 sm:border-r sm:border-b-0">
            <div className="flex items-center gap-3">
              <span className="num flex h-8 w-8 items-center justify-center rounded-full border border-line2 text-[13px] font-semibold">
                {i + 1}
              </span>
              <span className="text-xl font-[750] wide">{step.title}</span>
            </div>
            <p className="m-0 text-sm leading-relaxed text-ink2">{step.body}</p>
            <span className="num mt-auto text-xs text-ink3">{step.meta}</span>
          </div>
        ))}
      </Panel>

      <div className="flex flex-wrap items-start gap-16 pt-16">
        <nav aria-label="On this page" className="top-24 flex flex-[0_1_240px] flex-col gap-1 md:sticky">
          <span className="num pb-2 text-[11px] tracking-[0.1em] text-ink3">ON THIS PAGE</span>
          {SECTIONS.map(([id, label]) => (
            <a
              key={id}
              href={`#${id}`}
              className="border-l-2 border-line px-3 py-2 text-sm text-ink2 no-underline hover:border-glow hover:text-ink"
            >
              {label}
            </a>
          ))}
        </nav>
        <article className="flex min-w-0 flex-[1_1_560px] flex-col gap-14 text-[17px] leading-[1.75] text-ink2">
          <Section id="collection" title="Collection">
            <p className="m-0">
              Every source is read through its official, public API and within its terms of use. Bluesky posts arrive
              from the public Jetstream feed within seconds. Mastodon hashtag timelines are checked every two minutes.
              YouTube, The Guardian and the New York Times are checked every 30 to 60 minutes, as their API quotas
              allow. Each page shows when its source last updated.
            </p>
            <p className="m-0">
              We only keep what we need to show the charts: the text that is scored, a link to the original, the
              author&apos;s public handle, and engagement counts. Bluesky and Reddit posts deleted at the source are
              removed here automatically. Mastodon accounts that opted out of indexing, bot accounts, and Bluesky
              accounts hidden from logged-out viewers are left out. YouTube data is refreshed from YouTube at least
              every 30 days, and anything removed there is removed here. YouTube results are shown only as topic-level
              aggregates, never as scores for individual channels.
            </p>
          </Section>
          <Section id="relevance" title="Relevance filtering">
            <p className="m-0">
              Searching for “nuclear” also finds idioms (“the nuclear option”), weapons, geopolitics and medicine. Those
              texts are filtered out before scoring, along with anything that is not in English and text written by
              language-model bots, so the trends reflect discussion of nuclear energy. News articles are split into
              sentences, and a sentence only counts when its article is about energy somewhere.
            </p>
          </Section>
          <Section id="model" title="The sentiment model">
            <p className="m-0">
              Each text is labeled positive, neutral or negative by a BERT model fine-tuned on nuclear-energy discourse
              {model && (
                <>
                  {" "}
                  (<code className="num rounded-md bg-panel2 px-1.5 py-0.5 text-[15px] text-ink">{model.name}</code>)
                </>
              )}
              {accuracy ? `, which scored ${(accuracy * 100).toFixed(1)}% accuracy on the lab's held-out test set` : ""}
              . Like any model, it makes mistakes, especially on sarcasm and very short posts, so individual labels
              should be read as estimates and trends as the more reliable signal.{" "}
              <Link to="/model" className="text-ink underline">
                See where it slips
              </Link>
              .
            </p>
            <p className="m-0">
              The highlighted words on posts come from the same model: integrated gradients measure how much each word
              pushed the text toward positive or negative. Nobody writes them by hand.
            </p>
          </Section>
          <Section id="net" title="Reading net sentiment">
            <p className="m-0">
              Net sentiment is the share of positive texts minus the share of negative texts. It runs from {"−"}1,
              everything negative, to +1, everything positive. Neutral texts count toward the total but pull in neither
              direction. Every figure comes with a 95% interval, and below 30 texts the site says “too few to call”
              instead of showing a number.
            </p>
            <Panel className="flex flex-col gap-3.5 p-6 text-ink">
              <span className="num text-[11px] tracking-[0.1em] text-ink3">WORKED EXAMPLE</span>
              <div className="flex h-3.5 gap-[2px]" aria-hidden="true">
                <span className="rounded-[3px] bg-pos" style={{ width: "20%" }} />
                <span className="rounded-[3px] bg-neu" style={{ width: "50%" }} />
                <span className="rounded-[3px] bg-neg" style={{ width: "30%" }} />
              </div>
              <div className="num flex flex-wrap items-baseline gap-2.5 text-lg">
                <span>20% positive</span>
                <span className="text-ink3">{"−"}</span>
                <span>30% negative</span>
                <span className="text-ink3">=</span>
                <span className="text-[28px] font-semibold">{"−"}0.10</span>
              </div>
            </Panel>
          </Section>
          <Section id="limits" title="What this data is and is not">
            <p className="m-0">
              These are public, English-language posts and articles that mention nuclear energy. They are not a
              representative sample of any country&apos;s population, and platforms differ a lot in who posts and why.
              Data from before 2026 comes from the lab&apos;s earlier collection and was re-filtered and re-scored with
              the same rules and model as live data.
            </p>
          </Section>
          <Section id="people" title="Contributors">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(220px,100%),1fr))] gap-3">
              {PEOPLE.map(([name, role]) => (
                <Panel key={name} as="div" className="flex flex-col gap-1 rounded-xl px-[18px] py-4">
                  <span className="text-[15px] font-[650] text-ink">{name}</span>
                  <span className="text-[13px] leading-normal text-ink2">{role}</span>
                </Panel>
              ))}
            </div>
          </Section>
          <Section id="contact" title="Contact and removal requests">
            <p className="m-0">
              To ask a question or have content removed, contact the AIMS Lab through{" "}
              <a href="https://www.aims-umich.com/" className="text-ink underline">
                aims-umich.com
              </a>
              .
            </p>
          </Section>
        </article>
      </div>
    </div>
  )
}
