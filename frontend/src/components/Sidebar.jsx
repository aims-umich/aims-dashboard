import { Home, Info } from "lucide-react"
import { useState } from "react"
import { PLATFORMS, PLATFORM_ORDER } from "../lib/platforms"
import { useStatus } from "../lib/statusContext"
import PlatformIcon from "./PlatformIcon"
import { SidebarBody, SidebarImpl, SidebarLink } from "./ui/SidebarImpl"

export function Sidebar({ children }) {
  const [open, setOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { data } = useStatus()
  // Only platforms the API is serving; before the first response, show them all to avoid layout jumps.
  const live = data ? new Set(data.platforms.map((p) => p.platform)) : null
  const links = PLATFORM_ORDER.filter((key) => !live || live.has(key)).map((key) => ({
    label: PLATFORMS[key].name,
    href: PLATFORMS[key].route,
    icon: <PlatformIcon platform={key} size={24} />,
  }))

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <SidebarImpl open={open} setOpen={setOpen} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen}>
        <SidebarBody className="justify-between gap-10">
          <div className="flex flex-1 flex-col overflow-y-auto overflow-x-hidden">
            <SidebarLink
              link={{ label: "All dashboards", href: "/", icon: <Home size={20} className="text-gray-700 dark:text-gray-200" /> }}
            />
            <div className="mt-6 flex flex-col gap-1">
              {links.map((link) => (
                <SidebarLink key={link.href} link={link} />
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <SidebarLink
              link={{ label: "About the data", href: "/about", icon: <Info size={20} className="text-gray-700 dark:text-gray-200" /> }}
            />
            <SidebarLink
              link={{
                label: "AIMS Lab",
                href: "https://www.aims-umich.com/",
                external: true,
                icon: <img src="/michigan.webp" className="h-6 w-6 rounded-full" width={24} height={24} alt="" />,
              }}
            />
          </div>
        </SidebarBody>
      </SidebarImpl>
      <div className="pt-12 md:pl-16 md:pt-0">{children}</div>
    </div>
  )
}
