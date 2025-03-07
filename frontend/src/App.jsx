import { Link } from "react-router-dom";
import {
  Instagram,
  DogIcon as Mastodon,
  RssIcon as Reddit,
  Youtube,
  Newspaper,
  BookOpen,
} from "lucide-react";
import SocialCard from "./components/ui/SocialCard";

const socialPlatforms = [
  {
    id: "instagram",
    name: "Instagram Threads",
    icon: Instagram,
    color: "from-pink-500 to-purple-500",
    textColor: "text-white",
    description: "Microblogging and social networking.",
    route: "/instagram",
  },
  {
    id: "mastodon",
    name: "Mastodon",
    icon: Mastodon,
    color: "from-indigo-500 to-blue-500",
    textColor: "text-white",
    description: "Decentralized social network.",
    route: "/mastodon",
  },
  {
    id: "reddit",
    name: "Reddit",
    icon: Reddit,
    color: "from-orange-500 to-red-500",
    textColor: "text-white",
    description: "Social news and forum social network.",
    route: "/reddit",
  },
  {
    id: "youtube",
    name: "YouTube",
    icon: Youtube,
    color: "from-red-500 to-red-600",
    textColor: "text-white",
    description: "Online video sharing platform.",
    route: "/youtube",
  },
  {
    id: "guardian",
    name: "The Guardian",
    icon: BookOpen,
    color: "from-green-500 to-teal-500",
    textColor: "text-white",
    description: "British daily newspaper.",
    route: "/guardian",
  },
  {
    id: "times",
    name: "New York Times",
    icon: Newspaper,
    color: "from-blue-500 to-blue-600",
    textColor: "text-white",
    description: "Daily newspaper based in New York City.",
    route: "/times",
  },
];

const App = () => {
  return (
    <div className="max-w-7xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-8 text-center text-gray-900 dark:text-white">
        Social Media Dashboards
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
        {socialPlatforms.map((platform, index) => (
          <Link 
            key={platform.id} 
            to={platform.route}
            className="block"
          >
            <SocialCard
              name={platform.name}
              Icon={platform.icon}
              gradientClass={platform.color}
              textColor={platform.textColor}
              description={platform.description}
              animationDelay={index * 0.1}
            />
          </Link>
        ))}
      </div>
    </div>
  );
};

export default App;