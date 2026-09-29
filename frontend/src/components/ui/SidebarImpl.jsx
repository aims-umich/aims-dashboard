import { IconMenu2, IconX } from "@tabler/icons-react"
import { AnimatePresence, motion } from "framer-motion"
import { useEffect } from "react"
import { NavLink, useLocation } from "react-router-dom"
import { classNames } from "../../lib/utils"
import { SidebarContext, useSidebar } from "./sidebarContext"


export const SidebarImpl = ({ children, open, setOpen, mobileOpen, setMobileOpen }) => {
  const location = useLocation()
  // Close the mobile menu after navigating.
  useEffect(() => setMobileOpen(false), [location.pathname, setMobileOpen])
  return (
    <SidebarContext.Provider value={{ open, setOpen, mobileOpen, setMobileOpen }}>{children}</SidebarContext.Provider>
  )
}

export const SidebarBody = (props) => (
  <>
    <DesktopSidebar {...props} />
    <MobileSidebar {...props} />
  </>
)

// Collapsed to icons; expands over the page on hover or keyboard focus without moving the content.
export const DesktopSidebar = ({ className, children }) => {
  const { open, setOpen } = useSidebar()
  return (
    <motion.nav
      aria-label="Dashboards"
      className={classNames(
        "fixed top-0 left-0 z-30 hidden h-screen flex-col overflow-hidden border-r border-gray-200 bg-white px-3.5 py-4 dark:border-gray-700 dark:bg-gray-800 md:flex",
        open && "shadow-xl",
        className,
      )}
      initial={false}
      animate={{ width: open ? 256 : 64 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setOpen(false)}
    >
      {children}
    </motion.nav>
  )
}

export const MobileSidebar = ({ className, children }) => {
  const { mobileOpen, setMobileOpen } = useSidebar()
  return (
    <div className="fixed inset-x-0 top-0 z-30 flex h-12 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-700 dark:bg-gray-800 md:hidden">
      <span className="text-sm font-semibold text-gray-900 dark:text-white">Nuclear Energy Sentiment</span>
      <button
        type="button"
        aria-label="Open menu"
        aria-expanded={mobileOpen}
        onClick={() => setMobileOpen(true)}
        className="rounded-md p-1.5 text-gray-800 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
      >
        <IconMenu2 size={22} />
      </button>
      <AnimatePresence>
        {mobileOpen && (
          <motion.nav
            aria-label="Dashboards"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className={classNames(
              "fixed inset-0 z-50 flex h-full w-full flex-col justify-between bg-white p-6 dark:bg-gray-800",
              className,
            )}
          >
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setMobileOpen(false)}
              className="absolute right-4 top-4 rounded-md p-1.5 text-gray-800 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
            >
              <IconX size={22} />
            </button>
            {children}
          </motion.nav>
        )}
      </AnimatePresence>
    </div>
  )
}

export const SidebarLink = ({ link, className }) => {
  const { open, mobileOpen } = useSidebar()
  const expanded = open || mobileOpen
  const label = (
    <span
      className={classNames(
        "whitespace-pre transition-opacity duration-150",
        expanded ? "opacity-100" : "pointer-events-none opacity-0",
      )}
    >
      {link.label}
    </span>
  )
  if (link.external) {
    return (
      <a
        href={link.href}
        target="_blank"
        rel="noopener noreferrer"
        title={expanded ? undefined : link.label}
        className={classNames(
          "flex items-center gap-3 rounded-lg px-1.5 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-700/40",
          className,
        )}
      >
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center">{link.icon}</span>
        {label}
      </a>
    )
  }
  return (
    <NavLink
      to={link.href}
      end={link.href === "/"}
      title={expanded ? undefined : link.label}
      className={({ isActive }) =>
        classNames(
          "flex items-center gap-3 rounded-lg px-1.5 py-1.5 text-sm transition-colors",
          isActive
            ? "bg-gray-100 font-medium text-gray-900 dark:bg-gray-700/70 dark:text-white"
            : "text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-700/40",
          className,
        )
      }
    >
      <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center">{link.icon}</span>
      {label}
    </NavLink>
  )
}
