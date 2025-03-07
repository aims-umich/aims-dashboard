import { useState } from "react";
import { motion } from "framer-motion";

export default function SocialCard({ 
  name, 
  Icon, 
  gradientClass, 
  textColor, 
  description, 
  animationDelay = 0 
}) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: animationDelay, duration: 0.5 }}
      className="relative group z-0"
    >
      <div
        className={`relative overflow-hidden rounded-xl shadow-lg transition-all duration-300 ${
          isHovered ? "scale-[1.02]" : "scale-100"
        }`}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className={`absolute inset-0 bg-gradient-to-br ${gradientClass} opacity-90`}></div>
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,white_0%,transparent_60%)]"></div>
        </div>
        <div className="relative p-6 h-full flex flex-col">
          <div className="flex items-center mb-4">
            <div className={`p-2 rounded-full bg-white/20 ${textColor}`}>
              <Icon size={24} />
            </div>
            <h3 className={`ml-3 text-xl font-bold ${textColor}`}>{name}</h3>
          </div>
          <p className={`${textColor} opacity-80 text-sm mb-4`}>{description}</p>
          <div className="mt-auto flex justify-between items-center">
            <div className={`text-sm font-medium ${textColor}`}>View Dashboard</div>
            <div
              className={`p-2 rounded-full bg-white/20 ${textColor} transition-transform duration-300 ${
                isHovered ? "translate-x-1" : ""
              }`}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>
        </div>
        <div
          className={`absolute inset-0 border border-white/30 rounded-xl transition-opacity duration-300 ${
            isHovered ? "opacity-100" : "opacity-0"
          }`}
        ></div>
      </div>
    </motion.div>
  );
}