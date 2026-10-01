import { BookOpen, Newspaper } from "lucide-react"
// Import only the networks we show; the package entry point bundles every network's icon.
import { SocialIcon } from "react-social-icons/component"
import "react-social-icons/mastodon"
import "react-social-icons/reddit"
import "react-social-icons/youtube"

// The Bluesky butterfly, drawn inline because the icon set predates it.
function BlueskyMark({ size }) {
  return (
    <span
      className="inline-flex items-center justify-center rounded-full bg-[#1185FE] flex-shrink-0"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 600 530" width={size * 0.56} height={size * 0.56} fill="white">
        <path d="m135.72 44.03c66.496 49.921 138.02 151.14 164.28 205.46 26.262-54.316 97.782-155.54 164.28-205.46 47.98-36.021 125.72-63.892 125.72 24.795 0 17.712-10.155 148.79-16.111 170.07-20.703 73.984-96.144 92.854-163.25 81.433 117.3 19.964 147.14 86.092 82.697 152.22-122.39 125.59-175.91-31.511-189.63-71.766-2.514-7.3797-3.6904-10.832-3.7077-7.8964-0.0174-2.9357-1.1937 0.51669-3.7077 7.8964-13.714 40.255-67.233 197.36-189.63 71.766-64.444-66.128-34.605-132.26 82.697-152.22-67.108 11.421-142.55-7.4491-163.25-81.433-5.9562-21.282-16.111-152.36-16.111-170.07 0-88.687 77.742-60.816 125.72-24.795z" />
      </svg>
    </span>
  )
}

function Glyph({ size, className, children }) {
  return (
    <span
      className={`inline-flex items-center justify-center rounded-full flex-shrink-0 ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {children}
    </span>
  )
}

export default function PlatformIcon({ platform, size = 24 }) {
  switch (platform) {
    case "bluesky":
      return <BlueskyMark size={size} />
    case "mastodon":
    case "reddit":
    case "youtube":
      return <SocialIcon as="span" network={platform} style={{ width: size, height: size }} aria-hidden="true" />
    case "guardian":
      return (
        <Glyph size={size} className="bg-[#052962] text-white">
          <BookOpen size={size * 0.55} />
        </Glyph>
      )
    case "nyt":
      return (
        <Glyph size={size} className="bg-neutral-900 text-white light:bg-neutral-900">
          <Newspaper size={size * 0.55} />
        </Glyph>
      )
    default:
      return null
  }
}
