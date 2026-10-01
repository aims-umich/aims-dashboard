import { Link } from "react-router-dom"
import { MODEL_ACCURACY, PAPER } from "../../lib/platforms"
import { useStatus } from "../../lib/statusContext"

export default function Footer() {
  const model = useStatus().data?.scorer?.model
  const accuracy = model ? MODEL_ACCURACY[model.name] : null
  return (
    <footer className="border-t border-line bg-panel pb-24 md:pb-0">
      <div className="mx-auto grid max-w-[1320px] grid-cols-[repeat(auto-fit,minmax(min(280px,100%),1fr))] gap-8 px-4 py-10 text-[13px] text-ink2 sm:px-10">
        <div className="flex flex-col gap-2">
          <span className="font-bold text-ink">Nuclear Sentiment Analysis</span>
          <span>
            A research project of the AIMS Lab, Nuclear Engineering and Radiological Sciences, University of Michigan.
          </span>
          <a href={PAPER.href} target="_blank" rel="noopener noreferrer" className="text-ink underline">
            Read the paper
          </a>
        </div>
        <div className="flex flex-col gap-2">
          <span className="font-bold text-ink">What this is not</span>
          <span>
            Public, English-language texts that mention nuclear energy, collected through each platform&apos;s official
            API. Not a representative sample of any country&apos;s population.
          </span>
        </div>
        <div className="flex flex-col gap-2">
          <span className="font-bold text-ink">Scored by</span>
          {model ? (
            <span className="num text-xs">
              {model.name} @ {model.revision.slice(0, 7)}
            </span>
          ) : (
            <span>…</span>
          )}
          <span>
            {accuracy ? `${(accuracy * 100).toFixed(1)}% accuracy on the lab's held-out test set. ` : ""}
            <Link to="/model" className="text-ink underline">
              Model details
            </Link>
          </span>
        </div>
      </div>
    </footer>
  )
}
